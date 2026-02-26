use libattpc_merger::worker_status::WorkerStatus;
use std::io::{self, Write};
use std::sync::mpsc::Receiver;

trait ProgressReporter {
    fn report_start(&mut self);
    fn report_progress(&mut self, percentage: i32);
    fn report_finish(&mut self);
}

struct ZmqProgressReporter {
    execution_id: String,
    task_id: i32,
    _context: zmq::Context,
    socket: Option<zmq::Socket>,
}

impl ZmqProgressReporter {
    fn new(execution_id: String, task_id: i32) -> Self {
        let context = zmq::Context::new();
        let socket = match context.socket(zmq::PUSH) {
            Ok(socket) => match socket.connect("ipc://@attpc_flow_zmq") {
                Ok(_) => Some(socket),
                Err(error) => {
                    eprintln!(
                        "Warning: failed to connect ZMQ progress socket to {}: {}",
                        "ipc://@attpc_flow_zmq", error
                    );
                    None
                }
            },
            Err(error) => {
                eprintln!("Warning: failed to create ZMQ progress socket: {error}");
                None
            }
        };

        Self {
            execution_id,
            task_id,
            _context: context,
            socket,
        }
    }

    fn send(&self, message: &str) {
        if let Some(socket) = &self.socket {
            if let Err(error) = socket.send(message, zmq::DONTWAIT) {
                eprintln!("Warning: failed to send progress update via ZMQ: {error}");
            }
        }
    }
}

impl ProgressReporter for ZmqProgressReporter {
    fn report_start(&mut self) {
        let message = format!("task,start,{},{}", self.execution_id, self.task_id);
        self.send(&message);
    }

    fn report_progress(&mut self, percentage: i32) {
        let message = format!(
            "task,progress,{},{},{}",
            self.execution_id, self.task_id, percentage
        );
        self.send(&message);
    }

    fn report_finish(&mut self) {
        let message = format!("task,finish,{},{}", self.execution_id, self.task_id);
        self.send(&message);
    }
}

struct TextProgressReporter {
    prefix: String,
}

impl TextProgressReporter {
    fn new(prefix: impl Into<String>) -> Self {
        Self {
            prefix: prefix.into(),
        }
    }

    fn label(&self) -> &str {
        if self.prefix.is_empty() {
            "Progress"
        } else {
            &self.prefix
        }
    }
}

impl ProgressReporter for TextProgressReporter {
    fn report_start(&mut self) {
        print!("{}:", self.label());
        let _ = io::stdout().flush();
    }

    fn report_progress(&mut self, percentage: i32) {
        let clamped = percentage.clamp(0, 100);
        print!("\r{}: {:>3}%", self.label(), clamped);
        let _ = io::stdout().flush();
    }

    fn report_finish(&mut self) {
        println!("\r{}: Task completed", self.label());
    }
}

pub fn spawn_progress_reporter(
    task_id: i32,
    execution_id: String,
    rx: Receiver<WorkerStatus>,
) -> std::thread::JoinHandle<()> {
    std::thread::spawn(move || {
        let mut reporter: Box<dyn ProgressReporter + Send> = if task_id >= 0 {
            Box::new(ZmqProgressReporter::new(execution_id, task_id))
        } else {
            Box::new(TextProgressReporter::new("Progress"))
        };

        reporter.report_start();

        while let Ok(status) = rx.recv() {
            let percentage = ((status.progress * 100.0).round() as i32).clamp(0, 100);
            reporter.report_progress(percentage);
        }

        reporter.report_finish();
    })
}

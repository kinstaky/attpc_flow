mod progress_reporter;

use hdf5::types::VarLenArray;
use hdf5::{Dataset, File};
use libattpc_merger::config::Config;
use libattpc_merger::process::process_run;
use pyo3::prelude::*;
use rusqlite::{Connection, OptionalExtension};
use std::path::{Path, PathBuf};
use std::sync::{mpsc, Arc};

fn setup_logger(log_path: &Path) {
    if let Some(parent) = log_path.parent() {
        if let Err(error) = std::fs::create_dir_all(parent) {
            spdlog::warn!("Failed to create log directory: {error}");
            return;
        }
    }

    let file_sink = Arc::new(
        spdlog::sink::FileSink::builder()
            .path(log_path.to_path_buf())
            .formatter(Box::new(spdlog::formatter::PatternFormatter::new(
                spdlog::formatter::pattern!(
                    "[{date_short} {time_short}] - [thread: {tid}] - [{^{level}}] - {payload}{eol}"
                ),
            )))
            .truncate(false)
            .build()
            .unwrap(),
    );

    let logger = Arc::new(
        spdlog::Logger::builder()
            .flush_level_filter(spdlog::LevelFilter::All)
            .sink(file_sink)
            .build()
            .unwrap(),
    );

    spdlog::set_default_logger(logger);
}

fn read_summary_range(summary_path: &Path, run: i32) -> Option<(u64, u64)> {
    if !summary_path.exists() {
        return None;
    }
    let conn = Connection::open(summary_path).ok()?;
    let mut stmt = conn
        .prepare(
            "SELECT start, end FROM summary WHERE run = ?1 AND cobo = -1 AND asad = -1",
        )
        .ok()?;
    let row: Option<(i64, i64)> = stmt
        .query_row([run], |row| Ok((row.get(0)?, row.get(1)?)))
        .optional()
        .ok()?;
    let (min_event, max_event) = row?;
    if min_event < 0 || max_event < 0 {
        return None;
    }
    Some((min_event as u64, max_event as u64))
}

fn read_event_id_attr(dataset: &Dataset) -> Option<u64> {
    let id_attr = dataset.attr("id").ok()?;
    let value: u32 = id_attr.read_scalar().ok()?;
    Some(value as u64)
}

fn read_hdf_event_id_range(hdf_path: &Path) -> Option<(u64, u64)> {
    if !hdf_path.exists() {
        return None;
    }
    let file = File::open(hdf_path).ok()?;
    let events_group = file.group("events").ok()?;
    let min_index: u64 = events_group.attr("min_event").ok()?.read_scalar().ok()?;
    let max_index: u64 = events_group.attr("max_event").ok()?.read_scalar().ok()?;

    let get_group = events_group.group("get").ok()?;
    let min_dataset = get_group.dataset(&format!("event_{min_index}")).ok()?;
    let max_dataset = get_group.dataset(&format!("event_{max_index}")).ok()?;

    let min_event_id = read_event_id_attr(&min_dataset)?;
    let max_event_id = read_event_id_attr(&max_dataset)?;

    Some((min_event_id, max_event_id))
}

fn read_bad_events(bad_event_path: &Path) -> Vec<u64> {
    if !bad_event_path.exists() {
        return Vec::new();
    }
    let Ok(contents) = std::fs::read_to_string(bad_event_path) else {
        return Vec::new();
    };
    let mut events: Vec<u64> = contents
        .lines()
        .filter_map(|line| line.trim().parse::<u64>().ok())
        .collect();
    events.sort_unstable();
    events.dedup();
    events
}

fn read_hdf_bad_events(hdf_path: &Path) -> Option<Vec<u64>> {
    if !hdf_path.exists() {
        return None;
    }
    let file = File::open(hdf_path).ok()?;
    let events_group = file.group("events").ok()?;
    let attr = events_group.attr("bad_events").ok()?;
    let values = attr.read_scalar::<VarLenArray<u64>>().ok()?;
    Some(values.as_slice().to_vec())
}

fn write_hdf_bad_events(hdf_path: &Path, bad_events: &[u64]) -> Result<(), hdf5::Error> {
    let file = File::open_rw(hdf_path)?;
    let events_group = file.group("events")?;
    let values = VarLenArray::from_slice(bad_events);

    if let Ok(attr) = events_group.attr("bad_events") {
        attr.write_scalar(&values)?;
        return Ok(());
    }

    let attr = events_group.new_attr::<VarLenArray<u64>>().create("bad_events")?;
    attr.write_scalar(&values)?;
    Ok(())
}

#[pyfunction]
fn merge_attpc(
    execution_id: String,
    task_id: i32,
    workspace: String,
    graw: String,
    evt: String,
    map: String,
    run: i32,
    merger_tag: Option<String>,
) -> PyResult<String> {
    let workspace_path = PathBuf::from(&workspace);
    let hdf_path = workspace_path.join("hdf5");
    // create hdf path if not exist
    if !hdf_path.exists() {
        std::fs::create_dir_all(&hdf_path)?;
    }
    setup_logger(
        &workspace_path
            .join("log")
            .join("attpc_merger")
            .join(format!("{run}.log")),
    );
    let graw_path = PathBuf::from(&graw);
    let evt_path = PathBuf::from(&evt);
    let map_path = PathBuf::from(&map);
    let config = Config {
        graw_path: graw_path,
        online: false,
        experiment: String::from(""),
        merge_atttpc: true,
        merge_silicon: true,
        evt_path: Some(evt_path),
        hdf_path: hdf_path,
        copy_path: None,
        delete_copied: true,
        channel_map_path: Some(map_path),
        first_run_number: run,
        last_run_number: run,
        n_threads: 1,
    };

    let hdf_file_path = config.hdf_path.join(format!("run_{run}.h5"));

    let summary_path = workspace_path.join("summary").join("merge_check.db");
    let summary_range = read_summary_range(&summary_path, run);
    let hdf_event_id_range = read_hdf_event_id_range(&hdf_file_path);

    // Gate information
    spdlog::info!("HDF5 file path: {}", hdf_file_path.display());
    spdlog::info!("Summary DB path: {}", summary_path.display());
    spdlog::info!("Merger tag: {:?}", merger_tag);

    match summary_range {
        Some((min_evt, max_evt)) => {
            spdlog::info!("Summary event-id range: min={min_evt}, max={max_evt}");
        }
        None => {
            spdlog::warn!("Summary event-id range not available");
        }
    }
    match hdf_event_id_range {
        Some((min_evt, max_evt)) => {
            spdlog::info!("HDF5 event-id range: min={min_evt}, max={max_evt}");
        }
        None => {
            spdlog::warn!("HDF5 event-id range not available");
        }
    }

    let hdf_missing = !hdf_file_path.exists();
    let merger_not_success = merger_tag.as_deref() != Some("success");
    let event_id_range_mismatch = match (summary_range, hdf_event_id_range) {
        (Some(summary), Some(hdf)) => summary != hdf,
        _ => false,
    };

    let mut merge_reasons: Vec<String> = Vec::new();
    if hdf_missing {
        merge_reasons.push(String::from("merged HDF5 file does not exist"));
    }
    if merger_not_success {
        merge_reasons.push(format!(
            "merger tag is missing or not success (current: {:?})",
            merger_tag
        ));
    }
    if event_id_range_mismatch {
        merge_reasons.push(format!(
            "event-id range mismatch (summary={:?}, hdf5={:?})",
            summary_range, hdf_event_id_range
        ));
    }

    let need_merge = !merge_reasons.is_empty();
    if need_merge {
        for reason in &merge_reasons {
            spdlog::info!("Gate decision: NEED MERGE - {reason}");
        }
    } else {
        spdlog::info!("Gate decision: SKIP MERGE - all merge conditions are false");
    }

    if need_merge {
        let (tx, rx) = mpsc::channel();
        let worker_id: usize = if run < 0 { 0 } else { run as usize };
        let reporter_handle =
            progress_reporter::spawn_progress_reporter(task_id, execution_id, rx);

        let run_result = process_run(&config, run, &tx, &worker_id);
        drop(tx);

        if let Err(error) = reporter_handle.join() {
            spdlog::warn!("Progress reporter thread panicked: {error:?}");
        }

        if let Err(error) = run_result {
            spdlog::error!("Run failed: {error:?}");
            return Ok(String::from("failed"));
        }
    } else {
        let mut reporter = progress_reporter::create_progress_reporter(
            task_id, execution_id
        );
        reporter.report_cached();
        spdlog::info!("Skipping merge operation.");
    }

    // Collect final statistics
    let mut final_min_event: u64 = 0;
    let mut final_max_event: u64 = 0;
    let mut bad_events: Vec<u64> = Vec::new();
    let mut total_events: u64 = 0;

    if hdf_file_path.exists() {
        let bad_event_path =
            workspace_path.join("run").join("bad_events").join(format!("{run}.txt"));
        bad_events = read_bad_events(&bad_event_path);

        // Get HDF5 real event-id stats from events/get/event_{index}.attr("id")
        if let Some((min_evt, max_evt)) = read_hdf_event_id_range(&hdf_file_path) {
            final_min_event = min_evt;
            final_max_event = max_evt;
        }

        // Sync bad events to HDF5
        let hdf_bad_events = read_hdf_bad_events(&hdf_file_path).unwrap_or_default();
        if bad_events != hdf_bad_events {
            spdlog::info!("Bad events mismatch: file has {}, HDF5 has {}", bad_events.len(), hdf_bad_events.len());
            if let Err(error) = write_hdf_bad_events(&hdf_file_path, &bad_events) {
                spdlog::warn!("Failed to sync bad_events to HDF5: {error}");
            } else {
                spdlog::info!("Synced {} bad events to HDF5", bad_events.len());
            }
        } else {
            spdlog::info!("Bad events already in sync: {} events", bad_events.len());
        }
    }

    // Calculate total events including bad events
    if final_max_event >= final_min_event {
        total_events = final_max_event - final_min_event + 1;
    }

    // Print final merge statistics
    spdlog::info!("=== Merge Statistics for run {run} ===");
    spdlog::info!("Min event: {final_min_event}");
    spdlog::info!("Max event: {final_max_event}");
    spdlog::info!("Bad event count: {}", bad_events.len());
    spdlog::info!("Total events (including bad): {total_events}");
    if !bad_events.is_empty() {
        let bad_events_str: Vec<String> = bad_events.iter().map(|e| e.to_string()).collect();
        spdlog::info!("Bad event IDs: [{}]", bad_events_str.join(", "));
    }

    Ok(String::from("success"))

}

#[pymodule]
mod _lib {
    #[pymodule_export]
    use super::merge_attpc;
}
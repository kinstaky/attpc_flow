#ifdef ATTPC_FLOW_USE_ZMQ

#include "include/common/zmq_progress_reporter.h"

#include <sstream>
#include <iostream>

namespace atflow {

ZmqProgressReporter::ZmqProgressReporter(
	std::string execution_id,
	int task_id,
	const std::string &endpoint
)
: execution_id_(execution_id)
, task_id_(task_id)
, endpoint_(endpoint)
, context_()
, socket_(context_, zmq::socket_type::push) {
	try {
		socket_.connect(endpoint_);
	} catch (const zmq::error_t &e) {
		std::cerr << "Warning: Failed to initialize ZMQ progress reporter: " << e.what() << std::endl;
	}
}

void ZmqProgressReporter::ReportStart() {
	try {
		std::stringstream msg;
		msg << "task,start," << execution_id_ << "," << task_id_;
		socket_.send(zmq::buffer(msg.str()), zmq::send_flags::dontwait);
	} catch (const zmq::error_t &e) {
		// Log but don't throw - progress reporting failure shouldn't stop processing
		std::cerr << "Warning: Failed to send start message: " << e.what() << std::endl;
	}
}

void ZmqProgressReporter::ReportProgress(int percentage) {
	try {
		if (percentage < 0) percentage = 0;
		if (percentage > 100) percentage = 100;
		std::stringstream msg;
		msg << "task,progress," << execution_id_ << "," << task_id_ << "," << percentage;
		socket_.send(zmq::buffer(msg.str()), zmq::send_flags::dontwait);
	} catch (const zmq::error_t &e) {
		// Log but don't throw - progress reporting failure shouldn't stop processing
		std::cerr << "Warning: Failed to send progress update: " << e.what() << std::endl;
	}
}

void ZmqProgressReporter::ReportFinish() {
	try {
		std::stringstream msg;
		msg << "task,finish," << execution_id_ << "," << task_id_;
		socket_.send(zmq::buffer(msg.str()), zmq::send_flags::dontwait);
	} catch (const zmq::error_t &e) {
		// Log but don't throw - progress reporting failure shouldn't stop processing
		std::cerr << "Warning: Failed to send finish message: " << e.what() << std::endl;
	}
}

}

#endif // ATTPC_FLOW_USE_ZMQ

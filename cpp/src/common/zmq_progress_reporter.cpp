#ifdef ATTPC_FLOW_USE_ZMQ

#include "include/common/zmq_progress_reporter.h"

#include <sstream>
#include <iostream>

namespace atflow {

ZmqProgressReporter::ZmqProgressReporter(int task_id, const std::string &endpoint)
	: task_id_(task_id)
	, endpoint_(endpoint)
	, context_()
	, socket_(context_, zmq::socket_type::push)
{
	try {
		socket_.connect(endpoint_);
	} catch (const zmq::error_t &e) {
		std::cerr << "Warning: Failed to initialize ZMQ progress reporter: " << e.what() << std::endl;
	}
}

ZmqProgressReporter::~ZmqProgressReporter() {
	// zmq::socket_t and zmq::context_t will be destroyed automatically
}

void ZmqProgressReporter::report_progress(int percentage) {
	try {
		std::stringstream msg;
		msg << task_id_ << "," << percentage;
		socket_.send(zmq::buffer(msg.str()), zmq::send_flags::dontwait);
	} catch (const zmq::error_t &e) {
		// Log but don't throw - progress reporting failure shouldn't stop processing
		std::cerr << "Warning: Failed to send progress update: " << e.what() << std::endl;
	}
}

}

#endif // ATTPC_FLOW_USE_ZMQ

#ifndef ZMQ_PROGRESS_REPORTER_H_
#define ZMQ_PROGRESS_REPORTER_H_

#include "include/common/progress_reporter.h"
#include "ext/zmq.hpp"
#include <string>

namespace atflow {

/// @brief ZeroMQ-based progress reporter
/// Only available when ATTPC_FLOW_USE_ZMQ is defined at compile time
class ZmqProgressReporter : public ProgressReporter {
public:
	/// @brief Constructor
	/// @param[in] execution_id Execution identifier for progress messages
	/// @param[in] task_id Task identifier for progress messages
	/// @param[in] endpoint ZMQ endpoint string (e.g., "ipc://@attpc_flow_zmq")
	ZmqProgressReporter(std::string execution_id, int task_id, const std::string &endpoint);

	/// @brief Destructor
	virtual ~ZmqProgressReporter() override = default;

	/// @brief Report the start of a task via ZeroMQ
	virtual void ReportStart() override;

	/// @brief Report progress percentage via ZeroMQ
	/// @param[in] percentage Progress percentage (0-100)
	virtual void ReportProgress(int percentage) override;

	/// @brief Report the finish of a task via ZeroMQ
	virtual void ReportFinish() override;

	// Delete copy constructor and assignment operator
	ZmqProgressReporter(const ZmqProgressReporter &) = delete;
	ZmqProgressReporter &operator=(const ZmqProgressReporter &) = delete;

private:
	std::string execution_id_;
	int task_id_;
	std::string endpoint_;
	zmq::context_t context_;
	zmq::socket_t socket_;
};

}

#endif // ZMQ_PROGRESS_REPORTER_H_

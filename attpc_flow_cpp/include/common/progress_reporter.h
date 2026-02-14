#ifndef PROGRESS_REPORTER_H_
#define PROGRESS_REPORTER_H_

namespace atflow {

/// @brief Abstract interface for progress reporting
/// Allows different implementations (ZeroMQ, terminal output, file, etc.)
class ProgressReporter {
public:
	/// @brief Virtual destructor
	virtual ~ProgressReporter() = default;

	/// @brief Report the start of a task
	virtual void ReportStart() = 0;

	/// @brief Report progress percentage
	/// @param[in] percentage Progress percentage (0-100)
	virtual void ReportProgress(int percentage) = 0;

	/// @brief Report the finish of a task
	virtual void ReportFinish() = 0;
};

}

#endif // PROGRESS_REPORTER_H_

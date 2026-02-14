#ifndef TEXT_PROGRESS_REPORTER_H_
#define TEXT_PROGRESS_REPORTER_H_

#include "include/common/progress_reporter.h"
#include <string>

namespace atflow {

/// @brief Text-based progress reporter that prints to stdout
/// Uses carriage return to update progress on the same line
class TextProgressReporter : public ProgressReporter {
public:
	/// @brief Constructor
	/// @param[in] prefix Optional prefix text for progress messages
	explicit TextProgressReporter(const std::string &prefix = "");

	/// @brief Destructor
	virtual ~TextProgressReporter() override = default;

	/// @brief Report the start of a task via stdout
	virtual void ReportStart() override;

	/// @brief Report progress percentage via stdout
	/// @param[in] percentage Progress percentage (0-100)
	virtual void ReportProgress(int percentage) override;

	/// @brief Report the finish of a task via stdout
	virtual void ReportFinish() override;

	// Delete copy constructor and assignment operator
	TextProgressReporter(const TextProgressReporter &) = delete;
	TextProgressReporter &operator=(const TextProgressReporter &) = delete;

private:
	std::string prefix_;
};

}

#endif // TEXT_PROGRESS_REPORTER_H_

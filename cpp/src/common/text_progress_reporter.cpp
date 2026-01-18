#include "include/common/text_progress_reporter.h"
#include <iostream>
#include <iomanip>

namespace atflow {

TextProgressReporter::TextProgressReporter(const std::string &prefix)
	: prefix_(prefix)
	, first_report_(true)
{
}

TextProgressReporter::~TextProgressReporter() {
	// Print newline on destruction to ensure final state is visible
	if (!first_report_) {
		std::cout << std::endl;
	}
}

void TextProgressReporter::report_progress(int percentage) {
	if (percentage < 0) percentage = 0;
	if (percentage > 100) percentage = 100;

	if (first_report_) first_report_ = false;
	else std::cout << "\r";

	if (prefix_.empty()) {
		std::cout << "Progress: " << std::setw(3) << percentage << "%";
	} else {
		std::cout << prefix_ << ": " << std::setw(3) << percentage << "%";
	}
	std::cout << std::flush;
}

}

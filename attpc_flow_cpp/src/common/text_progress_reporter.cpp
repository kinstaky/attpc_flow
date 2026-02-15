#include "include/common/text_progress_reporter.h"
#include <iostream>
#include <iomanip>

namespace atflow {

TextProgressReporter::TextProgressReporter(const std::string &prefix)
	: prefix_(prefix) {}

void TextProgressReporter::ReportStart() {
	if (prefix_.empty()) {
		std::cout << "Progress:";
	} else {
		std::cout << prefix_ << ":";
	}
}

void TextProgressReporter::ReportProgress(int percentage) {
	if (percentage < 0) percentage = 0;
	if (percentage > 100) percentage = 100;

	std::cout << "\r";
	if (prefix_.empty()) {
		std::cout << "Progress: " << std::setw(3) << percentage << "%";
	} else {
		std::cout << prefix_ << ": " << std::setw(3) << percentage << "%";
	}
	std::cout << std::flush;
}

void TextProgressReporter::ReportFinish() {
	std::cout << "\r";
	if (prefix_.empty()) {
		std::cout << "Progress: Task completed" << std::endl;
	} else {
		std::cout << prefix_ << ": Task completed" << std::endl;
	}
}

}

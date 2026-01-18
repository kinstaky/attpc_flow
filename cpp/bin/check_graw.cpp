#include <iostream>
#include <fstream>
#include <filesystem>
#include <vector>
#include <algorithm>
#include <memory>

#include "include/merge/graw_checker.h"
#include "include/common/text_progress_reporter.h"


int main(int argc, char **argv) {
	// check arguments
	if (argc != 4) {
		std::cout << "Usage: " << argv[0] << " <graw_dir> <workspace_dir> <run>" << std::endl;
		return -1;
	}
	// graw directory
	std::filesystem::path graw_dir(argv[1]);
	// workspace directory
	std::filesystem::path workspace_dir(argv[2]);
	// run number
	int run = std::stoi(argv[3]);
	// check with text progress reporter
	auto progress_reporter = std::make_unique<atflow::TextProgressReporter>("Checking graw files");
	atflow::GrawChecker checker(workspace_dir, graw_dir, run, std::move(progress_reporter));
	atflow::CheckGrawResult result = checker.Check();
	// show results
	std::cout << (result.pass ? "Pass" : "Fail") << std::endl;
	for (const int idx : result.which) {
		std::cout << result.asad_results[idx].cobo
			<< ", " << result.asad_results[idx].asad
			<< ", " << atflow::AsadResultTypeToString(result.asad_results[idx].type)
			<< std::endl;
	}
	return 0;
}
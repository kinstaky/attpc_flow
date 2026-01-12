#include <iostream>
#include <fstream>
#include <filesystem>
#include <vector>
#include <algorithm>

#include "include/merge/graw_checker.h"


int main(int argc, char **argv) {
	// check arguments
	if (argc != 3) {
		std::cout << "Usage: " << argv[0] << " <graw_dir> <run>" << std::endl;
		return -1;
	}
	// graw directory
	std::filesystem::path graw_dir(argv[1]);
	// run number
	int run = std::stoi(argv[2]);
	// check
	flow::GrawChecker checker(graw_dir, run);
	flow::CheckGrawResult result = checker.Check();
	// show results
	std::cout << (result.pass ? "Pass" : "Fail") << std::endl;
	for (const int idx : result.which) {
		std::cout << result.asad_results[idx].cobo
			<< ", " << result.asad_results[idx].asad
			<< ", " << flow::AsadResultTypeToString(result.asad_results[idx].type)
			<< std::endl;
	}
	return 0;
}
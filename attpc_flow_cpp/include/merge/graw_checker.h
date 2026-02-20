#ifndef GRAW_CHECKER_H_
#define GRAW_CHECKER_H_

#include <filesystem>
#include <memory>
#include <vector>
#include <sstream>
#include <set>

#include "include/merge/graw.h"
#include "include/common/progress_reporter.h"

namespace atflow {

/// @brief Result type of checking single asad's data
enum class AsadResultType {
	/// @brief asad's data is complete and continuous
	Pass,
	/// @brief asad's data is broken, invalid meta type or frame type
	Broken,
	/// @brief data is incomplete, event count less than other asad
	Incomplete,
	/// @brief event id missing
	Missing,
};

/// @brief Convert AsadResultType to string
/// @param[in] type AsadResultType
/// @returns String representation of AsadResultType
std::string AsadResultTypeToString(const AsadResultType &type);


/// @brief Result of checking single asad's data
struct CheckAsadResult {
	// Cobo number
	int cobo;
	// Asad number
	int asad;
	// Event id
	int event;
	// Result type
	AsadResultType type;
	// size of files
	size_t size;
};

/// @brief Result of checking graw file
struct CheckGrawResult {
	// pass or not
	bool pass;
	// Results of each asad
	CheckAsadResult asad_results[42];
	// error ones
	std::vector<int> which;
};

class GrawChecker {
public:
	/// @brief Constructor
	/// @param[in] execution_id execution identifier
	/// @param[in] workspace_dir workspace directory
	/// @param[in] graw_dir graw directory
	/// @param[in] run run number
	/// @param[in] progress_reporter optional progress reporter (nullptr for no progress reporting)
	GrawChecker(
		const std::string &execution_id,
		const std::filesystem::path &workspace_dir,
		const std::filesystem::path &graw_dir,
		int run,
		std::unique_ptr<ProgressReporter> progress_reporter = nullptr
	);

	/// @brief Default destructor
	~GrawChecker() = default;

	/// @brief Check graw file
	/// @returns CheckGrawResult
	CheckGrawResult Check();
private:
	// execution identifier
	std::string execution_id_;
	// workspace directory
	std::filesystem::path workspace_dir_;
	// Graw directory
	std::filesystem::path graw_dir_;
	// run number
	int run_;
	// progress reporter (nullable)
	std::unique_ptr<ProgressReporter> progress_reporter_;
	// total size of graw files
	size_t total_size_;
	// event counts
	int event_counts_[42];
	// first event's id
	int start_event_[42];
	// last event's id
	int end_event_[42];
	// file not broken
	bool good_[42];
	// event id is continuous
	bool continuous_[42];
	// file is complete
	bool complete_[42];
	// log stream for normal logging
	std::stringstream log_stream_;
	// bad event set for unique bad event IDs
	std::set<int> bad_events_;

	/// @brief Check single asad's data
	/// @param[in] cobo cobo number
	/// @param[in] asad asad number
	/// @returns CheckAsadResult
	CheckAsadResult CheckAsad(int cobo, int asad);

	/// @brief Check event id is continuous
	/// @param[in] ids event ids
	void CheckEventId(int *id_list, CheckGrawResult &result, bool max = true);

	/// @brief Record results
	void Record() const;
};

}


#endif
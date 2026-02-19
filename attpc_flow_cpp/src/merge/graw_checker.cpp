#include "include/merge/graw_checker.h"
#include "include/common/statistics.h"

#include <algorithm>
#include <iostream>
#include <sstream>

namespace atflow {

std::string AsadResultTypeToString(const AsadResultType &type) {
	switch (type) {
		case AsadResultType::Pass: return "Pass";
		case AsadResultType::Broken: return "Broken";
		case AsadResultType::Incomplete: return "Incomplete";
		case AsadResultType::InContinuous: return "InContinuous";
		default: return "Unknown";
	}
}

GrawChecker::GrawChecker(
	const std::string &execution_id,
	const std::filesystem::path &workspace_dir,
	const std::filesystem::path &graw_dir,
	int run,
	std::unique_ptr<ProgressReporter> progress_reporter
)
: execution_id_(execution_id)
, workspace_dir_(workspace_dir)
, graw_dir_(graw_dir)
, run_(run)
, progress_reporter_(std::move(progress_reporter)) {
	// get total size
	total_size_ = 0;
	std::stringstream ss;
	ss << std::setw(4) << std::setfill('0')
		<< "run_" << run_;
	std::filesystem::path run_dir = graw_dir_ / ss.str();
	for (int cobo = 0; cobo < 11; ++cobo) {
		// Cobo directory
		std::filesystem::path cobo_dir = run_dir / ("mm" + std::to_string(cobo));
		if (!std::filesystem::exists(cobo_dir)) continue;
		// loop files
		for (const auto &file : std::filesystem::directory_iterator(cobo_dir)) {
			if (file.path().extension() != ".graw") continue;
			total_size_ += file.file_size();
		}
	}
	for (int idx = 0; idx < 42; ++idx) {
		event_counts_[idx] = 0;
		start_event_[idx] = -1;
		end_event_[idx] = -1;
		good_[idx] = true;
		continuous_[idx] = true;
		complete_[idx] = true;
	}
}

CheckGrawResult GrawChecker::Check() {
	// initialize result
	CheckGrawResult result;
	result.pass = true;
	result.msg = "";

	// report start if progress reporter is available
	if (progress_reporter_) {
		progress_reporter_->ReportStart();
		progress_reporter_->ReportProgress(0);
	}

	// check size
	size_t check_size = 0;
	// check each asad
	for (int idx = 0; idx < 42; ++idx) {
		int cobo = idx / 4;
		int asad = idx % 4;
		CheckAsadResult asad_result = CheckAsad(cobo, asad);
		result.asad_results[idx] = asad_result;
		if (asad_result.type != AsadResultType::Pass) {
			result.which.push_back(idx);
			result.pass = false;
		}
		result.msg += asad_result.msg;
		// check size
		check_size += asad_result.size;

		// report progress if progress reporter is available
		if (progress_reporter_ && total_size_ > 0) {
			int percentage = static_cast<int>(check_size * 100.0 / total_size_);
			progress_reporter_->ReportProgress(percentage);
		}
	}

	// report completion if progress reporter is available
	if (progress_reporter_) {
		progress_reporter_->ReportProgress(100);
		progress_reporter_->ReportFinish();
	}

	CheckEventId(start_event_, result);
	CheckEventId(end_event_, result);
	// record
	Record();
	// record result to log file
	std::filesystem::path log_dir = workspace_dir_ / "log";
	if (!std::filesystem::exists(log_dir)) {
		std::filesystem::create_directories(log_dir);
	}
	std::string log_name =
		"graw-event-id-check-" + std::to_string(run_) + ".log";
	std::filesystem::path log_path(log_dir / log_name);
	std::ofstream log(log_path);
	if (result.pass) {
		log << "Pass\n";
	} else {
		log << result.msg << "\n";
	}
	log.close();
	return result;
}


CheckAsadResult GrawChecker::CheckAsad(int cobo, int asad) {
	// result
	CheckAsadResult result{
		.cobo = cobo,
		.asad = asad,
		.event = -1,
		.type = AsadResultType::Pass,
		.size = 0,
		.msg = ""
	};
	// index
	int idx = cobo*4+asad;
	// file name
	std::stringstream ss;
	ss << std::setw(4) << std::setfill('0')
		<< "run_" << run_
		<< "/mm" << cobo;
	// Cobo directory
	std::filesystem::path cobo_dir = graw_dir_ / ss.str();
	if (!std::filesystem::exists(cobo_dir)) {
		result.type = AsadResultType::Broken;
		return result;
	}
	// files for this cobo, asad
	std::vector<std::filesystem::path> files;
	for (const auto &file : std::filesystem::directory_iterator(cobo_dir)) {
		std::string asad_str = "AsAd" + std::to_string(asad);
		if (
			file.path().extension() == ".graw"
			&& file.path().string().find(asad_str) != std::string::npos
		) {
			files.push_back(file.path());
		}
	}
	// sort files by name
	std::sort(
		files.begin(),
		files.end(),
		[](
			const std::filesystem::path &a,
			const std::filesystem::path &b
		) {
			return a.string() < b.string();
		}
	);
	// loop events
	for (const auto &file : files) {
		// open file
		GrawFrameHeaderReader reader(file);
		while (reader.Read()) {
			// check header
			if (
				reader.MetaType() != 8
				|| reader.FrameType() != 1
				|| reader.ItemSize() != 4
			) {
				good_[idx] = false;
				result.type = AsadResultType::Broken;
				result.msg += "Broken," + std::to_string(end_event_[idx]) + "\n";
				return result;
			}
			// increase event count
			++event_counts_[idx];
			// event id
			int event_id = reader.EventId();
			// check event id
			if (start_event_[idx] == -1) {
				// get start event
				start_event_[idx] = event_id;
			} else if (event_id != end_event_[idx] + 1) {
				// check if event id is continuous
				continuous_[idx] = false;
				result.type = AsadResultType::InContinuous;
				result.event = end_event_[idx];
				result.msg += "InContinuous," + std::to_string(end_event_[idx]) + "\n";
			}
			// update event count
			end_event_[idx] = event_id;
		}
		// check size
		result.size += std::filesystem::file_size(file);
	}

	return result;
}


void GrawChecker::CheckEventId(int *id_list, CheckGrawResult &result) {
	// get max events
	int max_events = id_list[0];
	for (int idx = 0; idx < 42; ++idx) {
		if (result.asad_results[idx].type != AsadResultType::Pass) {
			continue;
		}
		if (id_list[idx] > max_events) {
			max_events = id_list[idx];
		}
	}
	// check if event count less than max_events
	for (int idx = 0; idx < 42; ++idx) {
		if (result.asad_results[idx].type != AsadResultType::Pass) {
			continue;
		}
		if (id_list[idx] != max_events) {
			complete_[idx] = false;
			result.asad_results[idx].type = AsadResultType::Incomplete;
			result.which.push_back(idx);
			result.pass = false;
			result.msg += "Incomplete\n";
		}
	}
}


void GrawChecker::Record() const {
	// record result to statistics file
	std::filesystem::path statistics_path(
		workspace_dir_ / "statistics" / "merge_check.csv"
	);
	Statistics statistics(
		statistics_path,
		[](const Row &row) {
			int run = row.As<int>(0);
			int cobo = row.As<int>(2);
			int asad = row.As<int>(3);
			int key = (run<<6) | (cobo<<2) | asad;
			return key;
		}
	);
	statistics.SetHeader("Run,Execution,Cobo,Asad,events,start,end,good,continuous,complete");
	for (int idx = 0; idx < 42; ++idx) {
		int cobo = idx / 4;
		int asad = idx % 4;
		statistics.AddEntry()
			<< run_ << execution_id_ << cobo << asad
			<< event_counts_[idx] << start_event_[idx] << end_event_[idx]
			<< (good_[idx] ? "true" : "false")
			<< (continuous_[idx] ? "true" : "false")
			<< (complete_[idx] ? "true" : "false");
	}
	statistics.Write();
}

}
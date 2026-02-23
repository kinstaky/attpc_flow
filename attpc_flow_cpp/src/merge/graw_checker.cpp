#include "include/merge/graw_checker.h"
#include "include/common/file_lock.h"

#include <SQLiteCpp/SQLiteCpp.h>

#include <algorithm>
#include <iostream>
#include <sstream>
#include <fstream>

namespace atflow {

std::string AsadResultTypeToString(const AsadResultType &type) {
	switch (type) {
		case AsadResultType::Pass: return "Pass";
		case AsadResultType::Broken: return "Broken";
		case AsadResultType::Incomplete: return "Incomplete";
		case AsadResultType::Missing: return "Missing";
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

	CheckEventId(start_event_, result, false);
	CheckEventId(end_event_, result, true);
	// record
	Record();
	// record result to log stream
	if (result.pass) log_stream_ << "Pass\n";
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
		bool first = true;
		while (reader.Read()) {
			// check header
			if (
				reader.MetaType() != 8
				|| reader.FrameType() != 1
				|| reader.ItemSize() != 4
			) {
				good_[idx] = false;
				result.type = AsadResultType::Broken;
				log_stream_ << "Broken," << idx << "," << end_event_[idx] << "\n";
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
				result.type = AsadResultType::Missing;
				result.event = end_event_[idx];
				log_stream_ << "Missing," << idx << "," << end_event_[idx] << "\n";
				bad_events_.insert(end_event_[idx]);
			}
			// update event count
			end_event_[idx] = event_id;
			// record first event
			if (first) {
				first = false;
				log_stream_ << "File first," << idx << "," <<  event_id << "\n";
			}
		}
		// check size
		result.size += std::filesystem::file_size(file);
	}

	return result;
}


void GrawChecker::CheckEventId(
	int *id_list,
	CheckGrawResult &result,
	bool max
) {
	// get max events
	int ref_event = id_list[0];
	for (int idx = 0; idx < 42; ++idx) {
		if (result.asad_results[idx].type != AsadResultType::Pass) {
			continue;
		}
		if (max && id_list[idx] > ref_event) {
			ref_event = id_list[idx];
		} else if (!max && id_list[idx] < ref_event) {
			ref_event = id_list[idx];
		}
	}
	// check if event count less than max_events
	for (int idx = 0; idx < 42; ++idx) {
		if (result.asad_results[idx].type != AsadResultType::Pass) {
			continue;
		}
		if (id_list[idx] != ref_event) {
			complete_[idx] = false;
			result.asad_results[idx].type = AsadResultType::Incomplete;
			result.which.push_back(idx);
			result.pass = false;
			log_stream_ << "Incomplete," << idx << "\n";
			if (max) {
				for (int id = id_list[idx]+1; id <= ref_event; ++id) {
					bad_events_.insert(id);
				}
			} else {
				for (int id = ref_event; id < id_list[idx]; ++id) {
					bad_events_.insert(id);
				}
			}
		}
	}
}


void GrawChecker::Record() const {
	// record result to summary database
	std::filesystem::path summary_path(
		workspace_dir_ / "summary" / "merge_check.db"
	);
	std::filesystem::create_directories(summary_path.parent_path());

	SQLite::Database db(
		summary_path.string(),
		SQLite::OPEN_READWRITE | SQLite::OPEN_CREATE
	);
	db.exec("PRAGMA journal_mode=WAL");
	SQLite::Transaction transaction(db);
	db.exec(
		"CREATE TABLE IF NOT EXISTS summary ("
		"run INTEGER NOT NULL,"
		"cobo INTEGER NOT NULL,"
		"asad INTEGER NOT NULL,"
		"events INTEGER NOT NULL,"
		"start INTEGER NOT NULL,"
		"end INTEGER NOT NULL,"
		"good INTEGER NOT NULL,"
		"continuous INTEGER NOT NULL,"
		"complete INTEGER NOT NULL,"
		"PRIMARY KEY (run, cobo, asad)"
		")"
	);

	SQLite::Statement insert(
		db,
		"INSERT OR REPLACE INTO summary "
		"(run, cobo, asad, events, start, end, good, continuous, complete) "
		"VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
	);

	for (int idx = 0; idx < 42; ++idx) {
		int cobo = idx / 4;
		int asad = idx % 4;
		insert.bind(1, run_);
		insert.bind(2, cobo);
		insert.bind(3, asad);
		insert.bind(4, event_counts_[idx]);
		insert.bind(5, start_event_[idx]);
		insert.bind(6, end_event_[idx]);
		insert.bind(7, good_[idx] ? 1 : 0);
		insert.bind(8, continuous_[idx] ? 1 : 0);
		insert.bind(9, complete_[idx] ? 1 : 0);
		insert.exec();
		insert.reset();
		insert.clearBindings();
	}

	transaction.commit();

	// Write normal log
	if (!log_stream_.str().empty()) {
		std::filesystem::path log_path =
			workspace_dir_
			/ "log"
			/ ("graw_event_id_" + std::to_string(run_) + ".log");
		std::filesystem::create_directories(log_path.parent_path());
		std::ofstream log_file(log_path);
		if (log_file.is_open()) {
			log_file << log_stream_.str();
			log_file.close();
		}
	}

	// Write bad events with file lock
	if (!bad_events_.empty()) {
		std::filesystem::path bad_event_path =
			workspace_dir_
			/ "run"
			/ ("bad_event_" + std::to_string(run_) + ".txt");
		std::filesystem::create_directories(bad_event_path.parent_path());

		// Create lock file path
		std::filesystem::path lock_path =
			bad_event_path.parent_path()
			/ (bad_event_path.stem().string() + ".lock");
		// Use FileLock on lock file for thread-safe writing
		FileLock lock(lock_path.c_str());
		// Open data file for writing (overwrite mode)
		std::ofstream bad_event_file(bad_event_path);
		if (bad_event_file.is_open()) {
			// Copy and sort bad events before writing
			std::vector<int> sorted_events(bad_events_.begin(), bad_events_.end());
			std::sort(sorted_events.begin(), sorted_events.end());
			for (int event_id : sorted_events) {
				bad_event_file << event_id << "\n";
			}
			bad_event_file.close();
		}
	}
}

}
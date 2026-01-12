#include "include/merge/graw_checker.h"

#include <algorithm>
#include <iostream>
#include <sstream>

namespace flow {

std::string AsadResultTypeToString(const AsadResultType &type) {
	switch (type) {
		case AsadResultType::Pass: return "Pass";
		case AsadResultType::Broken: return "Broken";
		case AsadResultType::Incomplete: return "Incomplete";
		case AsadResultType::InContinuous: return "InContinuous";
		default: return "Unknown";
	}
}

GrawChecker::GrawChecker(const std::filesystem::path &path, int run)
: graw_dir_(path)
, run_(run) {
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
	CheckGrawResult result;
	result.pass = true;
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
	}
	// get max events
	int max_events = *(std::max_element(event_counts_, event_counts_+42));
	// check if event count less than max_events
	for (int idx = 0; idx < 42; ++idx) {
		if (result.asad_results[idx].type != AsadResultType::Pass) {
			continue;
		}
		if (event_counts_[idx] != max_events) {
			complete_[idx] = false;
			result.asad_results[idx].type = AsadResultType::Incomplete;
			result.which.push_back(idx);
			result.pass = false;
		}
	}
	// print results
	std::cout << "Cobo,Asad,events,start,end,good,complete,continuous\n";
	for (int idx = 0; idx < 42; ++idx) {
		std::cout << idx/4 << "," << idx%4 << ","
			<< event_counts_[idx] << ","
			<< start_event_[idx] << ","
			<< end_event_[idx] << ","
			<< (good_[idx] ? "true" : "false") << ","
			<< (complete_[idx] ? "true" : "false") << ","
			<< (continuous_[idx] ? "true" : "false")
			<< "\n";
	}
	// std::filesystem::path statistics_path;
	// Statistics statistics(
	// 	statistics_path,
	// 	[](const auto &row){
	// 		int run = row.as<int>(0);
	// 		int cobo = row.as<int>(1);
	// 		int asad = row.as<int>(2);
	// 		key = (run<<6) | (cobo<<2) | asad;
	// 		return key;
	// 	}
	// );
	// statistics.SetHeader("Run,Cobo,Asad,events,start,end,good,continuous,complete");
	// for (int idx = 0; idx < 42; ++idx) {
	// 	int cobo = idx / 4;
	// 	int asad = idx % 4;
	// 	statistics.AddEntry()
	// 		<< run_ << cobo << asad
	// 		<< event_counts_[idx] << start_event_[idx] << end_event_[idx]
	// 		<< good_[idx] << continuous_[idx] << complete_[idx];
	// }
	// statistics.Write();
	return result;
}


CheckAsadResult GrawChecker::CheckAsad(int cobo, int asad) {
	// result
	CheckAsadResult result{
		.cobo = cobo,
		.asad = asad,
		.event = -1,
		.type = AsadResultType::Pass,
	};
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
				good_[cobo*4+asad] = false;
				result.type = AsadResultType::Broken;
				return result;
			}
			// increase event count
			++event_counts_[cobo*4+asad];
			// event id
			int event_id = reader.EventId();
			// check event id
			if (start_event_[cobo*4+asad] == -1) {
				// get start event
				start_event_[cobo*4+asad] = event_id;
			} else if (event_id != end_event_[cobo*4+asad] + 1) {
				// check if event id is continuous
				continuous_[cobo*4+asad] = false;
				result.type = AsadResultType::InContinuous;
			}
			// update event count
			end_event_[cobo*4+asad] = event_id;
			result.event = event_id;
		}
	}

	return result;
}

}
#include <nanobind/nanobind.h>
#include <nanobind/stl/string.h>
#include <memory>
#include "include/merge/graw_checker.h"

#include "include/common/zmq_progress_reporter.h"
#include "include/common/text_progress_reporter.h"

namespace nb = nanobind;
using namespace nb::literals;

std::string check_graw_event_id(
	std::string execution_id,
	int task_id,
	std::string workspace_dir,
	std::string graw_dir,
	int run
) {
	std::unique_ptr<atflow::ProgressReporter> progress_reporter = nullptr;

	if (task_id >= 0) {
		// Workflow/server mode: use ZMQ progress reporter
		progress_reporter = std::make_unique<atflow::ZmqProgressReporter>(
			execution_id, task_id, "ipc://@attpc_flow_zmq"
		);
	} else if (task_id == -1) {
		// CLI node mode: use text progress reporter
		progress_reporter = std::make_unique<atflow::TextProgressReporter>(
			"Cheking graw files"
		);
	}

	atflow::GrawChecker checker(
		execution_id,
		workspace_dir,
		graw_dir,
		run,
		std::move(progress_reporter)
	);
	atflow::CheckGrawResult result = checker.Check();
	std::string summary = result.pass ? "pass" : "";
	if (!result.pass) {
		for (int idx : result.which) {
			const auto& asad_result = result.asad_results[idx];
			if (asad_result.type == atflow::AsadResultType::Pass) {
				continue;
			}
			if (asad_result.type == atflow::AsadResultType::Broken) {
				summary = "broken";
				break;
			} else if (
				asad_result.type == atflow::AsadResultType::Incomplete
			) {
				summary = "incomplete";
			} else if (
				asad_result.type == atflow::AsadResultType::Missing
				&& summary == ""
			) {
				summary = "missing";
			}
		}
	}
	return summary;
}

NB_MODULE(_lib, m) {
	m.doc() = "Python extensions written in C++ for attpc flow.";
	m.def(
		"check_graw_event_id",
		&check_graw_event_id,
		"execution_id"_a,
		"task_id"_a,
		"workspace_dir"_a,
		"graw_dir"_a,
		"run"_a,
		"This function check single run graw files."
	);
}
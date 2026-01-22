#include <nanobind/nanobind.h>
#include <nanobind/stl/string.h>
#include <memory>
#include "include/merge/graw_checker.h"

#include "include/common/zmq_progress_reporter.h"

namespace nb = nanobind;
using namespace nb::literals;

bool check_graw_event_id(
	int task_id,
	std::string workspace_dir,
	std::string graw_dir,
	int run
) {
	std::unique_ptr<atflow::ProgressReporter> progress_reporter = nullptr;

	if (task_id >= 0) {
		progress_reporter = std::make_unique<atflow::ZmqProgressReporter>(
			task_id, "ipc://@attpc_flow_zmq"
		);
	}

	atflow::GrawChecker checker(
		workspace_dir,
		graw_dir,
		run,
		std::move(progress_reporter)
	);
	atflow::CheckGrawResult result = checker.Check();
	return result.pass;
}

NB_MODULE(attpc_flow_ext, m) {
	m.doc() = "Python extensions written in C++ for attpc flow.";
	m.def(
		"check_graw_event_id",
		&check_graw_event_id,
		"task_id"_a, "workspace_dir"_a, "graw_dir"_a, "run"_a,
		"This function check single run graw files."
	);
}
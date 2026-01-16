#include <nanobind/nanobind.h>
#include <nanobind/stl/string.h>
#include "include/merge/graw_checker.h"

namespace nb = nanobind;
using namespace nb::literals;

bool check_graw_event_id(std::string graw_dir, std::string workspace_dir, int run) {
	atflow::GrawChecker checker(graw_dir, workspace_dir, run);
	atflow::CheckGrawResult result = checker.Check();
	return result.pass;
}

NB_MODULE(attpc_flow_ext, m) {
	m.doc() = "Python extensions written in C++ for attpc flow.";
	m.def(
		"check_graw_event_id",
		&check_graw_event_id,
		"graw_dir"_a, "workspace_dir"_a, "run"_a,
		"This function check single run graw files."
	);
}
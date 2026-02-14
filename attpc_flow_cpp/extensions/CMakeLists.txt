nanobind_add_module(_lib STABLE_ABI NB_STATIC LTO lib.cpp)
target_link_libraries(_lib PUBLIC graw_checker zmq_progress_reporter)

install(TARGETS _lib LIBRARY DESTINATION ${SKBUILD_PROJECT_NAME})

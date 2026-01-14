add_library(graw graw.cpp)
target_include_directories(graw PUBLIC ${PROJECT_SOURCE_DIR})
set_target_properties(graw PROPERTIES POSITION_INDEPENDENT_CODE ON)

add_library(graw_checker graw_checker.cpp)
target_link_libraries(graw_checker PUBLIC graw)
set_target_properties(graw_checker PROPERTIES POSITION_INDEPENDENT_CODE ON)
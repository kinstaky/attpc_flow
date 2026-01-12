add_library(graw graw.cpp)
target_include_directories(graw PUBLIC ${PROJECT_SOURCE_DIR})

add_library(graw_checker graw_checker.cpp)
target_link_libraries(graw_checker PUBLIC graw)

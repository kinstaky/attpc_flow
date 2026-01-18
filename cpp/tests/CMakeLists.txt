# Google Test via FetchContent
include(FetchContent)
FetchContent_Declare(
  googletest
  URL https://github.com/google/googletest/archive/52eb8108c5bdec04579160ae17225d66034bd723.zip
)
# For Windows: Prevent overriding the parent project's compiler/linker settings
set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(googletest)

enable_testing()
include(GoogleTest)

# Statistics tests
add_executable(statistics_test statistics_test.cpp)
target_include_directories(statistics_test PRIVATE ${PROJECT_SOURCE_DIR})
target_link_libraries(statistics_test PRIVATE gtest_main)
gtest_discover_tests(statistics_test)

# FileLock tests
add_executable(file_lock_test file_lock_test.cpp)
target_include_directories(file_lock_test PRIVATE ${PROJECT_SOURCE_DIR})
target_link_libraries(file_lock_test PRIVATE gtest_main)
gtest_discover_tests(file_lock_test)

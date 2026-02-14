#include "include/common/file_lock.h"

#include <gtest/gtest.h>
#include <filesystem>
#include <fstream>
#include <sys/file.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/wait.h>
#include <errno.h>
#include <string>
#include <chrono>
#include <thread>

namespace atflow {

// Test fixture for FileLock tests
class FileLockTest : public ::testing::Test {
protected:
	void SetUp() override {
		// Create temporary directory for each test
		test_dir_ = std::filesystem::temp_directory_path() /
		            ("filelock_test_" + std::to_string(getpid()));
		std::filesystem::create_directories(test_dir_);
		lock_file_ = test_dir_ / "test.lock";
	}

	void TearDown() override {
		// Clean up test directory
		if (std::filesystem::exists(test_dir_)) {
			std::filesystem::remove_all(test_dir_);
		}
	}

	std::filesystem::path test_dir_;
	std::filesystem::path lock_file_;
};

// Test 1: Lock Acquisition
TEST_F(FileLockTest, TestLockAcquisition) {
	// FileLock should acquire exclusive lock on construction
	{
		FileLock lock(lock_file_.string().c_str());

		// Verify lock file was created
		ASSERT_TRUE(std::filesystem::exists(lock_file_));

		// Try to acquire lock from another file descriptor (should fail with EWOULDBLOCK)
		int fd2 = open(lock_file_.string().c_str(), O_RDWR);
		ASSERT_NE(fd2, -1);

		// Try to acquire non-blocking lock (should fail because lock is held)
		int result = flock(fd2, LOCK_EX | LOCK_NB);
		ASSERT_EQ(result, -1);
		ASSERT_EQ(errno, EWOULDBLOCK);

		close(fd2);
	}

	// After FileLock destruction, lock should be released
	int fd3 = open(lock_file_.string().c_str(), O_RDWR);
	ASSERT_NE(fd3, -1);

	// Now we should be able to acquire the lock
	int result = flock(fd3, LOCK_EX | LOCK_NB);
	ASSERT_EQ(result, 0);

	flock(fd3, LOCK_UN);
	close(fd3);
}

// Test 2: Lock File Creation
TEST_F(FileLockTest, TestLockFileCreation) {
	// Verify file doesn't exist initially
	ASSERT_FALSE(std::filesystem::exists(lock_file_));

	// Create FileLock - should create file
	{
		FileLock lock(lock_file_.string().c_str());
		ASSERT_TRUE(std::filesystem::exists(lock_file_));
	}

	// File should still exist after lock release
	ASSERT_TRUE(std::filesystem::exists(lock_file_));

	// Verify file permissions (should be 0644)
	std::filesystem::perms perms = std::filesystem::status(lock_file_).permissions();
	// Note: permissions() returns a bitmask, we check that it's readable/writable by owner
	ASSERT_TRUE((perms & std::filesystem::perms::owner_read) != std::filesystem::perms::none);
	ASSERT_TRUE((perms & std::filesystem::perms::owner_write) != std::filesystem::perms::none);
}

// Test 3: Concurrent Access - Multiple Processes
TEST_F(FileLockTest, TestConcurrentAccess) {
	// Create a shared data file to test concurrent writes
	std::filesystem::path data_file = test_dir_ / "data.txt";

	// Initialize data file
	std::ofstream init(data_file);
	init << "0";
	init.close();

	// Fork a child process
	pid_t pid = fork();

	if (pid == 0) {
		// Child process
		FileLock lock(lock_file_.string().c_str());

		// Read, increment, and write
		std::ifstream in(data_file);
		int value;
		in >> value;
		in.close();

		// Simulate some work
		std::this_thread::sleep_for(std::chrono::milliseconds(100));

		value++;

		std::ofstream out(data_file);
		out << value;
		out.close();

		_exit(0);
	} else if (pid > 0) {
		// Parent process
		// Wait a bit to ensure child starts first
		std::this_thread::sleep_for(std::chrono::milliseconds(10));

		// Try to acquire lock (should block until child releases)
		FileLock lock(lock_file_.string().c_str());

		// Read, increment, and write
		std::ifstream in(data_file);
		int value;
		in >> value;
		in.close();

		value++;

		std::ofstream out(data_file);
		out << value;
		out.close();

		// Wait for child to finish
		int status;
		waitpid(pid, &status, 0);

		// Verify final value (should be 2: child incremented to 1, parent to 2)
		std::ifstream final_in(data_file);
		int final_value;
		final_in >> final_value;
		final_in.close();

		ASSERT_EQ(final_value, 2);
	} else {
		// Fork failed
		FAIL() << "fork() failed";
	}
}

// Test 4: Lock on Non-Existent File
TEST_F(FileLockTest, TestLockOnNonExistentFile) {
	// Verify file doesn't exist
	ASSERT_FALSE(std::filesystem::exists(lock_file_));

	// Create FileLock - should create the file
	{
		FileLock lock(lock_file_.string().c_str());
		ASSERT_TRUE(std::filesystem::exists(lock_file_));

		// Verify lock is actually held
		int fd2 = open(lock_file_.string().c_str(), O_RDWR);
		int result = flock(fd2, LOCK_EX | LOCK_NB);
		ASSERT_EQ(result, -1);
		ASSERT_EQ(errno, EWOULDBLOCK);
		close(fd2);
	}
}

// Test 5: Multiple FileLock Instances on Same File (Sequential)
TEST_F(FileLockTest, TestMultipleFileLockInstancesSequential) {
	// Create first lock
	{
		FileLock lock1(lock_file_.string().c_str());
		ASSERT_TRUE(std::filesystem::exists(lock_file_));
	}

	// Create second lock after first is destroyed
	{
		FileLock lock2(lock_file_.string().c_str());
		ASSERT_TRUE(std::filesystem::exists(lock_file_));
	}

	// Both should work sequentially
	ASSERT_TRUE(true);
}

// Test 6: Verify Exclusive Lock Behavior
TEST_F(FileLockTest, TestExclusiveLockBehavior) {
	FileLock lock(lock_file_.string().c_str());

	// Try to open file with another descriptor
	int fd2 = open(lock_file_.string().c_str(), O_RDWR);
	ASSERT_NE(fd2, -1);

	// Try non-blocking exclusive lock (should fail)
	int result = flock(fd2, LOCK_EX | LOCK_NB);
	ASSERT_EQ(result, -1);
	ASSERT_EQ(errno, EWOULDBLOCK);

	// Try non-blocking shared lock (should also fail - exclusive lock prevents both)
	result = flock(fd2, LOCK_SH | LOCK_NB);
	ASSERT_EQ(result, -1);
	ASSERT_EQ(errno, EWOULDBLOCK);

	close(fd2);
}

// Test 7: Concurrent Access - Blocking Behavior
TEST_F(FileLockTest, TestConcurrentAccessBlocking) {
	pid_t pid = fork();

	if (pid == 0) {
		// Child process: acquire lock and hold it for a while
		FileLock lock(lock_file_.string().c_str());
		std::this_thread::sleep_for(std::chrono::milliseconds(200));
		_exit(0);
	} else if (pid > 0) {
		// Parent process: wait a bit, then try to acquire lock
		std::this_thread::sleep_for(std::chrono::milliseconds(50));

		// Measure time to acquire lock (should block until child releases)
		auto start = std::chrono::steady_clock::now();

		FileLock lock(lock_file_.string().c_str());

		auto end = std::chrono::steady_clock::now();
		auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start);

		// Should have blocked for at least 100ms (child holds for 200ms, we wait 50ms)
		ASSERT_GE(duration.count(), 100);

		// Wait for child
		int status;
		waitpid(pid, &status, 0);
	} else {
		FAIL() << "fork() failed";
	}
}

} // namespace atflow

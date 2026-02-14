#include "include/common/statistics.h"

#include <gtest/gtest.h>
#include <filesystem>
#include <fstream>
#include <functional>
#include <sstream>
#include <string>
#include <vector>

namespace atflow {

// Helper function to read file content
std::string ReadFileContent(const std::filesystem::path& path) {
	std::ifstream file(path);
	if (!file.is_open()) {
		return "";
	}
	std::stringstream buffer;
	buffer << file.rdbuf();
	return buffer.str();
}

// Helper function to count lines in file
size_t CountLines(const std::filesystem::path& path) {
	std::ifstream file(path);
	if (!file.is_open()) {
		return 0;
	}
	size_t count = 0;
	std::string line;
	while (std::getline(file, line)) {
		count++;
	}
	return count;
}

// Test fixture for Statistics tests
class StatisticsTest : public ::testing::Test {
protected:
	void SetUp() override {
		// Create temporary directory for each test
		test_dir_ = std::filesystem::temp_directory_path() /
		            ("statistics_test_" + std::to_string(getpid()));
		std::filesystem::create_directories(test_dir_);
		test_file_ = test_dir_ / "test_stats.csv";
	}

	void TearDown() override {
		// Clean up test directory
		if (std::filesystem::exists(test_dir_)) {
			std::filesystem::remove_all(test_dir_);
		}
	}

	std::filesystem::path test_dir_;
	std::filesystem::path test_file_;

	// Simple key function: use first column as integer key
	auto GetKeyFunction() {
		return [](const Row &row) {
			return row.As<int>(0);
		};
	}
};

// Test 1: File Creation Test
TEST_F(StatisticsTest, TestFileCreation) {
	// Verify file doesn't exist initially
	ASSERT_FALSE(std::filesystem::exists(test_file_));

	// Create Statistics instance - should create directory
	Statistics stats(test_file_, GetKeyFunction());
	stats.SetHeader("Key,Value");

	// Directory should be created
	ASSERT_TRUE(std::filesystem::exists(test_file_.parent_path()));

	// File should not exist yet (only created on Write)
	ASSERT_FALSE(std::filesystem::exists(test_file_));

	// Add entry and write
	stats.AddEntry() << 1 << "test1";
	stats.Write();

	// File should now exist
	ASSERT_TRUE(std::filesystem::exists(test_file_));

	// Verify file content
	std::string content = ReadFileContent(test_file_);
	ASSERT_NE(content.find("Key,Value"), std::string::npos);
	ASSERT_NE(content.find("1,test1"), std::string::npos);
}

// Test 2: Read Existing Items and Write Back
TEST_F(StatisticsTest, TestReadExistingFile) {
	// Create a test file with known content
	std::ofstream out(test_file_);
	out << "Key,Value,Extra\n";
	out << "1,value1,extra1\n";
	out << "2,value2,extra2\n";
	out << "3,value3,extra3\n";
	out.close();

	// Initialize Statistics with existing file
	Statistics stats(test_file_, GetKeyFunction());

	// Verify header was read (we can't access it directly, but we can verify via Write)
	stats.SetHeader("Key,Value,Extra");

	// Add a new entry
	stats.AddEntry() << 4 << "value4" << "extra4";
	stats.Write();

	// Verify file was updated correctly
	std::string content = ReadFileContent(test_file_);
	ASSERT_NE(content.find("Key,Value,Extra"), std::string::npos);
	ASSERT_NE(content.find("1,value1,extra1"), std::string::npos);
	ASSERT_NE(content.find("2,value2,extra2"), std::string::npos);
	ASSERT_NE(content.find("3,value3,extra3"), std::string::npos);
	ASSERT_NE(content.find("4,value4,extra4"), std::string::npos);

	// Verify we have 5 lines (header + 4 data rows)
	ASSERT_EQ(CountLines(test_file_), 5);
}

// Test 2b: Verify CSV parsing
TEST_F(StatisticsTest, TestCSVParsing) {
	// Create a test file with CSV content
	std::ofstream out(test_file_);
	out << "Key,Value\n";
	out << "10,value10\n";
	out << "20,value20\n";
	out.close();

	// Initialize Statistics
	Statistics stats(test_file_, GetKeyFunction());

	// Modify an existing entry
	stats.AddEntry() << 10 << "modified_value10";
	stats.Write();

	// Verify the entry was updated
	std::string content = ReadFileContent(test_file_);
	ASSERT_NE(content.find("10,modified_value10"), std::string::npos);
	ASSERT_EQ(content.find("10,value10"), std::string::npos); // Old value should be gone
}

// Test 3: AddEntry() Behavior - Add New Key
TEST_F(StatisticsTest, TestAddEntryNewKey) {
	// Create initial file
	std::ofstream out(test_file_);
	out << "Key,Value\n";
	out << "1,value1\n";
	out << "3,value3\n";
	out.close();

	Statistics stats(test_file_, GetKeyFunction());

	// Add new entry with key 2 (should insert between 1 and 3)
	stats.AddEntry() << 2 << "value2";
	stats.Write();

	// Verify insertion
	std::string content = ReadFileContent(test_file_);

	// Find positions of each entry
	size_t pos1 = content.find("1,value1");
	size_t pos2 = content.find("2,value2");
	size_t pos3 = content.find("3,value3");

	ASSERT_NE(pos1, std::string::npos);
	ASSERT_NE(pos2, std::string::npos);
	ASSERT_NE(pos3, std::string::npos);

	// Verify order: 1 < 2 < 3
	ASSERT_LT(pos1, pos2);
	ASSERT_LT(pos2, pos3);
}

// Test 3b: AddEntry() Behavior - Replace Existing Key
TEST_F(StatisticsTest, TestAddEntryExistingKey) {
	// Create initial file
	std::ofstream out(test_file_);
	out << "Key,Value\n";
	out << "1,old_value1\n";
	out << "2,value2\n";
	out.close();

	Statistics stats(test_file_, GetKeyFunction());

	// Add entry with existing key 1 (should replace)
	stats.AddEntry() << 1 << "new_value1";
	stats.Write();

	// Verify replacement
	std::string content = ReadFileContent(test_file_);
	ASSERT_NE(content.find("1,new_value1"), std::string::npos);
	ASSERT_EQ(content.find("1,old_value1"), std::string::npos); // Old value should be gone

	// Verify other entries unchanged
	ASSERT_NE(content.find("2,value2"), std::string::npos);

	// Should still have 3 lines (header + 2 data rows)
	ASSERT_EQ(CountLines(test_file_), 3);
}

// Test 3c: Multiple AddEntry() calls before Write()
TEST_F(StatisticsTest, TestMultipleAddEntryBeforeWrite) {
	Statistics stats(test_file_, GetKeyFunction());
	stats.SetHeader("Key,Value");

	// Add multiple entries before writing
	stats.AddEntry() << 3 << "value3";
	stats.AddEntry() << 1 << "value1";
	stats.AddEntry() << 2 << "value2";
	stats.AddEntry() << 4 << "value4";

	stats.Write();

	// Verify all entries were written in sorted order
	std::string content = ReadFileContent(test_file_);

	size_t pos1 = content.find("1,value1");
	size_t pos2 = content.find("2,value2");
	size_t pos3 = content.find("3,value3");
	size_t pos4 = content.find("4,value4");

	ASSERT_NE(pos1, std::string::npos);
	ASSERT_NE(pos2, std::string::npos);
	ASSERT_NE(pos3, std::string::npos);
	ASSERT_NE(pos4, std::string::npos);

	// Verify sorted order
	ASSERT_LT(pos1, pos2);
	ASSERT_LT(pos2, pos3);
	ASSERT_LT(pos3, pos4);
}

// Test 4: Key-Based Ordering
TEST_F(StatisticsTest, TestKeyOrdering) {
	Statistics stats(test_file_, GetKeyFunction());
	stats.SetHeader("Key,Value");

	// Add entries in random order
	stats.AddEntry() << 50 << "value50";
	stats.AddEntry() << 10 << "value10";
	stats.AddEntry() << 30 << "value30";
	stats.AddEntry() << 20 << "value20";
	stats.AddEntry() << 40 << "value40";

	stats.Write();

	// Verify entries are written in sorted order
	std::string content = ReadFileContent(test_file_);
	std::istringstream iss(content);
	std::string header;
	std::getline(iss, header); // skip header

	std::vector<int> keys;
	std::string line;
	while (std::getline(iss, line)) {
		if (line.empty()) continue;
		std::istringstream line_stream(line);
		std::string key_str;
		std::getline(line_stream, key_str, ',');
		int key = std::stoi(key_str);
		keys.push_back(key);
	}
	ASSERT_EQ(keys.size(), 5);
	ASSERT_EQ(keys[0], 10);
	ASSERT_EQ(keys[1], 20);
	ASSERT_EQ(keys[2], 30);
	ASSERT_EQ(keys[3], 40);
	ASSERT_EQ(keys[4], 50);
}

// Test 4b: Key-Based Ordering with String Keys
TEST_F(StatisticsTest, TestKeyOrderingStringKeys) {
	// Use string key function
	auto string_key_func = [](const Row &row) {
		return row.As<std::string>(0);
	};

	Statistics<std::function<std::string(const Row&)>> stats(test_file_, string_key_func);
	stats.SetHeader("Key,Value");

	// Add entries in random order
	stats.AddEntry() << "zebra" << "value_z";
	stats.AddEntry() << "apple" << "value_a";
	stats.AddEntry() << "cherry" << "value_c";
	stats.AddEntry() << "banana" << "value_b";

	stats.Write();

	// Verify alphabetical order
	std::string content = ReadFileContent(test_file_);

	size_t pos_apple = content.find("apple,value_a");
	size_t pos_banana = content.find("banana,value_b");
	size_t pos_cherry = content.find("cherry,value_c");
	size_t pos_zebra = content.find("zebra,value_z");

	ASSERT_NE(pos_apple, std::string::npos);
	ASSERT_NE(pos_banana, std::string::npos);
	ASSERT_NE(pos_cherry, std::string::npos);
	ASSERT_NE(pos_zebra, std::string::npos);

	ASSERT_LT(pos_apple, pos_banana);
	ASSERT_LT(pos_banana, pos_cherry);
	ASSERT_LT(pos_cherry, pos_zebra);
}

// Test 4c: Key-Based Ordering with Composite Keys
TEST_F(StatisticsTest, TestKeyOrderingCompositeKeys) {
	// Use composite key: (first_col << 16) | second_col
	auto composite_key_func = [](const Row &row) {
		int first = row.As<int>(0);
		int second = row.As<int>(1);
		return (first << 16) | second;
	};

	Statistics<std::function<int(const Row&)>> stats(test_file_, composite_key_func);
	stats.SetHeader("First,Second,Value");

	// Add entries
	stats.AddEntry() << 2 << 1 << "value_2_1";
	stats.AddEntry() << 1 << 2 << "value_1_2";
	stats.AddEntry() << 1 << 1 << "value_1_1";
	stats.AddEntry() << 2 << 2 << "value_2_2";

	stats.Write();

	// Verify order: (1,1) < (1,2) < (2,1) < (2,2)
	std::string content = ReadFileContent(test_file_);

	size_t pos_1_1 = content.find("1,1,value_1_1");
	size_t pos_1_2 = content.find("1,2,value_1_2");
	size_t pos_2_1 = content.find("2,1,value_2_1");
	size_t pos_2_2 = content.find("2,2,value_2_2");

	ASSERT_NE(pos_1_1, std::string::npos);
	ASSERT_NE(pos_1_2, std::string::npos);
	ASSERT_NE(pos_2_1, std::string::npos);
	ASSERT_NE(pos_2_2, std::string::npos);

	ASSERT_LT(pos_1_1, pos_1_2);
	ASSERT_LT(pos_1_2, pos_2_1);
	ASSERT_LT(pos_2_1, pos_2_2);
}

// Test: Empty file handling
TEST_F(StatisticsTest, TestEmptyFile) {
	// Create file with only header
	std::ofstream out(test_file_);
	out << "Key,Value\n";
	out.close();

	Statistics stats(test_file_, GetKeyFunction());

	// Add entry
	stats.AddEntry() << 1 << "value1";
	stats.Write();

	// Verify
	std::string content = ReadFileContent(test_file_);
	ASSERT_NE(content.find("Key,Value"), std::string::npos);
	ASSERT_NE(content.find("1,value1"), std::string::npos);
	ASSERT_EQ(CountLines(test_file_), 2);
}

// Test: Replace multiple entries
TEST_F(StatisticsTest, TestReplaceMultipleEntries) {
	// Create initial file
	std::ofstream out(test_file_);
	out << "Key,Value\n";
	out << "1,old1\n";
	out << "2,old2\n";
	out << "3,old3\n";
	out.close();

	Statistics stats(test_file_, GetKeyFunction());

	// Replace all entries
	stats.AddEntry() << 1 << "new1";
	stats.AddEntry() << 2 << "new2";
	stats.AddEntry() << 3 << "new3";
	stats.Write();

	// Verify all replaced
	std::string content = ReadFileContent(test_file_);
	ASSERT_NE(content.find("1,new1"), std::string::npos);
	ASSERT_NE(content.find("2,new2"), std::string::npos);
	ASSERT_NE(content.find("3,new3"), std::string::npos);
	ASSERT_EQ(content.find("old1"), std::string::npos);
	ASSERT_EQ(content.find("old2"), std::string::npos);
	ASSERT_EQ(content.find("old3"), std::string::npos);
}

} // namespace atflow

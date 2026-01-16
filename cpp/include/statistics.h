#ifndef __STATISTICS_H__
#define __STATISTICS_H__

#include <algorithm>
#include <filesystem>
#include <iostream>
#include <sstream>
#include <vector>

#include "include/file_lock.h"

namespace atflow {

class Row {
public:
	template<typename T>
	inline Row& operator<<(const T &val) {
		cells_.push_back(std::to_string(val));
		return *this;
	}

	inline Row& operator<<(std::string_view val) {
		cells_.push_back(std::string(val));
		return *this;
	}

	inline Row& operator<<(const std::string &val) {
		cells_.push_back(val);
		return *this;
	}

	inline Row& operator<<(const char *val) {
		cells_.push_back(std::string(val));
		return *this;
	}

	template<typename T>
	inline T As(size_t i) const {
		T result;
		std::stringstream ss(cells_[i]);
		ss >> result;
		return result;
	}

	friend std::ostream& operator<<(std::ostream &os, const Row &row) {
		for (size_t i = 0; i < row.cells_.size(); ++i) {
			os << row.cells_[i];
			if (i < row.cells_.size() - 1) {
				os << ",";
			}
		}
		return os;
	}

private:
	std::vector<std::string> cells_;
};


template<typename Key>
class Statistics {
public:

	Statistics(
		const std::filesystem::path &path,
		const Key &key
	);

	inline void SetHeader(const std::string &header) {
		header_ = header;
	}

	Row& AddEntry();

	void Write();

private:
	// path
	std::filesystem::path path_;
	// key function
	Key key_;
	// header
	std::string header_;
	// rows
	std::vector<Row> rows_;
	// new rows for lazy update
	std::vector<Row> new_rows_;
};


template<typename Key>
Statistics<Key>::Statistics(
	const std::filesystem::path &path,
	const Key &key
) : path_(path), key_(key) {
	// create directory if not exists
	std::filesystem::create_directories(path_.parent_path());
	// read file if exists
	if (std::filesystem::exists(path_)) {
		// create lock file if not exists
		std::filesystem::path lock_path =
			path_.parent_path() / (path_.stem().string() + ".lock");
		// acquire lock
		FileLock lock(lock_path.string().c_str());
		// read file
		std::ifstream fin(path_);
		std::string line;
		// read header
		std::getline(fin, header_);
		// read rows
		while (std::getline(fin, line)) {
			rows_.emplace_back();
			std::size_t pos = 0;
			for (
				size_t found = line.find(",", pos);
				found != std::string::npos;
				pos = found + 1, found = line.find(",", pos)
			) {
				rows_.back() << std::string_view(
					line.data() + pos, found - pos
				);
			}
			if (pos != line.size()) {
				rows_.back() << std::string_view(
					line.data() + pos, line.size() - pos
				);
			}
		}
		fin.close();
	}
}


template<typename Key>
Row& Statistics<Key>::AddEntry() {
	new_rows_.emplace_back();
	return new_rows_.back();
}


template<typename Key>
void Statistics<Key>::Write() {
	// merge new rows
	for (const auto &row : new_rows_) {
		auto key = key_(row);
		auto iter = std::lower_bound(
			rows_.begin(),
			rows_.end(),
			key,
			[&](const Row &a, const decltype(key_(a)) &b) {
				return key_(a) < b;
			}
		);
		if (iter == rows_.end() || key_(*iter) != key) {
			rows_.insert(iter, row);
		} else {
			*iter = row;
		}
	}
	// create lock file if not exists
	std::filesystem::path lock_path =
		path_.parent_path() / (path_.stem().string() + ".lock");
	// acquire lock
	FileLock lock(lock_path.string().c_str());
	// open file
	std::ofstream fout(path_);
	fout << header_ << "\n";
	for (const auto &row : rows_) {
		fout << row << "\n";
	}
	fout.close();
}



}

#endif	// __STATISTICS_H__
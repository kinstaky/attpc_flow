#include "include/merge/graw.h"

namespace atflow {

GrawFrameHeaderReader::GrawFrameHeaderReader(const std::filesystem::path &path) {
	fin_.open(path, std::ios::binary);
}

GrawFrameHeaderReader::~GrawFrameHeaderReader() {
	fin_.close();
}

bool GrawFrameHeaderReader::Read() {
	fin_.read(buffer_, sizeof(buffer_));
	header_ = (GrawFrameHeader*)buffer_;
	fin_.seekg((FrameSize() - 1)*256, std::ios::cur);
	return fin_.good();
}


}
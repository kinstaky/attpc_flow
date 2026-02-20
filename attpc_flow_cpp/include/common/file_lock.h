#ifndef __FILE_LOCK_H__
#define __FILE_LOCK_H__

#include <fcntl.h>
#include <sys/file.h>
#include <unistd.h>

namespace atflow {

class FileLock {
public:

	FileLock(const char* path) {
		fd_ = open(path, O_RDWR | O_CREAT, 0644);
		if (fd_ != -1) flock(fd_, LOCK_EX);
	}

	~FileLock() {
		if (fd_ != -1) {
			flock(fd_, LOCK_UN);
			close(fd_);
		}
	}

private:
	// file descriptor
	int fd_;
};

}

#endif	// __FILE_LOCK_H__

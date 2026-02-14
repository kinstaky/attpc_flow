#ifndef GRAW_H
#define GRAW_H

#include <cstdint>
#include <fstream>
#include <filesystem>

namespace atflow {

struct GrawFrameHeader {
	uint32_t meta_type : 8;
	uint32_t frame_size : 24;
	uint32_t revision : 8;
	uint32_t frame_type: 16;
	uint32_t source: 8;
	uint32_t header_size: 16;
	uint32_t item_size: 16;
	uint32_t n_items;
	uint32_t event_time_high;
	uint32_t event_time_low: 16;
	uint32_t event_id_high: 16;
	uint32_t event_id_low: 16;
	uint32_t cobo_id: 8;
	uint32_t asad_id: 8;
	uint32_t read_offset: 16;
	uint32_t status: 8;
	uint32_t reserve[56];
};


struct GrawData {
	uint32_t aget: 2;
	uint32_t channel: 7;
	uint32_t time_bucket_id: 9;
	uint32_t reserve: 2;
	uint32_t sample: 12;
};


class GrawFrameHeaderReader {
public:
	/// @brief Constructor
	/// @param[in] path Path to the graw file
	GrawFrameHeaderReader(const std::filesystem::path &path);

	/// @brief Destructor
	~GrawFrameHeaderReader();

	/// @brief Read next frame header
	/// @returns True if successful, false otherwise
	bool Read();

	/// @brief Get meta type
	/// @returns Meta type
	inline uint32_t MetaType() const {
		return header_->meta_type;
	}

	/// @brief Get the frame size
	/// @returns Frame size in bytes
	inline uint32_t FrameSize() const {
		return
			(header_->frame_size >> 16)
			| (header_->frame_size & 0xff00)
			| ((header_->frame_size & 0xff) << 16);
	}

	/// @brief Get revision
	/// @returns Revision
	inline uint32_t Revision() const {
		return header_->revision;
	}

	/// @brief Get frame type
	/// @returns Frame type
	inline uint32_t FrameType() const {
		return
			(header_->frame_type >> 8)
			| ((header_->frame_type & 0xff) << 8);
	}

	/// @brief Get source
	/// @returns Source
	inline uint32_t Source() const {
		return header_->source;
	}

	/// @brief Get header size
	/// @returns Header size in 256 bytes
	inline uint32_t HeaderSize() const {
		return
			(header_->header_size >> 8)
			| ((header_->header_size & 0xff) << 8);
	}

	/// @brief Get item size
	/// @returns Item size in bytes
	inline uint32_t ItemSize() const {
		return
			(header_->item_size >> 8)
			| ((header_->item_size & 0xff) << 8);
	}

	/// @brief Get number of items
	/// @returns Number of items
	inline uint32_t NItems() const {
		return
			(header_->n_items >> 24)
			| ((header_->n_items & 0xff0000) >> 8)
			| ((header_->n_items & 0xff00) << 8)
			| ((header_->n_items & 0xff) << 24);
	}

	/// @brief Get event time
	/// @returns Event time in ns
	inline uint64_t EventTime() const {
		return
			(((uint64_t)header_->event_time_high & 0xff000000) >> 8)
			| (((uint64_t)header_->event_time_high & 0xff0000) << 8)
			| (((uint64_t)header_->event_time_high & 0xff00) << 24)
			| (((uint64_t)header_->event_time_high & 0xff) << 40)
			| (((uint64_t)header_->event_time_low & 0xff00) >> 8)
			| (((uint64_t)header_->event_time_low & 0xff) << 8);
	}

	/// @brief Get event ID
	/// @returns Event ID
	inline uint32_t EventId() const {
		return
			((header_->event_id_high & 0xff00) << 8)
			| ((header_->event_id_high & 0xff) << 24)
			| (header_->event_id_low >> 8)
			| ((header_->event_id_low & 0xff) << 8);
	}

	/// @brief Get cobo ID
	/// @returns Cobo ID
	inline uint32_t Cobo() const {
		return header_->cobo_id;
	}

	/// @brief Get ASAD ID
	/// @returns ASAD ID
	inline uint32_t Asad() const {
		return header_->asad_id;
	}

	/// @brief Get read offset
	/// @returns Read offset in bytes
	inline uint32_t ReadOffset() const {
		return
			(header_->read_offset >> 8)
			| ((header_->read_offset & 0xff) << 8);
	}

	/// @brief Get status
	/// @returns Status
	inline uint32_t Status() const {
		return header_->status;
	}

private:
	std::ifstream fin_;
	char buffer_[256];
	GrawFrameHeader* header_;
};


}
#endif
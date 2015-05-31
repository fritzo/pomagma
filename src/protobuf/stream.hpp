// Copyright (c) 2014, Salesforce.com, Inc.  All rights reserved.
//
// Redistribution and use in source and binary forms, with or without
// modification, are permitted provided that the following conditions
// are met:
//
// - Redistributions of source code must retain the above copyright
//   notice, this list of conditions and the following disclaimer.
// - Redistributions in binary form must reproduce the above copyright
//   notice, this list of conditions and the following disclaimer in the
//   documentation and/or other materials provided with the distribution.
// - Neither the name of Salesforce.com nor the names of its contributors
//   may be used to endorse or promote products derived from this
//   software without specific prior written permission.
//
// THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
// "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
// LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
// FOR A PARTICULAR PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL THE
// COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
// INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
// BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS
// OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
// ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR
// TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE
// USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

#pragma once

#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <vector>
#include <google/protobuf/io/coded_stream.h>
#include <google/protobuf/io/zero_copy_stream_impl.h>
#include <google/protobuf/io/gzip_stream.h>
#include <pomagma/platform/util.hpp>

namespace pomagma
{
namespace protobuf
{

class InFile : noncopyable
{
public:

    InFile (int fid) : fid_(fid)
    {
        _open();
    }

    InFile (const std::string & filename) : filename_(filename)
    {
        POMAGMA_ASSERT(not filename_.empty(),
            "empty filename is not supported");
        _open();
    }

    ~InFile ()
    {
        _close();
    }

    const std::string & filename () const { return filename_; }
    bool is_file () const { return is_file_; }

    uint64_t position () const { return position_; }

    void set_position (uint64_t target)
    {
        if (target < position_) {
            _close();
            _open();
        }

        while (position_ < target) {
            google::protobuf::io::CodedInputStream coded(stream_);
            uint32_t message_size = 0;
            bool success = coded.ReadLittleEndian32(& message_size);
            POMAGMA_ASSERT(success, "failed to set position of " << filename_);
            success = coded.Skip(message_size);
            POMAGMA_ASSERT(success, "failed to set position of " << filename_);
            ++position_;
        }
    }

    template<class Message>
    void read (Message & message)
    {
        bool success = message.ParseFromZeroCopyStream(stream_);
        POMAGMA_ASSERT(success, "failed to parse message from " << filename_);
    }

    template<class Message>
    bool try_read_stream (Message & message)
    {
        google::protobuf::io::CodedInputStream coded(stream_);
        uint32_t message_size = 0;
        if (likely(coded.ReadLittleEndian32(& message_size))) {
            auto old_limit = coded.PushLimit(message_size);
            bool success = message.ParseFromCodedStream(& coded);
            POMAGMA_ASSERT(success,
                "failed to parse message from " << filename_);
            coded.PopLimit(old_limit);
            ++position_;
            return true;
        }
        return false;
    }

    bool try_read_stream (std::vector<char> & raw)
    {
        google::protobuf::io::CodedInputStream coded(stream_);
        uint32_t message_size = 0;
        if (likely(coded.ReadLittleEndian32(& message_size))) {
            auto old_limit = coded.PushLimit(message_size);
            raw.resize(message_size);
            bool success = coded.ReadRaw(raw.data(), message_size);
            POMAGMA_ASSERT(success,
                "failed to parse message from " << filename_);
            coded.PopLimit(old_limit);
            ++position_;
            return true;
        }
        return false;
    }

    template<class Message>
    void cyclic_read_stream (Message & message)
    {
        POMAGMA_ASSERT2(is_file(), "only files support cyclic_read_stream");
        if (unlikely(not try_read_stream(message))) {
            _close();
            _open();
            bool success = try_read_stream(message);
            POMAGMA_ASSERT(success, "stream is empty");
        }
    }

    struct StreamStats
    {
        bool is_file;
        uint64_t message_count;
        uint32_t max_message_size;
    };

    static StreamStats stream_stats (const std::string & filename)
    {
        InFile file(filename);

        StreamStats stats;
        stats.is_file = file.is_file();
        stats.message_count = 0;
        stats.max_message_size = 0;

        while (true) {
            google::protobuf::io::CodedInputStream coded(file.stream_);
            uint32_t message_size = 0;
            if (likely(coded.ReadLittleEndian32(& message_size))) {
                bool success = coded.Skip(message_size);
                POMAGMA_ASSERT(success, "failed to count " << filename);
                ++stats.message_count;
                stats.max_message_size =
                    std::max(stats.max_message_size, message_size);
            } else {
                break;
            }
        }
        return stats;
    }

private:

    void _open ()
    {
        if (filename_.empty()) {
            is_file_ = false;
        } else if (filename_ == "-" or filename_ == "-.gz") {
            is_file_ = false;
            fid_ = STDIN_FILENO;
        } else {
            is_file_ = true;
            fid_ = open(filename_.c_str(), O_RDONLY | O_NOATIME);
            POMAGMA_ASSERT(fid_ != -1,
                "failed to open input file " << filename_);
        }

        file_ = new google::protobuf::io::FileInputStream(fid_);

        if (endswith(filename_, ".gz")) {
            gzip_ = new google::protobuf::io::GzipInputStream(file_);
            stream_ = gzip_;
        } else {
            gzip_ = nullptr;
            stream_ = file_;
        }

        position_ = 0;
    }

    void _close ()
    {
        delete gzip_;
        delete file_;
        if (is_file()) {
            close(fid_);
        }
    }

    const std::string filename_;
    int fid_;
    bool is_file_;
    google::protobuf::io::FileInputStream * file_;
    google::protobuf::io::GzipInputStream * gzip_;
    google::protobuf::io::ZeroCopyInputStream * stream_;
    uint64_t position_;
};


class OutFile : noncopyable
{
public:

    enum { APPEND = O_APPEND };

    OutFile (int fid) : fid_(fid)
    {
        _open();
    }

    OutFile (const std::string & filename, int flags = 0) : filename_(filename)
    {
        POMAGMA_ASSERT(not filename_.empty(),
            "empty filename is not supported");
        _open(flags);
    }

    ~OutFile ()
    {
        delete gzip_;
        delete file_;
        if (is_file()) {
            close(fid_);
        }
    }

    const std::string & filename () const { return filename_; }
    bool is_file () const { return is_file_; }

    template<class Message>
    void write (Message & message)
    {
        POMAGMA_ASSERT1(message.IsInitialized(), "message not initialized");
        bool success = message.SerializeToZeroCopyStream(stream_);
        POMAGMA_ASSERT(success,
            "failed to serialize message to " << filename_);
    }

    template<class Message>
    void write_stream (Message & message)
    {
        google::protobuf::io::CodedOutputStream coded(stream_);
        POMAGMA_ASSERT1(message.IsInitialized(), "message not initialized");
        uint32_t message_size = message.ByteSize();
        coded.WriteLittleEndian32(message_size);
        message.SerializeWithCachedSizes(& coded);
    }

    void write_stream (const std::vector<char> & raw)
    {
        google::protobuf::io::CodedOutputStream coded(stream_);
        coded.WriteLittleEndian32(raw.size());
        coded.WriteRaw(raw.data(), raw.size());
    }

    void flush ()
    {
        if (gzip_) {
            gzip_->Flush();
        }
        file_->Flush();
    }

private:

    void _open (int flags = 0)
    {
        if (filename_.empty()) {
            is_file_ = false;
        } else if (filename_ == "-" or filename_ == "-.gz") {
            is_file_ = false;
            fid_ = STDOUT_FILENO;
        } else {
            is_file_ = true;
            fid_ = open(
                filename_.c_str(),
                O_WRONLY | O_CREAT | O_TRUNC | flags, 0664);
            POMAGMA_ASSERT(fid_ != -1,
                "failed to open output file " << filename_);
        }

        file_ = new google::protobuf::io::FileOutputStream(fid_);

        if (endswith(filename_, ".gz")) {
            gzip_ = new google::protobuf::io::GzipOutputStream(file_);
            stream_ = gzip_;
        } else {
            gzip_ = nullptr;
            stream_ = file_;
        }
    }

    const std::string filename_;
    int fid_;
    bool is_file_;
    google::protobuf::io::FileOutputStream * file_;
    google::protobuf::io::GzipOutputStream * gzip_;
    google::protobuf::io::ZeroCopyOutputStream * stream_;
};

} // namespace protobuf

template<class Message>
Message protobuf_load (const std::string & filename)
{
    Message message;
    protobuf::InFile file(filename);
    file.read(message);
    return message;
}

template<class Message>
void protobuf_dump (
        const Message & message,
        const std::string & filename)
{
    protobuf::OutFile file(filename);
    file.write(message);
}

template<class Message>
std::vector<Message> protobuf_stream_load (const std::string & filename)
{
    std::vector<Message> messages(1);
    protobuf::InFile stream(filename);
    while (stream.try_read_stream(messages.back())) {
        messages.resize(messages.size() + 1);
    }
    messages.pop_back();
    return messages;
}

template<class Message>
void protobuf_stream_dump (
        const std::vector<Message> & messages,
        const std::string & filename)
{
    protobuf::OutFile stream(filename);
    for (const auto & message : messages) {
        stream.write_stream(message);
    }
}

} // namespace pomagma

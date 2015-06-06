#pragma once

#include <fcntl.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <google/protobuf/io/coded_stream.h>
#include <google/protobuf/io/gzip_stream.h>
#include <google/protobuf/io/zero_copy_stream_impl.h>
#include <google/protobuf/wire_format.h>
#include <google/protobuf/wire_format_lite.h>
#include <pomagma/util/util.hpp>

namespace pomagma
{
namespace protobuf
{

class InFile : noncopyable
{
    const std::string m_filename;
    const int m_fid;
    google::protobuf::io::FileInputStream * m_file;
    google::protobuf::io::GzipInputStream * m_gzip;

public:

    explicit InFile (const std::string & filename)
        : m_filename(filename),
          m_fid(open(filename.c_str(), O_RDONLY | O_NOATIME))
    {
        POMAGMA_ASSERT(m_fid != -1, "failed to open file " << filename);
        m_file = new google::protobuf::io::FileInputStream(m_fid);
        m_gzip = new google::protobuf::io::GzipInputStream(m_file);
    }

    ~InFile ()
    {
        delete m_gzip;
        delete m_file;
        close(m_fid);
    }

    const std::string & filename () const { return m_filename; }

    template<class Message>
    void read (Message & message)
    {
        bool info = message.ParseFromZeroCopyStream(m_gzip);
        POMAGMA_ASSERT(info, "file ended early: " << m_filename);
    }

    // This tries to parse a single piece of a message. Does not clear message.
    template<class Message>
    bool try_read_chunk (Message & message)
    {
        using google::protobuf::internal::WireFormat;
        using google::protobuf::internal::WireFormatLite;

        google::protobuf::io::CodedInputStream stream(m_gzip);
        const uint32_t tag = stream.ReadTag();
        if (unlikely(not tag)) return false; // EOF
        const int field_number = WireFormatLite::GetTagFieldNumber(tag);

        const auto* field =
            message.GetDescriptor()->FindFieldByNumber(field_number);
        POMAGMA_ASSERT(field, "unknown field " << field_number);

        bool info =
            WireFormat::ParseAndMergeField(tag, field, & message, & stream);
        POMAGMA_ASSERT(info, "failed to parse field " << field_number);
        return true;
    }
};

class OutFile : noncopyable
{
    const std::string m_filename;
    const int m_fid;
    google::protobuf::io::FileOutputStream * m_file;
    google::protobuf::io::GzipOutputStream * m_gzip;

public:

    explicit OutFile (const std::string & filename)
        : m_filename(filename),
          m_fid(open(filename.c_str(), O_WRONLY | O_CREAT | O_TRUNC, 0664))
    {
        POMAGMA_ASSERT(m_fid != -1, "failed to open file " << filename);
        m_file = new google::protobuf::io::FileOutputStream(m_fid);
        m_gzip = new google::protobuf::io::GzipOutputStream(m_file);
    }

    ~OutFile ()
    {
        delete m_gzip;
        delete m_file;
        close(m_fid);
    }

    const std::string & filename () const { return m_filename; }

    template<class Message>
    void write (Message & message)
    {
        POMAGMA_ASSERT1(message.IsInitialized(), "message not initialized");
        bool info = message.SerializeToZeroCopyStream(m_gzip);
        POMAGMA_ASSERT(info, "failed to write to " << m_filename);
    }
};

} // namespace protobuf
} // namespace pomagma

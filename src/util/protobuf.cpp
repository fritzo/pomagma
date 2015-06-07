#include <pomagma/util/protobuf.hpp>

#include <fcntl.h>
#include <google/protobuf/io/coded_stream.h>
#include <google/protobuf/io/gzip_stream.h>
#include <google/protobuf/io/zero_copy_stream_impl.h>
#include <google/protobuf/wire_format.h>
#include <google/protobuf/wire_format_lite.h>
#include <sys/stat.h>
#include <sys/types.h>

namespace pomagma {
namespace protobuf {

InFile::InFile (const std::string & filename)
    : m_filename(filename),
      m_fid(open(filename.c_str(), O_RDONLY | O_NOATIME))
{
    POMAGMA_ASSERT(m_fid != -1, "failed to open file " << filename);
    m_file = new google::protobuf::io::FileInputStream(m_fid);
    m_gzip = new google::protobuf::io::GzipInputStream(m_file);
}

InFile::~InFile ()
{
    delete m_gzip;
    delete m_file;
    close(m_fid);
}

void InFile::read (google::protobuf::Message & message)
{
    bool info = message.ParseFromZeroCopyStream(m_gzip);
    POMAGMA_ASSERT(info, "file ended early: " << m_filename);
}

// This tries to parse a single piece of a message. Does not clear message.
// Replicates a single pass through loop in WireFormat::ParseAndMergePartial.
// see https://github.com/google/protobuf/blob/master/src/google/protobuf/wire_format.cc#L389
bool InFile::try_read_chunk (google::protobuf::Message & message)
{
    using google::protobuf::internal::WireFormat;
    using google::protobuf::internal::WireFormatLite;
    google::protobuf::io::CodedInputStream stream(m_gzip);
    const uint32_t tag = stream.ReadTag();
    if (unlikely(not tag)) return false; // EOF
    const int field_number = WireFormatLite::GetTagFieldNumber(tag);
    POMAGMA_DEBUG("parsing field " << field_number << " of type " << (tag & 7));
    const auto* descriptor = message.GetDescriptor();
    POMAGMA_ASSERT1(descriptor, "failed to get descriptor");  // FIXME fails
    const auto* field = descriptor->FindFieldByNumber(field_number);
    POMAGMA_ASSERT(field, "unknown field " << field_number);
    bool info = WireFormat::ParseAndMergeField(tag, field, & message, & stream);
    POMAGMA_ASSERT(info, "failed to parse field " << field_number);
    return true;
}

OutFile::OutFile (const std::string & filename)
    : m_filename(filename),
      m_fid(open(filename.c_str(), O_WRONLY | O_CREAT | O_TRUNC, 0444))
{
    POMAGMA_ASSERT(m_fid != -1, "failed to open file " << filename);
    m_file = new google::protobuf::io::FileOutputStream(m_fid);
    m_gzip = new google::protobuf::io::GzipOutputStream(m_file);
}

OutFile::~OutFile ()
{
    delete m_gzip;
    delete m_file;
    close(m_fid);
}

void OutFile::write (const google::protobuf::Message & message)
{
    POMAGMA_ASSERT1(message.IsInitialized(), "message not initialized");
    bool info = message.SerializeToZeroCopyStream(m_gzip);
    POMAGMA_ASSERT(info, "failed to write to " << m_filename);
}

} // namespace protobuf
} // namespace pomagma

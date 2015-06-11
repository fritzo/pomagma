#include <pomagma/util/protobuf.hpp>

#include <fcntl.h>
#include <google/protobuf/io/coded_stream.h>
#include <google/protobuf/io/gzip_stream.h>
#include <google/protobuf/io/zero_copy_stream.h>
#include <google/protobuf/io/zero_copy_stream_impl.h>
#include <google/protobuf/wire_format.h>
#include <google/protobuf/wire_format_lite.h>
#include <pomagma/util/hasher.hpp>
#include <sys/stat.h>
#include <sys/types.h>

#define POMAGMA_DEBUG1(message)
//#define POMAGMA_DEBUG1(message) POMAGMA_DEBUG(message)

namespace pomagma {
namespace protobuf {

class Sha1OutputStream : public google::protobuf::io::ZeroCopyOutputStream
{
public:

    explicit Sha1OutputStream (int fid)
        : m_file(fid),
          m_buffer_data(nullptr),
          m_buffer_size(0),
          m_hasher()
    {
    }
    virtual ~Sha1OutputStream () = default;

    virtual bool Next (void ** data, int * size)
    {
        Flush();
        POMAGMA_ASSERT(m_file.Next(data, size), strerror(m_file.GetErrno()));
        m_buffer_data = * data;
        m_buffer_size = * size;
        return true;
    }
    virtual void BackUp (int count)
    {
        POMAGMA_ASSERT_LE(count, m_buffer_size);
        m_buffer_size -= count;
        m_file.BackUp(count);
    }
    virtual int64_t ByteCount () const { return m_file.ByteCount(); }

    Hasher::Digest Digest ()
    {
        Flush();
        POMAGMA_ASSERT(m_file.Close(), strerror(m_file.GetErrno()));
        return m_hasher.finish();
    }

private:

    void Flush ()
    {
        if (likely(m_buffer_size)) {
            m_hasher.add_raw(m_buffer_data, m_buffer_size);
            m_buffer_size = 0;
        }
    }

    google::protobuf::io::FileOutputStream m_file;
    void * m_buffer_data;
    int m_buffer_size;
    Hasher m_hasher;
};

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
    POMAGMA_DEBUG1("parsing field " << field_number << ", type " << (tag & 7));
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

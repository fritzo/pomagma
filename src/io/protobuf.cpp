#include <pomagma/io/protobuf.hpp>

#include <fcntl.h>
#include <google/protobuf/io/coded_stream.h>
#include <google/protobuf/io/gzip_stream.h>
#include <google/protobuf/io/zero_copy_stream.h>
#include <google/protobuf/io/zero_copy_stream_impl.h>
#include <google/protobuf/wire_format.h>
#include <google/protobuf/wire_format_lite.h>
#include <sys/stat.h>
#include <sys/types.h>

#define POMAGMA_DEBUG1(message)
//#define POMAGMA_DEBUG1(message) POMAGMA_DEBUG(message)

namespace pomagma {
namespace protobuf {

static google::protobuf::io::GzipOutputStream::Options default_gzip_options() {
    google::protobuf::io::GzipOutputStream::Options options;
    options.compression_level = Z_BEST_COMPRESSION;
    return options;
}

static const auto g_gzip_options = default_gzip_options();

class Sha1OutputStream : public google::protobuf::io::ZeroCopyOutputStream {
   public:
    explicit Sha1OutputStream(int fid)
        : m_file(fid), m_buffer_data(nullptr), m_buffer_size(0), m_hasher() {}
    virtual ~Sha1OutputStream() {}

    // implements ZeroCopyOutputStream
    virtual bool Next(void** data, int* size) {
        flush_hasher();
        POMAGMA_ASSERT(m_file.Next(data, size), strerror(m_file.GetErrno()));
        m_buffer_data = *data;
        m_buffer_size = *size;
        return true;
    }
    virtual void BackUp(int count) {
        POMAGMA_ASSERT_LE(count, m_buffer_size);
        m_buffer_size -= count;
        m_file.BackUp(count);
    }
    virtual int64_t ByteCount() const { return m_file.ByteCount(); }

    // this must be called exactly once, just before destruction
    const Hasher::Digest& Digest() __attribute__((warn_unused_result)) {
        flush_hasher();
        return m_hasher.finish();
    }

   private:
    void flush_hasher() {
        if (likely(m_buffer_size)) {
            m_hasher.add_raw(m_buffer_data, m_buffer_size);
            m_buffer_size = 0;
        }
    }

    google::protobuf::io::FileOutputStream m_file;
    void* m_buffer_data;
    int m_buffer_size;
    Hasher m_hasher;
};

namespace detail {

struct MagicNumber {
    uint8_t bytes[4];
    uint32_t size;

    bool matches(const MagicNumber& other) const {
        return memcmp(bytes, other.bytes, other.size) == 0;
    }
};

inline MagicNumber read_magic_number(const int fid) {
    MagicNumber magic_number = {{0, 0, 0, 0}, 4};
    size_t read_count = pread(fid, &magic_number.bytes, magic_number.size, 0);
    POMAGMA_ASSERT(read_count == magic_number.size,
                   "failed to read magic number");
    return magic_number;
}

static const MagicNumber g_gzip_magic_number = {{0x1f, 0x8b, 0, 0}, 2};
static const MagicNumber g_lz4_magic_number = {{0x18, 0x4D, 0x22, 0x04}, 4};

}  // namespace detail

// O_NOATIME is defined on linux but not OS X
#ifndef O_NOATIME
#define O_NOATIME 0
#endif  // O_NOATIME

InFile::InFile(const std::string& filename)
    : m_filename(filename),
      m_fid(open(filename.c_str(), O_RDONLY | O_NOATIME)) {
    POMAGMA_ASSERT(m_fid != -1, "opening " << filename << ": "
                                           << strerror(errno));
    m_file = new google::protobuf::io::FileInputStream(m_fid);
    const auto magic_number = detail::read_magic_number(m_fid);
    if (magic_number.matches(detail::g_gzip_magic_number)) {
        m_gzip = new google::protobuf::io::GzipInputStream(m_file);
    } else if (magic_number.matches(detail::g_lz4_magic_number)) {
        TODO("implement LZ4 compression");
    } else {
        POMAGMA_ERROR("Unknown magic number: " << std::hex
                                               << magic_number.bytes);
    }
}

InFile::~InFile() {
    delete m_gzip;
    delete m_file;
    close(m_fid);
}

void InFile::read(google::protobuf::Message& message) {
    bool info = message.ParseFromZeroCopyStream(m_gzip);
    POMAGMA_ASSERT(info, "file ended early: " << m_filename);
}

// This tries to parse a single piece of a message. Does not clear message.
// Replicates a single pass through loop in WireFormat::ParseAndMergePartial.
// see
// https://github.com/google/protobuf/blob/master/src/google/protobuf/wire_format.cc#L389
bool InFile::try_read_chunk(google::protobuf::Message& message) {
    using google::protobuf::internal::WireFormat;
    using google::protobuf::internal::WireFormatLite;
    google::protobuf::io::CodedInputStream stream(m_gzip);
    const uint32_t tag = stream.ReadTag();
    if (unlikely(not tag)) return false;  // EOF
    const int field_number = WireFormatLite::GetTagFieldNumber(tag);
    POMAGMA_DEBUG1("parsing field " << field_number << ", type " << (tag & 7));
    const auto* descriptor = message.GetDescriptor();
    POMAGMA_ASSERT1(descriptor, "failed to get descriptor");  // FIXME fails
    const auto* field = descriptor->FindFieldByNumber(field_number);
    POMAGMA_ASSERT(field, "unknown field " << field_number);
    bool info = WireFormat::ParseAndMergeField(tag, field, &message, &stream);
    POMAGMA_ASSERT(info, "failed to parse field " << field_number);
    return true;
}

OutFile::OutFile(const std::string& filename)
    : m_filename(filename), m_fid(creat(filename.c_str(), 0444)) {
    POMAGMA_ASSERT(m_fid != -1, "opening " << filename << ": "
                                           << strerror(errno));
    m_file = new google::protobuf::io::FileOutputStream(m_fid);
    m_gzip = new google::protobuf::io::GzipOutputStream(m_file, g_gzip_options);
}

OutFile::~OutFile() {
    delete m_gzip;
    delete m_file;
    POMAGMA_ASSERT(close(m_fid) != -1, "closing " << m_filename << ": "
                                                  << strerror(errno));
}

void OutFile::write(const google::protobuf::Message& message) {
    POMAGMA_ASSERT1(message.IsInitialized(), "message not initialized");
    bool info = message.SerializeToZeroCopyStream(m_gzip);
    POMAGMA_ASSERT(info, "failed to write to " << m_filename);
}

size_t OutFile::approx_bytes_written() { return m_file->ByteCount(); }

Sha1OutFile::Sha1OutFile(const std::string& filename)
    : m_filename(filename), m_fid(creat(filename.c_str(), 0444)) {
    POMAGMA_ASSERT(m_fid != -1, "opening " << filename << ": "
                                           << strerror(errno));
    m_file = new Sha1OutputStream(m_fid);
    m_gzip = new google::protobuf::io::GzipOutputStream(m_file, g_gzip_options);
}

Sha1OutFile::~Sha1OutFile() {
    POMAGMA_ASSERT(m_gzip == nullptr, "digest() has not been called");
    delete m_file;
    POMAGMA_ASSERT(close(m_fid) != -1, "closing " << m_filename << ": "
                                                  << strerror(errno));
}

void Sha1OutFile::write(const google::protobuf::Message& message) {
    POMAGMA_ASSERT1(message.IsInitialized(), "message not initialized");
    bool info = message.SerializeToZeroCopyStream(m_gzip);
    POMAGMA_ASSERT(info, "failed to write to " << m_filename);
}

size_t Sha1OutFile::approx_bytes_written() { return m_file->ByteCount(); }

const Hasher::Digest& Sha1OutFile::digest() {
    delete m_gzip;
    m_gzip = nullptr;
    return m_file->Digest();
}

std::string Sha1OutFile::hexdigest() {
    delete m_gzip;
    m_gzip = nullptr;
    return Hasher::str(m_file->Digest());
}

}  // namespace protobuf
}  // namespace pomagma

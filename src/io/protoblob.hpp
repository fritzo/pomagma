#pragma once

#include <pomagma/io/protobuf.hpp>
#include <pomagma/io/blobstore.hpp>
#include <functional>

namespace pomagma {
namespace protobuf {

class BlobWriter : noncopyable
{
    protobuf::Sha1OutFile * m_file;
    std::function<void(const std::string&)> m_add_blob;

    void open ()
    {
        POMAGMA_ASSERT1(m_file == nullptr, "open() called twice");
        m_file = new protobuf::Sha1OutFile(create_blob());
    }

    void close ()
    {
        POMAGMA_ASSERT1(m_file, "close() called twice");
        const std::string temp_path = m_file->filename();
        const std::string hexdigest = m_file->hexdigest();
        delete m_file;
        m_file = nullptr;
        store_blob(temp_path, hexdigest);
        m_add_blob(hexdigest);
    }

public:

    explicit BlobWriter (std::function<void(const std::string)> add_blob)
        : m_file(nullptr),
          m_add_blob(add_blob)
    {
        open();
    }

    void write (const google::protobuf::Message & message)
    {
        m_file->write(message);
    }

    bool try_split ()
    {
        if (m_file->approx_bytes_written() >= GOOD_BLOB_SIZE_BYTES) {
            close();
            open();
            return true;
        } else {
            return false;
        }
    }

    ~BlobWriter ()
    {
        close();
    }
};

class BlobReader : noncopyable
{
    protobuf::InFile m_file;

public:

    explicit BlobReader (const std::string & hexdigest)
        : m_file(find_blob(hexdigest))
    {
    }

    void read (google::protobuf::Message & message)
    {
        m_file.read(message);
    }

    bool try_read_chunk (google::protobuf::Message & message)
    {
        return m_file.try_read_chunk(message);
    }
};

} // namespace protobuf
} // namespace pomagma

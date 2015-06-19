#pragma once

#include <pomagma/io/protobuf.hpp>
#include <pomagma/io/blobstore.hpp>

namespace pomagma {
namespace protobuf {

class BlobWriter : noncopyable
{
    protobuf::Sha1OutFile * m_file;
    std::string * m_destin;

    void open (std::string * destin)
    {
        POMAGMA_ASSERT1(m_file == nullptr, "open() called twice");
        POMAGMA_ASSERT1(m_destin == nullptr, "open() called twice");
        m_file = new protobuf::Sha1OutFile(create_blob());
        m_destin = destin;
        m_destin->clear();
    }

    void close ()
    {
        POMAGMA_ASSERT1(m_file, "close() called twice");
        POMAGMA_ASSERT1(m_destin and m_destin->empty(), "close() called twice");
        const std::string temp_path = m_file->filename();
        * m_destin = m_file->hexdigest();
        delete m_file;
        store_blob(temp_path, * m_destin);
        m_file = nullptr;
        m_destin = nullptr;
    }

public:

    explicit BlobWriter (std::string * destin)
        : m_file(nullptr),
          m_destin(nullptr)
    {
        open(destin);
    }

    void write (const google::protobuf::Message & message)
    {
        m_file->write(message);
    }

    bool try_split (google::protobuf::RepeatedPtrField<std::string> * blobs)
    {
        if (m_file->approx_bytes_written() >= GOOD_BLOB_SIZE_BYTES) {
            close();
            open(blobs->Add());
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

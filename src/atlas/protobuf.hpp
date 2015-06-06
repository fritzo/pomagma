#pragma once

#include <pomagma/atlas/messages.pb.h>
#include <pomagma/util/blobstore.hpp>
#include <pomagma/util/protobuf.hpp>
#include <pomagma/util/util.hpp>

namespace pomagma
{
namespace protobuf
{

inline void delta_compress (SparseMap & chunk)
{
    POMAGMA_ASSERT_EQ(chunk.key_size(), chunk.val_size());
    int prev_key = 0;
    int prev_val = 0;
    for (size_t i = 0, count = chunk.key_size(); i < count; ++i) {
        int key = chunk.key(i);
        int val = chunk.val(i);
        POMAGMA_ASSERT1(key > prev_key, "keys are not increasing")
        chunk.add_key_diff_minus_one(key - prev_key - 1);
        chunk.add_val_diff(val - prev_val);
        prev_key = key;
        prev_val = val;
    }
    chunk.clear_key();
    chunk.clear_val();
}

inline void delta_decompress (SparseMap & chunk)
{
    POMAGMA_ASSERT_EQ(chunk.key_diff_minus_one_size(), chunk.val_diff_size());
    int key = 0;
    int val = 0;
    for (size_t i = 0, count = chunk.val_diff_size(); i < count; ++i) {
        chunk.add_key(key += chunk.key_diff_minus_one(i) + 1);
        chunk.add_val(val += chunk.val_diff(i));
    }
    chunk.clear_key_diff_minus_one();
    chunk.clear_val_diff();
}

class BlobWriter : noncopyable
{
    protobuf::OutFile & m_file;
    std::string & m_destin;

public:

    explicit BlobWriter (std::string * destin)
        : m_file(* new protobuf::OutFile(create_blob())),
          m_destin(* destin)
    {
    }

    ~BlobWriter ()
    {
        const std::string temp_path = m_file.filename();
        delete & m_file;
        m_destin = store_blob(temp_path);
    }

    template<class Message>
    void write (const Message & message)
    {
        m_file.write(message);
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

    template<class Message>
    void read (Message & message)
    {
        m_file.read(message);
    }

    template<class Message>
    bool try_read_chunk (Message & message)
    {
        return m_file.try_read_chunk(message);
    }
};

} // namespace protobuf
} // namespace pomagma

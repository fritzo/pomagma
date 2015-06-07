#pragma once

#include <pomagma/atlas/messages.pb.h>
#include <pomagma/util/blobstore.hpp>
#include <pomagma/util/protobuf.hpp>
#include <pomagma/util/util.hpp>

namespace pomagma
{
namespace protobuf
{

inline void delta_compress (SparseMap & map)
{
    POMAGMA_ASSERT_EQ(map.key_size(), map.val_size());
    POMAGMA_ASSERT_EQ(0, map.key_diff_minus_one_size());
    POMAGMA_ASSERT_EQ(0, map.val_diff_size());
    int prev_key = 0;
    int prev_val = 0;
    for (size_t i = 0, count = map.key_size(); i < count; ++i) {
        int key = map.key(i);
        int val = map.val(i);
        POMAGMA_ASSERT1(key > prev_key, "keys are not increasing")
        map.add_key_diff_minus_one(key - prev_key - 1);
        map.add_val_diff(val - prev_val);
        prev_key = key;
        prev_val = val;
    }
    map.clear_key();
    map.clear_val();
}

// this leaves uncompressed data uncompressed
inline void delta_decompress (SparseMap & map)
{
    POMAGMA_ASSERT_EQ(map.key_diff_minus_one_size(), map.val_diff_size());
    POMAGMA_ASSERT_EQ(map.key_size(), map.val_size());
    int key = 0;
    int val = 0;
    for (size_t i = 0, count = map.val_diff_size(); i < count; ++i) {
        map.add_key(key += map.key_diff_minus_one(i) + 1);
        map.add_val(val += map.val_diff(i));
    }
    map.clear_key_diff_minus_one();
    map.clear_val_diff();
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

    void write (const google::protobuf::Message & message)
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

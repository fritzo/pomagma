#pragma once

#include <pomagma/util/util.hpp>
#include <google/protobuf/io/coded_stream.h>

namespace pomagma {
namespace io {

class Int32Writer
{
    std::string & m_message;

    uint8_t * begin () const
    {
        return reinterpret_cast<uint8_t *>(& m_message.front());
    }

public:

    Int32Writer (std::string & message) : m_message(message)
    {
        m_message.clear();
    }
    Int32Writer (std::string & message, size_t int_count) : m_message(message)
    {
        m_message.clear();
        m_message.reserve(int_count * 4);
    }
    void write (uint32_t value)
    {
        m_message.resize(m_message.size() + 4);
        memcpy(& m_message.back() - 3, & value, 4);
    }
};

class Int32Reader
{
    const uint8_t * m_pos;

public:

    Int32Reader (const std::string & message)
        : m_pos(reinterpret_cast<const uint8_t *>(message.data())) {}

    uint32_t read ()
    {
        uint32_t result;
        memcpy(& result, m_pos, 4);
        m_pos += 4;
        return result;
    }
};

// Adapted from the public-domain snippet at:
// http://techoverflow.net/blog/2013/01/25/efficiently-encoding-variable-length-integers-in-cc
template<typename int_t>
uint8_t * dump_varint (int_t value, uint8_t * buffer) {
    *buffer = value & 127;
    while ((value >>= 7)) {
        *buffer++ |= 128;
        *buffer = value & 127;
    }
    return buffer + 1;
}

template<typename int_t>
const uint8_t * load_varint (int_t & value, const uint8_t * buffer) {
    value = *buffer & 127;
    for (size_t shift = 7; *buffer++ & 128; shift += 7) {
        value |= static_cast<int_t>(*buffer & 127) << shift;
    }
    return buffer;
}

class Varint32Writer
{
    std::string & m_message;

    uint8_t * begin () const
    {
        return reinterpret_cast<uint8_t *>(& m_message.front());
    }

public:

    Varint32Writer (std::string & message) : m_message(message)
    {
        m_message.clear();
    }
    Varint32Writer (std::string & message, size_t int_count)
        : m_message(message)
    {
        m_message.clear();
        m_message.reserve(int_count * 5);
    }
    void write (uint32_t value)
    {
        size_t offset = m_message.size();
        m_message.resize(offset + 5);
        uint8_t * end = dump_varint<uint32_t>(value, begin() + offset);
        m_message.resize(end - begin());
    }
};

class Varint32Reader
{
    const uint8_t * m_pos;

public:

    Varint32Reader (const std::string & message)
        : m_pos(reinterpret_cast<const uint8_t *>(message.data())) {}

    uint32_t read ()
    {
        uint32_t result;
        m_pos = load_varint<uint32_t>(result, m_pos);
        return result;
    }
};

class ProtobufVarint32Writer
{
    std::string & m_message;
    uint8_t * m_pos;
#if POMAGMA_DEBUG_LEVEL
    int64_t m_count;
#endif // POMAGMA_DEBUG_LEVEL

    typedef google::protobuf::io::CodedOutputStream Stream;

    uint8_t * begin () const
    {
        return reinterpret_cast<uint8_t *>(& m_message.front());
    }

public:

    ProtobufVarint32Writer (std::string & message, size_t int_count)
        : m_message(message)
    {
#if POMAGMA_DEBUG_LEVEL
        m_count = int_count;
#endif // POMAGMA_DEBUG_LEVEL
        m_message.resize(int_count * 5);
        m_pos = begin();
    }
    void write (uint32_t value)
    {
#if POMAGMA_DEBUG_LEVEL
        --m_count;
#endif // POMAGMA_DEBUG_LEVEL
        m_pos = Stream::WriteVarint32ToArray(value, m_pos);
    }
    ~ProtobufVarint32Writer ()
    {
        size_t size = m_pos - begin();
#if POMAGMA_DEBUG_LEVEL
        POMAGMA_ASSERT_EQ(m_count, 0);
        POMAGMA_ASSERT_LE(size, m_message.size());
#endif // POMAGMA_DEBUG_LEVEL
        m_message.resize(size);
    }
};

class ProtobufVarint32Reader
{
    google::protobuf::io::CodedInputStream m_stream;

public:

    ProtobufVarint32Reader (const std::string & message)
        : m_stream(
            reinterpret_cast<const uint8_t *>(message.data()),
            message.size())
    {}

    uint32_t read ()
    {
        uint32_t result;
        m_stream.ReadVarint32(& result);
        return result;
    }
};

} // namespace io
} // namespace pomagma

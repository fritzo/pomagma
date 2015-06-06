#pragma once

#include <pomagma/util/util.hpp>

namespace google {
namespace protobuf {

class Message;

namespace io {

class FileInputStream;
class FileOutputStream;
class GzipInputStream;
class GzipOutputStream;

} // namespace io
} // namespace protobuf
} // namespace google

namespace pomagma {
namespace protobuf {

class InFile : noncopyable
{
public:

    explicit InFile (const std::string & filename);
    ~InFile ();

    const std::string & filename () const { return m_filename; }

    void read (google::protobuf::Message & message);

    // This tries to parse a single piece of a message. Does not clear message.
    bool try_read_chunk (google::protobuf::Message & message);

private:

    const std::string m_filename;
    const int m_fid;
    google::protobuf::io::FileInputStream * m_file;
    google::protobuf::io::GzipInputStream * m_gzip;
};

class OutFile : noncopyable
{
public:

    explicit OutFile (const std::string & filename);
    ~OutFile ();

    const std::string & filename () const { return m_filename; }

    void write (const google::protobuf::Message & message);

private:

    const std::string m_filename;
    const int m_fid;
    google::protobuf::io::FileOutputStream * m_file;
    google::protobuf::io::GzipOutputStream * m_gzip;
};

} // namespace protobuf
} // namespace pomagma

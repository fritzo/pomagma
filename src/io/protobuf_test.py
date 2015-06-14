from nose.tools import assert_equal
from pomagma.util.testing import for_each
from pomagma.util import in_temp_dir
from pomagma.io.protobuf import InFile
from pomagma.io.protobuf import OutFile
from pomagma.io import protobuf_test_pb2

EXAMPLES = []

message = protobuf_test_pb2.TestMessage()
EXAMPLES.append(message)

message = protobuf_test_pb2.TestMessage()
message.optional_string = 'test'
EXAMPLES.append(message)

message = protobuf_test_pb2.TestMessage()
message.repeated_string.append('test1')
message.repeated_string.append('test2')
EXAMPLES.append(message)

message = protobuf_test_pb2.TestMessage()
message.optional_string = 'test'
message.repeated_string.append('test1')
message.repeated_string.append('test2')
sub_message = message.optional_message
sub_message.repeated_message.add().optional_string = 'sub sub 1'
sub_message.repeated_message.add().repeated_string.append('sub sub 2')
message.repeated_message.add().optional_string = 'sub 1'
message.repeated_message.add().repeated_string.append('sub 2')
EXAMPLES.append(message)


@for_each(EXAMPLES)
def test_write_read(expected):
    print 'Testing read(write({}))'.format(expected)
    actual = protobuf_test_pb2.TestMessage()
    with in_temp_dir():
        filename = 'test.pb'
        with OutFile(filename) as f:
            f.write(expected)
        with InFile(filename) as f:
            f.read(actual)
    assert_equal(actual, expected)

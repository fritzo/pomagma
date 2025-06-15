from google.protobuf import text_format

from pomagma.io import protobuf_test_pb2
from pomagma.io.protobuf import InFile, OutFile
from pomagma.util import in_temp_dir
from pomagma.util.testing import for_each


def parse(text, Message=protobuf_test_pb2.TestMessage):
    message = Message()
    text_format.Merge(text, message)
    return message


EXAMPLES = [
    parse(""),
    parse(
        """
        optional_string: 'test'
    """
    ),
    parse(
        """
        repeated_string: 'test1'
        repeated_string: 'test2'
    """
    ),
    parse(
        """
        optional_string: 'test'
        repeated_string: 'test1'
        repeated_string: 'test2'
        optional_message: {
            repeated_message: {}
            repeated_message: {
                optional_string: 'sub sub 1'
                repeated_string: 'sub'
            }
            repeated_message: {
                optional_string: 'sub 1'
            }
            repeated_message: {
                repeated_string: 'sub 2'
            }
        }
    """
    ),
]


@for_each(EXAMPLES)
def test_write_read(expected):
    print(f"Testing read(write({expected}))")
    actual = protobuf_test_pb2.TestMessage()
    with in_temp_dir():
        filename = "test.pb"
        with OutFile(filename) as f:
            f.write(expected)
        with InFile(filename) as f:
            f.read(actual)
    assert actual == expected


protobuf: compiler/syntax_pb2.py language/language_pb2.py atlas/structure_pb2.py cartographer/messages_pb2.py analyst/messages_pb2.py io/protobuf_test_pb2.py

compiler/syntax_pb2.py: compiler/syntax.proto
	protoc compiler/syntax.proto --python_out=. --cpp_out=.

language/language_pb2.py: language/language.proto
	protoc language/language.proto --python_out=. --cpp_out=.

atlas/structure_pb2.py: atlas/structure.proto
	protoc atlas/structure.proto --python_out=. --cpp_out=.

cartographer/messages_pb2.py: cartographer/messages.proto
	protoc cartographer/messages.proto --python_out=. --cpp_out=.

analyst/messages_pb2.py: analyst/messages.proto
	protoc analyst/messages.proto --python_out=. --cpp_out=.

io/protobuf_test_pb2.py: io/protobuf_test.proto
	protoc io/protobuf_test.proto --python_out=. --cpp_out=.

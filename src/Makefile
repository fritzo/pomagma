
protobuf: compiler/syntax_pb2.py language/language_pb2.py atlas/structure_pb2.py cartographer/messages_pb2.py analyst/messages_pb2.py io/protobuf_test_pb2.py

compiler/syntax_pb2.py: compiler/syntax.proto
	cd compiler ; protoc syntax.proto --python_out=. --cpp_out=.

language/language_pb2.py: language/language.proto
	cd language ; protoc language.proto --python_out=. --cpp_out=.

atlas/structure_pb2.py: atlas/structure.proto
	cd atlas ; protoc structure.proto --python_out=. --cpp_out=.

cartographer/messages_pb2.py: cartographer/messages.proto
	cd cartographer ; protoc messages.proto --python_out=. --cpp_out=.

analyst/messages_pb2.py: analyst/messages.proto
	cd analyst ; protoc messages.proto --python_out=. --cpp_out=.

io/protobuf_test_pb2.py: io/protobuf_test.proto
	cd io ; protoc protobuf_test.proto --python_out=. --cpp_out=.

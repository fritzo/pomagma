all: protobuf_test_pb2.py

protobuf_test_pb2.py: protobuf_test.proto
	protoc protobuf_test.proto --python_out=. --cpp_out=.

all: protobuf_test.pb.h

protobuf_test.pb.h: protobuf_test.proto
	protoc protobuf_test.proto --cpp_out=.

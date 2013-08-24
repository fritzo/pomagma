
all: messages_pb2.py

messages_pb2.py: messages.proto
	protoc messages.proto --python_out=. --cpp_out=.

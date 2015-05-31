
all: structure_pb2.py

structure_pb2.py: structure.proto
	protoc structure.proto --python_out=. --cpp_out=.

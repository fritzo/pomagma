
all: language_pb2.py

language_pb2.py: language.proto
	protoc language.proto --python_out=. --cpp_out=.

# TODO add make target for *.language

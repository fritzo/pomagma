
all: language_pb2.py h4.language sk.language skj.language skrj.language

language_pb2.py: language.proto
	protoc language.proto --python_out=. --cpp_out=.

%.language: %.json util.py language_pb2.py __init__.py
	python util.py compile $< $@

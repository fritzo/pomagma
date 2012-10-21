
all: language_pb2.py h4.language

language_pb2.py: language.proto
	protoc language.proto --python_out=. --cpp_out=.

%.language: %.json run.py language_pb2.py __init__.py
	python run.py compile $< $@

# TODO add make target for *.language


all: language_pb2.py h4.language sk.language

language_pb2.py: language.proto
	protoc language.proto --python_out=. --cpp_out=.

sk.json: sk.py
	python sk.py

skj.json: skj.py
	python skj.py

%.language: %.json run.py language_pb2.py __init__.py
	python run.py compile $< $@

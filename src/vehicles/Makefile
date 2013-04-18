
all: vehicles_pb2.py h4.vehicle sk.vehicle skj.vehicle

vehicles_pb2.py: vehicles.proto
	protoc vehicles.proto --python_out=. --cpp_out=.

sk.json: sk.py
	python sk.py

skj.json: skj.py
	python skj.py

%.vehicle: %.json run.py vehicles_pb2.py __init__.py
	python run.py compile $< $@

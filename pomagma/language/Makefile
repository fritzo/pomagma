
all: h4.language sk.language skj.language skja.language skrj.language

%.language: %.json util.py language_pb2.py __init__.py
	python util.py compile $< $@

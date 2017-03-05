.SILENT:
.PHONY: all lint test FORCE

PY_FILES := $(shell find . | grep '\.py$$' | grep -v '_pb2\.py')

all: lint FORCE

lint:
	$(info flake8)
	flake8 --jobs auto --ignore=E402 $(PY_FILES)

test: lint
	$(info py.test)
	py.test

FORCE:

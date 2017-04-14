.SILENT:
.PHONY: all lint test clean FORCE

PY_FILES := $(shell find . | grep '\.py$$' | grep -v '_pb2\.py')

all: lint FORCE

lint: FORCE
	$(info flake8)
	flake8 --jobs auto --ignore=E402 $(PY_FILES)

test: lint
	$(info py.test)
	py.test --nbval

clean:
	find . | grep '\.pyc$$' | xargs rm
	rm -Rf __pycache__ .ipynb_checkpoints

FORCE:

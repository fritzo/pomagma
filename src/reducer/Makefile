.SILENT:
.PHONY: all lint pyformat test clean FORCE

PY_FILES := $(shell find . | grep '\.py$$' | grep -v '_pb2\.py')
CPU_COUNT=$(shell python -c 'import multiprocessing as m; print m.cpu_count()')

all: lint FORCE

lint: FORCE
	# TODO Use clang-tidy
	$(info flake8)
	flake8 --jobs auto --ignore=E402 $(PY_FILES)

pyformat: FORCE
	$(info isort)
	isort --skip messages_pb2.py --apply
	$(info pyformat)
	pyformat --jobs 0 --aggressive --in-place $(PY_FILES)

test: lint
	$(info pytest)
	# This freezes, probably due to multiprocessing conflicts.
	# pytest -n $(CPU_COUNT)
	pytest

clean:
	find . | grep '\.pyc$$' | xargs rm
	rm -Rf __pycache__

FORCE:

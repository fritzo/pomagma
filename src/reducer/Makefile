.SILENT:
.PHONY: all lint clang-format pyformat format test clean FORCE

PY_FILES := $(shell find . | grep '\.py$$' | grep -v '_pb2\.py')
CPP_FILES := $(shell find . | grep '\.[ch]pp$$' | grep -v '\.pb\.')

all: lint FORCE

lint: FORCE
	# TODO Use clang-tidy
	$(info flake8)
	@flake8 --jobs auto --ignore=E402 $(PY_FILES)

clang-format: FORCE
	$(info clang-format)
	@clang-format -i --style="{BasedOnStyle: Google, IndentWidth: 4}" \
	  $(CPP_FILES)

pyformat: FORCE
	$(info pyformat)
	@pyformat --jobs 0 --aggressive --in-place $(PY_FILES)

format: clang-format pyformat FORCE

test: lint
	py.test

clean:
	find . | grep '\.pyc$$' | xargs rm
	rm -Rf __pycache__

FORCE:

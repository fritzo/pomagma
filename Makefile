.SILENT:
.PHONY: all protobuf tags lint python codegen debug release cpp-test unit-test bootstrap h4-test sk-test skj-test skja-test skrj-test batch-test small-test test big-test sk skj skja skrj profile clean FORCE

THEORY = skrj

# File lists for linting and formatting.
PY_FILES := *.py $(shell find src -not -wholename 'src/third_party/*' \
                                  -name '*.py' \
				  -not -name '*_pb2.py')
CPP_FILES := $(shell find src -not -wholename 'src/third_party/*' \
                              -regex '.*\.[ch]pp$$' \
			      -not -name '*.pb.*')

all: data/blob bootstrap FORCE
	$(MAKE) python
	$(MAKE) -C src/language
	$(MAKE) codegen codegen-summary debug release

echo-py-files: FORCE
	echo $(PY_FILES)
echo-cpp-files: FORCE
	echo $(CPP_FILES)


protobuf: FORCE
	$(MAKE) -C src protobuf

tags: protobuf FORCE
	cd src ; ctags -R
	cd src ; cscope -bcqR

clang-ctags:
	mkdir -p build/tags
	cd build/tags && cmake -DCMAKE_EXPORT_COMPILE_COMMANDS=1 ../..
	clang-ctags --output src/tags \
	  --compile-commands build/tags build/tags/compile_commands.json

lint: FORCE
	# TODO Use clang-tidy.
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

python: protobuf lint FORCE
	pip install -e .

codegen: FORCE
	python -m pomagma.compiler batch-compile

codegen-summary: FORCE
	python -m pomagma.compiler batch-extract-tasks

CMAKE = cmake
ifdef CC
	CMAKE += -DCMAKE_C_COMPILER=$(shell which $(CC))
endif
ifdef CXX
	CMAKE += -DCMAKE_CXX_COMPILER=$(shell which $(CXX))
endif

debug: protobuf FORCE
	mkdir -p build/debug
	cd build/debug \
	  && $(CMAKE) -DCMAKE_BUILD_TYPE=Debug ../.. \
	  && $(MAKE) VERBOSE=1

release: protobuf FORCE
	mkdir -p build/release
	cd build/release \
	  && $(CMAKE) -DCMAKE_BUILD_TYPE=RelWithDebInfo ../.. \
	  && $(MAKE)

DEBUG_LOG="$(shell pwd)/data/debug.log"
cpp-test: all FORCE
	rm -f $(DEBUG_LOG)
	POMAGMA_LOG_FILE=$(DEBUG_LOG) \
	  CTEST_OUTPUT_ON_FAILURE=1 $(MAKE) -C build/debug test \
	  || { cat $(DEBUG_LOG); exit 1; }

unit-test: all bootstrap FORCE
	./vet.py check || { ./diff.py codegen; exit 1; }
	POMAGMA_DEBUG=1 py.test -v --nbval --ignore=pomagma/third_party pomagma
	$(MAKE) cpp-test
	POMAGMA_DEBUG=1 pomagma.make profile-misc
	pomagma.make profile-misc

data/blob:
	mkdir -p data/blob

bootstrap: FORCE
	mkdir -p data
	cp -Rn bootstrap/* data/ \
	  || test -e data/atlas/$(THEORY)/region.normal.2047.pb
	cd data/atlas/$(THEORY) \
	  && (test -e world.pb || ln region.normal.2047.pb world.pb) \
	  && test -e world.normal.pb || ln region.normal.2047.pb world.normal.pb

h4-test: all FORCE
	POMAGMA_DEBUG=1 pomagma.make test-atlas h4
sk-test: all FORCE
	POMAGMA_DEBUG=1 pomagma.make test-atlas sk
skj-test: all FORCE
	POMAGMA_DEBUG=1 pomagma.make test-atlas skj
skja-test: all FORCE
	POMAGMA_DEBUG=1 pomagma.make test-atlas skja
skrj-test: all FORCE
	POMAGMA_DEBUG=1 pomagma.make test-atlas skrj
batch-test: all FORCE
	POMAGMA_DEBUG=1 pomagma.make test-atlas

small-test: all FORCE
	$(MAKE) unit-test
	$(MAKE) h4-test
	@echo '----------------'
	@echo 'PASSED ALL TESTS'

test: all FORCE
	$(MAKE) unit-test
	$(MAKE) batch-test
	@echo '----------------'
	@echo 'PASSED ALL TESTS'

big-test: test FORCE
	$(MAKE) unit-test
	$(MAKE) batch-test
	POMAGMA_DEBUG=1 pomagma.make test-analyst
	@echo '----------------'
	@echo 'PASSED ALL TESTS'

h4: all
	pomagma make h4
sk: all
	pomagma make sk
skj: all
	pomagma make skj
skja: all
	pomagma make skja
skrj: all
	pomagma make skrj

profile: release
	pomagma.make profile-misc
	# pomagma.make profile-surveyor
	# pomagma.make profile-cartographer

clean: FORCE
	rm -rf build lib
	git clean -fdx -e pomagma.egg-info -e node_modules -e data

FORCE:

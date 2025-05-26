.SILENT:
.PHONY: all build protobuf tags lint codegen debug release cpp-test unit-test bootstrap h4-test sk-test skj-test skja-test skrj-test batch-test small-test test big-test sk skj skja skrj profile clean setup-vcpkg FORCE

THEORY = skrj

# File lists for linting and formatting.
PY_FILES := *.py $(shell find src -not -wholename 'src/third_party/*' \
                                  -name '*.py' \
				  -not -name '*_pb2.py')
CPP_FILES := $(shell find src -not -wholename 'src/third_party/*' \
                              -regex '.*\.[ch]pp$$' \
			      -not -name '*.pb.*')

# Detect number of CPU cores for parallel builds
UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Darwin)
    NPROC := $(shell sysctl -n hw.ncpu)
else
    NPROC := $(shell nproc)
endif

all: build FORCE

build: data/blob bootstrap protobuf FORCE
	$(MAKE) -C src/language
	$(MAKE) codegen codegen-summary debug release

install: FORCE
	uv pip install --no-build-isolation -e .

setup-vcpkg: FORCE
	@echo "Setting up vcpkg for dependency management..."
	chmod +x setup-vcpkg.sh
	./setup-vcpkg.sh

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
	black --check $(PY_FILES)
	ruff check $(PY_FILES)

clang-format: FORCE
	$(info clang-format)
	@clang-format -i --style="{BasedOnStyle: Google, IndentWidth: 4}" \
	  $(CPP_FILES)

black: FORCE
	$(info black)
	@black $(PY_FILES)

ruff: FORCE
	$(info ruff)
	@ruff check --fix $(PY_FILES)
	@ruff format $(PY_FILES)

format: clang-format black ruff FORCE

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

# Add vcpkg toolchain if available
ifneq ($(wildcard vcpkg/scripts/buildsystems/vcpkg.cmake),)
	CMAKE += -DCMAKE_TOOLCHAIN_FILE=$(shell pwd)/vcpkg/scripts/buildsystems/vcpkg.cmake
else ifdef VCPKG_ROOT
	CMAKE += -DCMAKE_TOOLCHAIN_FILE=$(VCPKG_ROOT)/scripts/buildsystems/vcpkg.cmake
endif

debug: protobuf FORCE
	mkdir -p build/debug
	cd build/debug \
	  && $(CMAKE) -DCMAKE_BUILD_TYPE=Debug ../.. \
	  && $(MAKE) -j$(NPROC)
	ln -sf build/debug/compile_commands.json compile_commands.json

release: protobuf FORCE
	mkdir -p build/release
	cd build/release \
	  && $(CMAKE) -DCMAKE_BUILD_TYPE=RelWithDebInfo ../.. \
	  && $(MAKE) -j$(NPROC)
	ln -sf build/release/compile_commands.json compile_commands.json

DEBUG_LOG="$(shell pwd)/data/debug.log"
cpp-test: debug FORCE
	rm -f $(DEBUG_LOG)
	POMAGMA_LOG_FILE=$(DEBUG_LOG) \
	  CTEST_OUTPUT_ON_FAILURE=1 $(MAKE) -j$(NPROC) -C build/debug test \
	  || { cat $(DEBUG_LOG); exit 1; }

unit-test: build bootstrap FORCE
	./vet.py check || { ./diff.py codegen; exit 1; }
	pytest -v --nbval-lax pomagma
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

h4-test: FORCE
	POMAGMA_DEBUG=1 pomagma.make test-atlas h4
sk-test: FORCE
	POMAGMA_DEBUG=1 pomagma.make test-atlas sk
skj-test: FORCE
	POMAGMA_DEBUG=1 pomagma.make test-atlas skj
skja-test: FORCE
	POMAGMA_DEBUG=1 pomagma.make test-atlas skja
skrj-test: FORCE
	POMAGMA_DEBUG=1 pomagma.make test-atlas skrj
batch-test: FORCE
	POMAGMA_DEBUG=1 pomagma.make test-atlas

small-test: FORCE
	$(MAKE) unit-test
	$(MAKE) h4-test
	@echo '----------------'
	@echo 'PASSED ALL TESTS'

test: FORCE
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

h4:
	pomagma make h4
sk:
	pomagma make sk
skj:
	pomagma make skj
skja:
	pomagma make skja
skrj:
	pomagma make skrj

profile: release
	pomagma.make profile-misc
	# pomagma.make profile-surveyor
	# pomagma.make profile-cartographer

clean: FORCE
	rm -rf build lib compile_commands.json
	cd src && git clean -fdx -e third_party/

clean-vcpkg: FORCE
	rm -rf vcpkg

mrproper: clean clean-vcpkg FORCE
	git clean -fdx -e pomagma.egg-info -e node_modules -e data

FORCE:

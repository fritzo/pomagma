.SILENT:
THEORY = skrj
PY_FILES := *.py $(shell find src | grep '.py$$' | grep -v '_pb2.py')

all: data/blob bootstrap FORCE
	$(MAKE) python
	$(MAKE) tags codegen tasks debug release

protobuf: FORCE
	$(MAKE) -C src/analyst
	$(MAKE) -C src/atlas
	$(MAKE) -C src/cartographer
	$(MAKE) -C src/io
	$(MAKE) -C src/language

tags: protobuf FORCE
	cd src ; ctags -R
	cd src ; cscope -bcqR

lint: FORCE
	$(info pyflakes)
	@pyflakes $(PY_FILES)
	$(info pep8)
	@pep8 --ignore=E402 $(PY_FILES)

python: protobuf lint FORCE
	pip install -e .

codegen: FORCE
	python -m pomagma.compiler batch-compile

tasks: FORCE
	python -m pomagma.compiler batch-extract-tasks

debug: FORCE
	mkdir -p build/debug
	cd build/debug \
	  && cmake -DCMAKE_BUILD_TYPE=Debug ../.. \
	  && $(MAKE)

release: FORCE
	mkdir -p build/release
	cd build/release \
	  && cmake -DCMAKE_BUILD_TYPE=RelWithDebInfo ../.. \
	  && $(MAKE)

DEBUG_LOG="$(shell pwd)/data/debug.log"
cpp-test: all FORCE
	rm -f $(DEBUG_LOG)
	POMAGMA_LOG_FILE=$(DEBUG_LOG) \
	  CTEST_OUTPUT_ON_FAILURE=1 $(MAKE) -C build/debug test \
	  || { cat $(DEBUG_LOG); exit 1; }

unit-test: all bootstrap FORCE
	python vet.py check
	POMAGMA_DEBUG=1 nosetests -v pomagma
	$(MAKE) cpp-test
	POMAGMA_DEBUG=1 npm test
	python -m pomagma.make profile-misc

data/blob:
	mkdir -p data/blob

bootstrap: FORCE
	mkdir -p data
	cp -rn bootstrap/* data/
	cd data/atlas/$(THEORY) \
	  && (test -e world.pb || ln region.normal.2047.pb world.pb) \
	  && test -e world.normal.pb || ln region.normal.2047.pb world.normal.pb

h4-test: all FORCE
	POMAGMA_DB_FORMAT=h5 POMAGMA_DEBUG=1 \
	  python -m pomagma.make test-atlas h4
	POMAGMA_DB_FORMAT=pb POMAGMA_DEBUG=1 \
	  python -m pomagma.make test-atlas h4
sk-test: all FORCE
	POMAGMA_DEBUG=1 python -m pomagma.make test-atlas sk
skj-test: all FORCE
	POMAGMA_DEBUG=1 python -m pomagma.make test-atlas skj
skja-test: all FORCE
	POMAGMA_DEBUG=1 python -m pomagma.make test-atlas skja
skrj-test: all FORCE
	POMAGMA_DEBUG=1 python -m pomagma.make test-atlas skrj
batch-test: all FORCE
	POMAGMA_DEBUG=1 python -m pomagma.make test-atlas

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
	POMAGMA_DEBUG=1 python -m pomagma.make test-analyst
	@echo '----------------'
	@echo 'PASSED ALL TESTS'

h4: all
	python -m pomagma make h4
sk: all
	python -m pomagma make sk
skj: all
	python -m pomagma make skj
skja: all
	python -m pomagma make skja
skrj: all
	python -m pomagma make skrj

profile:
	python -m pomagma.make profile-misc
	#python -m pomagma.make profile-surveyor
	#python -m pomagma.make profile-cartographer

clean: FORCE
	rm -rf build lib
	git clean -fdx -e pomagma.egg-info -e node_modules -e data

FORCE:

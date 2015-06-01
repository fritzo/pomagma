THEORY = skrj
PY_FILES := *.py $(shell find src | grep '.py$$' | grep -v '_pb2.py')

all: bootstrap fixture FORCE
	$(MAKE) python
	$(MAKE) tags codegen tasks debug release

protobuf: FORCE
	$(MAKE) -C src/language
	$(MAKE) -C src/atlas
	$(MAKE) -C src/cartographer
	$(MAKE) -C src/analyst

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

cpp-test: all FORCE
	POMAGMA_LOG_FILE=$(shell pwd)/data/debug.log $(MAKE) -C build/debug test

unit-test: all fixture FORCE
	python vet.py check
	POMAGMA_DEBUG=1 nosetests -v pomagma
	POMAGMA_LOG_FILE=$(shell pwd)/data/debug.log $(MAKE) -C build/debug test
	POMAGMA_DEBUG=1 npm test

fixture: data/atlas/$(THEORY)/region.normal.2047.h5 FORCE
data/atlas/$(THEORY)/region.normal.2047.h5:
	mkdir -p data/atlas/$(THEORY)/
	7z e bootstrap/atlas/$(THEORY)/region.normal.2047.h5.7z -odata/atlas/$(THEORY)

bootstrap: data/atlas/$(THEORY)/world.normal.h5 FORCE
data/atlas/$(THEORY)/world.normal.h5: data/atlas/$(THEORY)/region.normal.2047.h5
	cd data/atlas/$(THEORY) \
	  && (test -e world.h5 || ln -s region.normal.2047.h5 world.h5) \
	  && test -e world.normal.h5 \
	  || ln -s region.normal.2047.h5 world.normal.h5 \

h4-test: all FORCE
	POMAGMA_DEBUG=1 python -m pomagma.make test-atlas h4
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
	#python -m pomagma.make profile-util
	python -m pomagma.make profile-surveyor
	# TODO add profile for sequential & concurrent dense_set

clean: FORCE
	rm -rf build lib
	git clean -fdx -e pomagma.egg-info -e node_modules -e data

FORCE:

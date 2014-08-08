all:
	$(MAKE) python
	$(MAKE) -C src/language
	$(MAKE) -C src/cartographer
	$(MAKE) -C src/analyst
	$(MAKE) debug release

python: FORCE
	find src | grep '.py$$' | grep -v '_pb2.py' | xargs pyflakes
	find src | grep '.py$$' | grep -v '_pb2.py' | xargs pep8
	pip install -e .

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

unit-test: all FORCE
	POMAGMA_DEBUG=1 nosetests -v pomagma
	POMAGMA_DEBUG=1 \
	  POMAGMA_LOG_FILE=$(shell pwd)/data/debug.log \
	  $(MAKE) -C build/debug test
	$(MAKE) node-test

data/atlas/skrj/region.normal.2047.h5:
	mkdir -p data/atlas/skrj/
	7z e testdata/atlas/skrj/region.normal.2047.h5.7z -odata/atlas/skrj
node-test: all data/atlas/skrj/region.normal.2047.h5 FORCE
	POMAGMA_DEBUG=1 npm test

h4-test: all FORCE
	POMAGMA_DEBUG=1 python -m pomagma.make test-atlas h4
sk-test: all FORCE
	POMAGMA_DEBUG=1 python -m pomagma.make test-atlas sk
skj-test: all FORCE
	POMAGMA_DEBUG=1 python -m pomagma.make test-atlas skj
skrj-test: all FORCE
	POMAGMA_DEBUG=1 python -m pomagma.make test-atlas skrj
batch-test: all FORCE
	POMAGMA_DEBUG=1 python -m pomagma.make test-atlas

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
skrj: all
	python -m pomagma make skrj

profile:
	python -m pomagma.make profile-util
	python -m pomagma.make profile-surveyor
	# TODO add profile for sequential & concurrent dense_set

clean: FORCE
	rm -rf build lib
	git clean -fdx -e pomagma.egg-info -e node_modules -e data

FORCE:

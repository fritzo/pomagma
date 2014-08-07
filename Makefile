all:
	$(MAKE) static-check
	pip install -e .
	$(MAKE) -C src/language
	$(MAKE) -C src/cartographer
	$(MAKE) -C src/analyst
	POMAGMA_DEBUG= python -m pomagma.make build
	python -m pomagma.make build

install:
	./install.sh
	$(MAKE) all

set-ulimit: FORCE
	$(call ulimit -c unlimited)

static-check: FORCE
	find src | grep '.py$$' | grep -v '_pb2.py' | xargs pyflakes
	find src | grep '.py$$' | grep -v '_pb2.py' | xargs pep8

unit-test: all set-ulimit FORCE
	POMAGMA_DEBUG= python -m pomagma.make test-units -v
batch-test: all set-ulimit FORCE
	POMAGMA_DEBUG= python -m pomagma.make test-atlas
h4-test: all set-ulimit FORCE
	POMAGMA_DEBUG= python -m pomagma.make test-atlas h4
sk-test: all set-ulimit FORCE
	POMAGMA_DEBUG= python -m pomagma.make test-atlas sk
skj-test: all set-ulimit FORCE
	POMAGMA_DEBUG= python -m pomagma.make test-atlas skj
skrj-test: all set-ulimit FORCE
	POMAGMA_DEBUG= python -m pomagma.make test-atlas skrj
test: all set-ulimit FORCE
	POMAGMA_DEBUG= python -m pomagma.make test-units -v
	POMAGMA_DEBUG= python -m pomagma.make test-atlas

h4: all
	python -m pomagma make h4
sk: all
	python -m pomagma make sk
skj: all
	python -m pomagma make skj
skrj: all
	python -m pomagma make skrj

python-libs:
	@$(MAKE) -C src/language all

profile:
	python -m pomagma.make profile
	# TODO add profile for sequential & concurrent dense_set

clean: FORCE
	rm -rf build lib include
	git clean -fdx -e pomagma.egg-info -e node_modules -e data

FORCE:

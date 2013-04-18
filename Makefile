all:
	pip install -e .
	$(MAKE) -C src/language
	$(MAKE) -C src/structure
	POMAGMA_DEBUG= python -m pomagma build
	python -m pomagma build

set-ulimit: FORCE
	$(call ulimit -c unlimited)

PYFLAKES = find src | grep '.py$$' | grep -v '_pb2.py' | xargs pyflakes

unit-test: set-ulimit
	@$(PYFLAKES)
	POMAGMA_DEBUG= python -m pomagma unit-test
batch-test: set-ulimit
	POMAGMA_DEBUG= python -m pomagma batch-test
h4-test: set-ulimit
	POMAGMA_DEBUG= python -m pomagma batch-test h4
sk-test: set-ulimit
	POMAGMA_DEBUG= python -m pomagma batch-test sk
skj-test: set-ulimit
	POMAGMA_DEBUG= python -m pomagma batch-test skj
test: unit-test
	@$(PYFLAKES)
	POMAGMA_DEBUG= python -m pomagma unit-test
	POMAGMA_DEBUG= python -m pomagma batch-test

h4:
	python -m pomagma.batch survey h4
sk:
	python -m pomagma.batch survey sk
skj:
	python -m pomagma.batch survey skj

python-libs:
	@$(MAKE) -C src/language all
	@$(MAKE) -C src/structure all

profile:
	python -m pomagma profile

clean: FORCE
	rm -rf build lib include
	git clean -fdx -e pomagma.egg-info

FORCE:

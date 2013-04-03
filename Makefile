all:
	pip install -e .
	$(MAKE) -C src/language
	POMAGMA_DEBUG= python -m pomagma build
	python -m pomagma build

unit-test:
	POMAGMA_DEBUG= python -m pomagma unit-test
batch-test:
	POMAGMA_DEBUG= python -m pomagma batch-test
h4-test:
	POMAGMA_DEBUG= python -m pomagma batch-test h4
sk-test:
	POMAGMA_DEBUG= python -m pomagma batch-test sk
skj-test:
	POMAGMA_DEBUG= python -m pomagma batch-test skj
test:
	POMAGMA_DEBUG= python -m pomagma unit-test
	POMAGMA_DEBUG= python -m pomagma batch-test

h4:
	python -m pomagma.batch grow h4
sk:
	python -m pomagma.batch grow sk
skj:
	python -m pomagma.batch grow skj

python-libs:
	@$(MAKE) -C src/language all
	@$(MAKE) -C src/structure all

profile:
	python -m pomagma profile

clean: FORCE
	rm -rf lib include build log
	git clean -fdx -e pomagma.egg-info

FORCE:

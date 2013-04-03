all:
	pip install -e .
	$(MAKE) -C src/language
	$(MAKE) -C src/structure
	POMAGMA_DEBUG= python -m pomagma build
	python -m pomagma build

set-ulimit: FORCE
	$(call ulimit -c unlimited)

unit-test: set-ulimit
	POMAGMA_DEBUG= python -m pomagma unit-test
batch-test: set-ulimit
	POMAGMA_DEBUG= python -m pomagma batch-test
h4-test: set-ulimit
	POMAGMA_DEBUG= python -m pomagma batch-test h4
sk-test: set-ulimit
	POMAGMA_DEBUG= python -m pomagma batch-test sk
skj-test: set-ulimit
	POMAGMA_DEBUG= python -m pomagma batch-test skj
test: set-ulimit
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

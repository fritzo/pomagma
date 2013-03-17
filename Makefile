all:
	POMAGMA_DEBUG= python -m pomagma build
	python -m pomagma build

test:
	POMAGMA_DEBUG= python -m pomagma unit-test
	POMAGMA_DEBUG= python -m pomagma batch-test

python-libs:
	@$(MAKE) -C src/language all
	@$(MAKE) -C src/structure all

# TODO move this to python
profile: build/release log FORCE
	@echo 'PWD =' `pwd`
	@(cd build/release && cmake -DCMAKE_BUILD_TYPE=RelWithDebInfo ../..)
	@$(MAKE) -C build/release
	@echo '' > log/profile.log
	@for i in `ls build/release/src/*/*_profile`; do \
		POMAGMA_LOG_LEVEL=2 \
		POMAGMA_LOG_FILE=$(CURDIR)/log/profile.log \
		$$i; \
	done

clean: FORCE
	rm -rf lib include build log
	git clean -fdx -e pomagma.egg-info

FORCE:

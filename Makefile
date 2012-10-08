
all: install

build:
	mkdir build
build/debug: build
	test -d build/debug || mkdir build/debug
build/release: build
	test -e build/release || mkdir build/release
log:
	mkdir log

install: build/release
	@(cd build/release && \
	cmake -DCMAKE_BUILD_TYPE=RelWithDebInfo ../.. \
	&& $(MAKE) && $(MAKE) install)

test: build/debug log
	@echo 'PWD =' `pwd`
	@(cd build/debug && cmake -DCMAKE_BUILD_TYPE=Debug ../..)
	@$(MAKE) -C build/debug
	@echo '' > log/test.log
	@POMAGMA_LOG_LEVEL=3 \
	POMAGMA_LOG_FILE=$(CURDIR)/log/test.log \
	$(MAKE) -C build/debug test \
	|| (grep -C3 -i error log/test.log && false)
	@$(MAKE) -C src/compiler test

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


PROCS=$(shell python -c 'from multiprocessing import cpu_count as c; print c()')

all: install

test: unit-test

build:
	mkdir build
build/debug: build
	test -d build/debug || mkdir build/debug
build/release: build
	test -e build/release || mkdir build/release
log:
	mkdir log

python-libs:
	@$(MAKE) -C src/language all
	@$(MAKE) -C src/structure all

install: python-libs build/release
	@(cd build/release && \
	cmake -DCMAKE_BUILD_TYPE=RelWithDebInfo ../.. \
	&& $(MAKE) && $(MAKE) install)

unit-test: python-libs build/debug log
	@(cd build/debug && cmake -DCMAKE_BUILD_TYPE=Debug ../..)
	@$(MAKE) -C build/debug
	@echo '' > log/test.log
	@POMAGMA_LOG_LEVEL=3 \
	POMAGMA_LOG_FILE=$(CURDIR)/log/test.log \
	$(MAKE) -C build/debug test \
	|| (grep -C3 -i error log/test.log && false)
	@$(MAKE) -C src/compiler test

h4-test: build/debug log
	@$(MAKE) -C src/language h4.language
	@(cd build/debug && cmake -DCMAKE_BUILD_TYPE=Debug ../..)
	@$(MAKE) -C build/debug/src/grower h4.grower
	@echo '' > log/h4.log
	#POMAGMA_SIZE=14400 # TODO slow
	POMAGMA_SIZE=1023 \
	POMAGMA_THREADS=$(PROCS) \
	POMAGMA_LOG_LEVEL=4 \
	POMAGMA_LOG_FILE=log/h4.log \
	build/debug/src/grower/h4.grower TODO_structure_out \
	|| (grep -C3 -i error log/h4.log && false)

h4: install log
	@$(MAKE) -C src/language h4.language
	@(cd build/debug && cmake -DCMAKE_BUILD_TYPE=Debug ../..)
	@$(MAKE) -C build/debug/src/grower h4.grower
	@echo '' > log/h4.log
	POMAGMA_SIZE=14400 \
	POMAGMA_THREADS=$(PROCS) \
	POMAGMA_LOG_LEVEL=4 \
	POMAGMA_LOG_FILE=log/h4.log \
	bin/h4.grower TODO_structure_out \
	|| (grep -C3 -i error log/h4.log && false)

sk-test: build/debug log
	@$(MAKE) -C src/language sk.language
	@(cd build/debug && cmake -DCMAKE_BUILD_TYPE=Debug ../..)
	@$(MAKE) -C build/debug/src/grower sk.grower
	@echo '' > log/sk.log
	POMAGMA_SIZE=2047 \
	POMAGMA_THREADS=$(PROCS) \
	POMAGMA_LOG_LEVEL=4 \
	POMAGMA_LOG_FILE=log/sk.log \
	build/debug/src/grower/sk.grower TODO_structure_out \
	|| (grep -C3 -i error log/sk.log && false)

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

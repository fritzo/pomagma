
PROCS=$(shell python -c 'from multiprocessing import cpu_count as c; print c()')
export POMAGMA_THREADS := $(PROCS)

all: install

test:
	@$(MAKE) unit-test
	@$(MAKE) h4-test
	@$(MAKE) sk-test
	@$(MAKE) skj-test

build:
	mkdir build
build/debug: build
	test -d build/debug || mkdir build/debug
build/release: build
	test -e build/release || mkdir build/release
log:
	mkdir log
data:
	mkdir data

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

h4-test: build/debug log data
	@$(MAKE) -C src/language h4.language
	@(cd build/debug && cmake -DCMAKE_BUILD_TYPE=Debug ../..)
	@$(MAKE) -C build/debug/src/grower h4.grower
	@echo '' > log/h4-test.log
	@echo -e '\nTesting grower with theory h4'
	@#POMAGMA_SIZE=14400 # TODO slow
	POMAGMA_SIZE=511 \
	POMAGMA_LOG_LEVEL=4 \
	POMAGMA_LOG_FILE=log/h4-test.log \
	build/debug/src/grower/h4.grower data/h4-test.h5 \
	|| (grep -C3 -i error log/h4-test.log && false)
	POMAGMA_SIZE=1023 \
	POMAGMA_LOG_LEVEL=4 \
	POMAGMA_LOG_FILE=log/h4-test.log \
	build/debug/src/grower/h4.grower data/h4-test.h5 data/h4-test.h5 \
	|| (grep -C3 -i error log/h4-test.log && false)

h4: install log data
	@echo '' > log/h4.log
	@echo -e '\nRunning grower with theory h4'
	POMAGMA_SIZE=14400 \
	POMAGMA_LOG_LEVEL=4 \
	POMAGMA_LOG_FILE=log/h4.log \
	bin/h4.grower data/h4.h5 \
	|| (grep -C3 -i error log/h4.log && false)

sk-test: build/debug log data
	@$(MAKE) -C src/language sk.language
	@(cd build/debug && cmake -DCMAKE_BUILD_TYPE=Debug ../..)
	@$(MAKE) -C build/debug/src/grower sk.grower
	@echo '' > log/sk-test.log
	@echo -e '\nTesting grower with theory sk'
	POMAGMA_SIZE=1023 \
	POMAGMA_LOG_LEVEL=4 \
	POMAGMA_LOG_FILE=log/sk-test.log \
	build/debug/src/grower/sk.grower data/sk-test.h5 \
	|| (grep -C3 -i error log/sk-test.log && false)
	POMAGMA_SIZE=1535 \
	POMAGMA_LOG_LEVEL=4 \
	POMAGMA_LOG_FILE=log/sk-test.log \
	build/debug/src/grower/sk.grower data/sk-test.h5 data/sk-test.h5 \
	|| (grep -C3 -i error log/sk-test.log && false)

sk: install log data
	@echo '' > log/sk.log
	@echo -e '\nRunning grower with theory skj'
	POMAGMA_SIZE=2047 \
	POMAGMA_LOG_LEVEL=4 \
	POMAGMA_LOG_FILE=log/sk.log \
	bin/sk.grower data/sk.h5 \
	|| (grep -C3 -i error log/sk.log && false)

skj-test: build/debug log data
	@$(MAKE) -C src/language skj.language
	@(cd build/debug && cmake -DCMAKE_BUILD_TYPE=Debug ../..)
	@$(MAKE) -C build/debug/src/grower skj.grower
	@echo '' > log/skj-test.log
	@echo -e '\nTesting grower with theory skj'
	POMAGMA_SIZE=1535 \
	POMAGMA_LOG_LEVEL=4 \
	POMAGMA_LOG_FILE=log/skj-test.log \
	build/debug/src/grower/skj.grower data/skj-test.h5 \
	|| (grep -C3 -i error log/skj-test.log && false)
	POMAGMA_SIZE=2047 \
	POMAGMA_LOG_LEVEL=4 \
	POMAGMA_LOG_FILE=log/skj-test.log \
	build/debug/src/grower/skj.grower data/skj-test.h5 data/skj-test.h5 \
	|| (grep -C3 -i error log/skj-test.log && false)

skj: install log data
	@echo '' > log/skj.log
	@echo -e '\nRunning grower with theory skj'
	POMAGMA_SIZE=2047 \
	POMAGMA_LOG_LEVEL=4 \
	POMAGMA_LOG_FILE=log/skj.log \
	bin/skj.grower data/skj.h5 \
	|| (grep -C3 -i error log/skj.log && false)

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


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
	(cd build/release && \
	cmake -DCMAKE_BUILD_TYPE=RelWithDebInfo ../.. \
	&& $(MAKE) && $(MAKE) install)

test: build/debug log
	@echo 'PWD =' `pwd`
	(cd build/debug && cmake -DCMAKE_BUILD_TYPE=Debug ../..)
	$(MAKE) -C build/debug
	echo '' > log/test.log
	POMAGMA_LOG_LEVEL=3 \
	POMAGMA_LOG_FILE=$(CURDIR)/log/test.log \
	$(MAKE) -C build/debug test \
	|| (grep -C3 -i error log/test.log && false)
	$(MAKE) -C pomagma test

clean: FORCE
	rm -rf lib include build log
	find . -type f | grep '\.log$$' | xargs rm -f
	find . -type f | grep '^core' | xargs rm -f

FORCE:

#!/bin/sh
test -e build || mkdir build && \
	(cd build && cmake .. && make && POMAGMA_LOG_LEVEL=3 make test)

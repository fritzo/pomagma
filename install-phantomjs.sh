#!/bin/sh

if [ ! -f phantomjs ]; then
	mkdir phantomjs
	cd phandomjs
	wget https://phantomjs.googlecode.com/files/phantomjs-1.9.1-linux-x86_64.tar.bz2
fi

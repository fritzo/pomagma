#!/bin/sh

if [ "$CC" = "gcc" ]
then
       	make small-test
else
	make cpp-test
fi

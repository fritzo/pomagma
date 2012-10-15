#!/bin/sh

i="sudo apt-get install -y"

$i cmake g++
$i libboost-all-dev
$i libtbb-dev libzmq-dev
$i libprotobuf-dev protobuf-compiler
$i python-pip python-nose virtualenvwrapper

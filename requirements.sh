#!/bin/sh

i="sudo apt-get install -y"

$i cmake g++
$i libboost-all-dev
$i libtbb-dev
$i libzmq-dev python-zmq
$i libprotobuf-dev protobuf-compiler python-protobuf
$i python-pip python-nose virtualenvwrapper

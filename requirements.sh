#!/bin/sh

i="sudo apt-get install -y"

$i cmake g++
$i libboost-all-dev libtbb-dev libzmq-dev
$i python-pip python-nose virtualenvwrapper

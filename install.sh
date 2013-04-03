#!/bin/sh

sudo apt-get install -y \
  cmake make g++ \
  libboost1.48-all-dev \
  libtbb-dev \
  libsparsehash-dev \
  libprotobuf-dev protobuf-compiler python-protobuf \
  libhdf5-serial-dev \
  libssl-dev \
  python-tables \
  python-pip virtualenvwrapper \
  graphviz \
  gdb \
  #libzmq-dev python-zmq \
  #

source ~/.bashrc
workon pomagma || mkvirtualenv --system-site-packages pomagma
workon pomagma
pip install -r requirements.txt
make


#!/bin/sh

sudo apt-get install -y \
  cmake make g++ \
  libboost1.48-all-dev \
  libtbb-dev \
  libsparsehash-dev \
  libprotobuf-dev protobuf-compiler python-protobuf \
  libhdf5-serial-dev \
  libssl-dev \
  python-pip virtualenvwrapper \
  python-tables \
  graphviz \
  gdb \
  p7zip-full \
  rubygems \
  libzmq-dev \
  #python-zmq \
  #

sudo gem install foreman

# FIXME mkvirtualenv never automatically works; I have to do it by hand; wtf
workon pomagma || mkvirtualenv --system-site-packages pomagma
workon pomagma && pip install -r requirements.txt && pip install -e . && make


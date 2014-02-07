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
  firefox \
  #jsdoc-toolkit \
  #phantomjs \
  #python-zmq \
  #

sudo gem install foreman

# FIXME mkvirtualenv never automatically works; possible solutions:
# http://stackoverflow.com/questions/13111881
# http://stackoverflow.com/questions/18627250
# http://stackoverflow.com/questions/18337767
workon pomagma || mkvirtualenv --system-site-packages pomagma
deactivate && workon pomagma &&\
pip install -r requirements.txt &&\
pip install -e . &&\
make


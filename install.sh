#!/bin/sh

sudo apt-get install -y \
  cmake make g++ \
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
  libzmq-dev \
  nodejs \
  firefox \
  #jsdoc-toolkit \
  #phantomjs \
  #python-zmq \
  #

sudo apt-get install -y rubygems
sudo gem install foreman

sudo npm install -g phantomjs

# FIXME mkvirtualenv never automatically works; possible solutions:
# http://stackoverflow.com/questions/13111881
# http://stackoverflow.com/questions/18627250
# http://stackoverflow.com/questions/18337767
workon pomagma || mkvirtualenv --system-site-packages pomagma
deactivate && workon pomagma &&\
pip install -r requirements.txt &&\
pip install -e . &&\
make


#!/bin/sh

sudo add-apt-repository -y ppa:chris-lea/node.js
sudo apt-get update
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
  #

# package libraries are installed from package.json
npm update
# testing libraries are installed by hand
sudo npm install -g phantomjs
sudo npm install -g mocha
sudo npm install -g chai

# FIXME mkvirtualenv never automatically works; possible solutions:
# http://stackoverflow.com/questions/13111881
# http://stackoverflow.com/questions/18627250
# http://stackoverflow.com/questions/18337767
#workon pomagma || mkvirtualenv --system-site-packages pomagma
#deactivate && workon pomagma &&\
#pip install -r requirements.txt &&\
#pip install -e . &&\
#make


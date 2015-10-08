#!/bin/bash

sudo apt-get update
sudo apt-get install -y \
  ccache \
  cmake \
  cscope \
  ctags \
  g++ \
  gdb \
  graphviz \
  libboost-filesystem-dev \
  libgoogle-perftools-dev \
  libprotobuf-dev \
  libssl-dev \
  libtbb-dev \
  libzmq-dev \
  make \
  p7zip-full \
  protobuf-compiler \
  python-pip \
  python-protobuf \
  virtualenvwrapper \
  #

if env | grep -q ^VIRTUAL_ENV=
then
	echo "Installing in $VIRTUAL_ENV"
else
	echo "Making new virtualenv"
	mkvirtualenv --system-site-packages pomagma
	deactivate
	workon pomagma
fi
pip install -r requirements.txt
pip install -e .
. $VIRTUAL_ENV/bin/activate

make all

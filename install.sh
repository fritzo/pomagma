#!/bin/bash
set -x

case "`uname`" in
  'Linux')
    sudo apt-get update
    sudo apt-get install -y \
      ccache \
      cmake \
      g++ \
      gdb \
      graphviz \
      libboost-filesystem-dev \
      libgoogle-glog-dev \
      libgoogle-perftools-dev \
      libprotobuf-dev \
      libssl-dev \
      libtbb-dev \
      libzmq3-dev \
      make \
      p7zip-full \
      protobuf-compiler \
      python-pip \
      python-protobuf \
      #
    ;;
  'Darwin')
    brew update
    brew bundle -v  # installs dependencies from Brewfile
    ;;
  *)
    echo "Unsupported OS: `uname`"
    return 1
    ;;
esac

if env | grep -q ^VIRTUAL_ENV=
then
  echo "Installing in $VIRTUAL_ENV"
else
  echo "Making new virtualenv"
  mkvirtualenv --system-site-packages pomagma
  if [ "`uname`" -eq 'Darwin' ]; then
    echo "Using clang-omp compiler"
    echo 'export CC=/usr/local/bin/clang-omp' >> \
      "$VIRTUAL_ENV/bin/postactivate"
    echo 'export CXX=/usr/local/bin/clang-omp++' >> \
      "$VIRTUAL_ENV/bin/postactivate"
  fi
  deactivate
  workon pomagma
fi
pip install -r requirements.txt
pip install -e .
. $VIRTUAL_ENV/bin/activate

make all

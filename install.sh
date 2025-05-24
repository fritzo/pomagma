#!/bin/bash
set -euo pipefail
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
      libboost-filesystem1.54-dev \
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

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "uv is not installed. Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi

# Create virtual environment with uv if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment with uv"
    uv venv --system-site-packages
fi

# Set compiler environment variables for Darwin
if [ "`uname`" = 'Darwin' ]; then
    echo "Setting up dependencies for macOS"
    # Install libomp for OpenMP support
    brew install libomp
    # Make sure LLVM is installed
    brew install llvm
    echo "Dependencies installed. Use 'source .env' to set up compiler environment."
fi

# Install dependencies
echo "Installing Python dependencies"
source .venv/bin/activate
uv pip install parsable setuptools  # Needed in setup.py
uv pip install --no-build-isolation -e .

# Run build
uv run make all

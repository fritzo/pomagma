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
    echo "Setting up macOS dependencies..."
    
    # Install basic tools via Homebrew (minimal set)
    brew update
    brew install cmake ccache git
    
    # Set up vcpkg for C++ dependencies
    echo "Setting up vcpkg for consistent C++ dependency management..."
    chmod +x setup-vcpkg.sh
    ./setup-vcpkg.sh
    
    # Source vcpkg environment
    source ./vcpkg-env.sh
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

# Install dependencies
echo "Installing Python dependencies"
source .venv/bin/activate
uv pip install parsable setuptools  # Needed in setup.py
uv pip install --no-build-isolation -e .

# Run build
if [ "`uname`" = 'Darwin' ]; then
    echo "Building with vcpkg dependencies..."
    source ./vcpkg-env.sh
fi

uv run make all

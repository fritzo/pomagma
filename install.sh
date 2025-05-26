#!/bin/bash
set -euo pipefail
set -x

case "`uname`" in
  'Linux')
    sudo apt update
    sudo apt install -y \
      bzip2 \
      ccache \
      cmake \
      clang \
      gdb \
      graphviz \
      libc++-dev \
      libgoogle-perftools-dev \
      libomp-dev \
      linux-libc-dev \
      make \
      p7zip-full \
      pkg-config \
      zip \
      #
    
    # Set compiler to clang
    export CC=/usr/bin/clang
    export CXX=/usr/bin/clang++
    
    # Set up vcpkg for C++ dependencies
    echo "Setting up vcpkg for consistent C++ dependency management..."
    chmod +x setup-vcpkg.sh
    ./setup-vcpkg.sh
    
    # Source vcpkg environment
    source ./env.sh
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
    source ./env.sh
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
    source $HOME/.local/bin/env
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
if [ "`uname`" = 'Darwin' ] || [ "`uname`" = 'Linux' ]; then
    echo "Building with vcpkg dependencies..."
    source ./env.sh
    
    # Ensure compiler settings are preserved on Linux
    if [ "`uname`" = 'Linux' ]; then
        export CC=/usr/bin/clang
        export CXX=/usr/bin/clang++
        echo "Using clang compiler: CC=$CC, CXX=$CXX"
    fi
fi

uv run make all

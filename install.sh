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
    echo "Setting up compilers for macOS"
    # Install libomp for OpenMP support
    brew install libomp
    # Add OpenMP configuration to activation script
    echo "Adding OpenMP configuration to .venv/bin/activate"
    cat >> .venv/bin/activate << 'EOF'

# OpenMP support for macOS (added by install.sh)
export CC=clang
export CXX=clang++
export LDFLAGS="-L/opt/homebrew/opt/libomp/lib"
export CPPFLAGS="-I/opt/homebrew/opt/libomp/include"
EOF
    echo "Added OpenMP flags to activation script"
fi

# Install dependencies
echo "Installing Python dependencies"
uv pip install parsable
uv pip install -r requirements.txt
uv pip install -e .

# Run build
uv run make all

#!/bin/bash
# Environment configuration for pomagma development
# Source this file with: source env.sh

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Set up vcpkg environment if available
if [ -d "$SCRIPT_DIR/vcpkg" ]; then
  export VCPKG_ROOT="$SCRIPT_DIR/vcpkg"
  export PATH="$VCPKG_ROOT:$PATH"
  export CMAKE_TOOLCHAIN_FILE="$VCPKG_ROOT/scripts/buildsystems/vcpkg.cmake"
  
  # Detect OS and architecture to determine correct triplet
  OS="$(uname)"
  ARCH="$(uname -m)"
  
  case "$OS" in
    'Linux')
      case "$ARCH" in
        'x86_64')
          TRIPLET="x64-linux"
          ;;
        'aarch64')
          TRIPLET="arm64-linux"
          ;;
        *)
          TRIPLET="x64-linux"  # fallback
          ;;
      esac
      ;;
    'Darwin')
      case "$ARCH" in
        'x86_64')
          TRIPLET="x64-osx"
          ;;
        'arm64')
          TRIPLET="arm64-osx"
          ;;
        *)
          TRIPLET="x64-osx"  # fallback
          ;;
      esac
      ;;
    *)
      TRIPLET="x64-linux"  # fallback
      ;;
  esac
  
  export VCPKG_DEFAULT_TRIPLET="$TRIPLET"
  
  # Add vcpkg tools to PATH if available
  if [ -d "$SCRIPT_DIR/vcpkg_installed/$TRIPLET/tools/protobuf" ]; then
    export PATH="$SCRIPT_DIR/vcpkg_installed/$TRIPLET/tools/protobuf:$PATH"
    echo "vcpkg protoc added to PATH"
  fi
  
  echo "vcpkg environment configured: $VCPKG_ROOT (triplet: $VCPKG_DEFAULT_TRIPLET)"
else
  echo "vcpkg not found in $SCRIPT_DIR/vcpkg - run ./setup-vcpkg.sh first"
fi

# Detect OS and set appropriate compiler paths
case "$(uname)" in
  'Darwin')
    # macOS: Use Homebrew LLVM for -march=native and -fopenmp support
    LLVM_PATH=$(find /opt/homebrew/Cellar/llvm -name "bin" -type d | head -1)
    if [ -n "$LLVM_PATH" ]; then
      export CC="$LLVM_PATH/clang"
      export CXX="$LLVM_PATH/clang++"
      # Add LLVM bin to PATH so 'which clang' finds the right one
      export PATH="$LLVM_PATH:$PATH"
      echo "Using Homebrew LLVM: $LLVM_PATH"
    else
      echo "Warning: Homebrew LLVM not found. Install with: brew install llvm"
      export CC=clang
      export CXX=clang++
    fi
    
    # OpenMP support
    export LDFLAGS="-L/opt/homebrew/opt/libomp/lib $LDFLAGS"
    export CPPFLAGS="-I/opt/homebrew/opt/libomp/include $CPPFLAGS"
    
    # Add Homebrew libraries to linker path
    export LDFLAGS="-L/opt/homebrew/lib $LDFLAGS"
    export CPPFLAGS="-I/opt/homebrew/include $CPPFLAGS"
    
    # Add Homebrew to PATH
    export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:$PATH"
    ;;
  'Linux')
    # Linux: Use clang compilers for consistency with install.sh
    export CC=/usr/bin/clang
    export CXX=/usr/bin/clang++
    echo "Using system clang: CC=$CC, CXX=$CXX"
    ;;
  *)
    echo "Unknown OS: $(uname)"
    ;;
esac

# Add local bin to PATH
export PATH="$HOME/.local/bin:$PATH" 
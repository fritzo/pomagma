#!/bin/bash
# Environment configuration for pomagma development
# Source this file with: source env.sh

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
    # Linux: Use system compilers (usually support the flags we need)
    export CC=gcc
    export CXX=g++
    ;;
  *)
    echo "Unknown OS: $(uname)"
    ;;
esac

# Add local bin to PATH
export PATH="$HOME/.local/bin:$PATH" 
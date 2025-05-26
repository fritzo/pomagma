#!/bin/bash
# Source this file to set up vcpkg environment
# Usage: source ./vcpkg-env.sh

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Set up vcpkg environment
export VCPKG_ROOT="$SCRIPT_DIR/vcpkg"
export PATH="$VCPKG_ROOT:$PATH"

# Set CMake toolchain file for vcpkg
export CMAKE_TOOLCHAIN_FILE="$VCPKG_ROOT/scripts/buildsystems/vcpkg.cmake"

# Set vcpkg triplet for macOS
export VCPKG_DEFAULT_TRIPLET="x64-osx"

echo "vcpkg environment configured:"
echo "  VCPKG_ROOT: $VCPKG_ROOT"
echo "  CMAKE_TOOLCHAIN_FILE: $CMAKE_TOOLCHAIN_FILE"
echo "  VCPKG_DEFAULT_TRIPLET: $VCPKG_DEFAULT_TRIPLET" 
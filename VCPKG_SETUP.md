# vcpkg Setup for Pomagma

This document explains how to use vcpkg for consistent dependency management in Pomagma, particularly to resolve compatibility issues with protobuf, abseil, and related libraries on macOS.

## Overview

vcpkg is a C++ package manager that provides consistent, reproducible builds across platforms. We use it to manage:

- protobuf (Protocol Buffers)
- abseil-cpp (Abseil C++ libraries)
- boost (Boost C++ libraries)
- TBB (Threading Building Blocks)
- OpenSSL
- ZeroMQ
- GTest

## Quick Start

### Automatic Setup

Run the installation script which will set up vcpkg automatically:

```bash
./install.sh
```

### Manual Setup

1. Set up vcpkg:
```bash
make setup-vcpkg
```

2. Source the vcpkg environment:
```bash
source ./vcpkg-env.sh
```

3. Build the project:
```bash
make clean && make debug
```

## Environment Variables

The vcpkg setup configures these environment variables:

- `VCPKG_ROOT`: Path to the vcpkg installation
- `CMAKE_TOOLCHAIN_FILE`: Path to the vcpkg CMake toolchain
- `VCPKG_DEFAULT_TRIPLET`: Target triplet (x64-osx for macOS)

## Dependency Versions

vcpkg uses a baseline commit to ensure consistent versions across all dependencies. The current baseline is specified in `vcpkg.json` and `vcpkg-configuration.json`.

## Troubleshooting

### Protobuf Version Conflicts

If you encounter protobuf version conflicts:

1. Clean the build directory:
```bash
make clean
```

2. Ensure vcpkg environment is loaded:
```bash
source ./vcpkg-env.sh
```

3. Rebuild:
```bash
make debug
```

### Python Protobuf Compatibility

The Python protobuf version in `pyproject.toml` is pinned to version 5, which should be compatible with the vcpkg-managed protobuf library.

### Homebrew Conflicts

If you have conflicting Homebrew packages, you can temporarily disable them:

```bash
# Backup current PATH
export OLD_PATH="$PATH"

# Remove Homebrew from PATH temporarily
export PATH=$(echo $PATH | tr ':' '\n' | grep -v '/opt/homebrew' | tr '\n' ':')

# Source vcpkg environment
source ./vcpkg-env.sh

# Build
make clean && make debug

# Restore PATH
export PATH="$OLD_PATH"
```

## Files

- `vcpkg.json`: vcpkg manifest file listing dependencies
- `vcpkg-configuration.json`: vcpkg configuration with baseline
- `setup-vcpkg.sh`: Script to install and configure vcpkg
- `vcpkg-env.sh`: Environment setup script
- `CMakeLists.txt`: Updated to use vcpkg toolchain
- `Makefile`: Updated with vcpkg support

## Benefits

1. **Consistent Versions**: All dependencies use the same baseline
2. **Reproducible Builds**: Same versions across different machines
3. **Isolation**: No conflicts with system packages
4. **Cross-Platform**: Works on macOS, Linux, and Windows
5. **ABI Compatibility**: All libraries built with same compiler flags 
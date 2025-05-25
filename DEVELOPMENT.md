# Development Setup

## Quick Start
1. Run the installer: `./install.sh`
2. Set up environment: `source env.sh`  
3. Build: `make debug`

## About env.sh
The `env.sh` script configures the environment to use Homebrew's LLVM (which supports `-march=native` and `-fopenmp`) instead of Apple's Clang.

## Modernized Dependencies
- **GoogleTest/GoogleMock**: Now uses CMake FetchContent (no more vendored code)
- **Compiler**: Uses Homebrew LLVM for full flag support on macOS
- **Architecture-aware**: Automatically configures for x86_64 vs ARM64

## macOS Core Dumping

To enable core dumps on macOS for debugging crashes: run
```sh
ulimit -c unlimited
sudo sysctl kern.coredump=1
sudo sysctl kern.corefile=/cores/core.%P
```
Our CMakeLists.txt codesigns all executables with `debug.entitlements`.

## Coding style

- Prefer annotations like `__attribute__((unused))` over hacks.

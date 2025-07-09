#!/bin/bash
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Setting up vcpkg for Pomagma...${NC}"

# Detect OS and architecture, then set triplet
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
        echo -e "${RED}Unsupported Linux architecture: $ARCH${NC}"
        exit 1
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
        echo -e "${RED}Unsupported macOS architecture: $ARCH${NC}"
        exit 1
        ;;
    esac
    ;;
  *)
    echo -e "${RED}Unsupported OS: $OS${NC}"
    exit 1
    ;;
esac

echo -e "${YELLOW}Detected OS: $OS, Architecture: $ARCH, using triplet: $TRIPLET${NC}"

# Check if vcpkg is already installed
if [ ! -d "vcpkg" ]; then
    echo -e "${YELLOW}Cloning vcpkg...${NC}"
    git clone https://github.com/Microsoft/vcpkg.git
    cd vcpkg
    ./bootstrap-vcpkg.sh
    cd ..
else
    echo -e "${GREEN}vcpkg already exists, updating...${NC}"
    cd vcpkg
    git pull
    ./bootstrap-vcpkg.sh
    cd ..
fi

# Set up environment variables
export VCPKG_ROOT="$(pwd)/vcpkg"
export PATH="$VCPKG_ROOT:$PATH"

echo -e "${YELLOW}Installing dependencies via vcpkg...${NC}"

# Install dependencies
./vcpkg/vcpkg install --triplet=$TRIPLET

echo -e "${GREEN}vcpkg setup complete!${NC}"
echo -e "${YELLOW}To use vcpkg in your shell, run:${NC}"
echo "export VCPKG_ROOT=\"$(pwd)/vcpkg\""
echo "export PATH=\"\$VCPKG_ROOT:\$PATH\""
echo ""
echo -e "${YELLOW}Or source the environment file:${NC}"
echo "source ./env.sh" 
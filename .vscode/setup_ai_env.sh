#!/bin/bash
# Setup script for AI agents to match user environment

# Change to the correct directory
cd /Users/fritzo/pomagma

# Source the project environment
source env.sh

# Activate the virtual environment  
source .venv/bin/activate

# Export useful variables
export PYTHONPATH="${PWD}/src:${PYTHONPATH}"
export POMAGMA_DEBUG=1

echo "AI environment setup complete:"
echo "  Working directory: $(pwd)"
echo "  Python: $(which python)"
echo "  UV: $(which uv)"
echo "  Environment: ${VIRTUAL_ENV}" 
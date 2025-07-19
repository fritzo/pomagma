# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Setup Commands

**Initial Setup:**
```bash
# Run installer (handles dependencies, uv virtual environment, vcpkg)
./install.sh

# Set up environment (configures compilers, vcpkg paths)
source env.sh
```

**Core Build Commands:**
```bash
make all                    # Full build (data/blob, bootstrap, protobuf, codegen, debug, release)
make debug                  # Debug build with compile_commands.json
make release                # Release build with compile_commands.json
make clean                  # Clean build artifacts (avoid when possible per Cursor rules)
```

**Testing Commands:**
```bash
make small-test             # Quick tests (~5 CPU minutes) - runs on CI
make test                   # Standard test suite (~1 CPU hour)
make big-test               # Extended tests with analyst testing
make cpp-test               # C++ tests only
make unit-test              # Python + C++ unit tests, includes vet check

# Individual atlas tests
make h4-test                # Test h4 atlas
make sk-test                # Test sk atlas  
make skj-test               # Test skj atlas
make skja-test              # Test skja atlas
make skrj-test              # Test skrj atlas
```

**Linting and Formatting:**
```bash
make lint                   # Run ruff, mypy on Python files
make format                 # Format code (clang-format + ruff)
make ruff-format           # Python formatting only
make clang-format          # C++ formatting only
```

**Code Generation and Vetting:**
```bash
make codegen               # Generate code from theories  
make codegen-summary       # Generate task summaries
./vet.py check             # Check generated files against vetted versions
./vet.py vet all           # Update vetted hashes for all files
./diff.py codegen          # Show differences in generated code
```

## Architecture Overview

Pomagma is a client-server inference engine for extensional lambda-join-calculus with the following architecture:

**Core Components:**
- **Atlas** (`/pomagma/atlas/`) - In-memory combinatory databases with macro/micro variants
- **Analyst** (`/pomagma/analyst/`) - Main database server and client for analysis queries
- **Surveyor** (`/pomagma/surveyor/`) - Forward-chaining inference engine for building databases
- **Cartographer** (`/pomagma/cartographer/`) - Scalable inference engine for large-scale operations
- **Compiler** (`/pomagma/compiler/`) - Compiles forward-chaining inference strategies
- **Reducer** (`/pomagma/reducer/`) - Lambda-calculus interpreters with comprehensive unit tests

**Language and Theory:**
- **Language** (`/pomagma/language/`) - Probabilistic grammars for Solomonoff priors
- **Theory** (`/pomagma/theory/`) - Theories of ordered combinatory algebras (.theory files)
- **Theorist** (`/pomagma/theorist/`) - Machine learning for theory conjecturing

**Python Integration:**
- **Torch** (`/pomagma/torch/`) - PyTorch frontend for machine learning over symbolic expressions
- **Examples** (`/pomagma/examples/`) - Applications using the analyst (Sudoku, synthesis, etc.)
- **IO** (`/pomagma/io/`) - Serialization utilities and S3 integration

## Key Development Workflows

**Client-Server Model:**
```bash
# Start analysis server
pomagma analyze             # Starts server with pre-built E-graph

# Connect from Python client  
pomagma connect            # Interactive client session
# Or use Python API: from pomagma import analyst
```

**E-graph Management:**
```bash
# Get pre-built E-graph from S3 (requires AWS credentials)
pomagma pull

# Build custom E-graph from scratch
pomagma make max_size=10000
```

**Development Environment:**
- Uses uv for Python virtual environment management
- vcpkg for C++ dependency management (protobuf, GoogleTest, etc.)
- CMake builds create `compile_commands.json` for language servers
- Supports both debug and release builds with proper compiler flags

## Testing Framework

**Python:** pytest with fixtures, hypothesis for property testing, nbval for notebook testing
**C++:** GoogleTest/GoogleMock via CMake FetchContent  
**Integration:** Cross-language testing between Python client and C++ server

**Critical Testing Rules (from Cursor rules):**
- NEVER delete or relax tests without explicit permission
- Tests are critical documentation of expected behavior
- Fix implementation rather than removing failing tests
- Do not relax timeouts, assertions, or test generators

## Code Generation System

Pomagma uses a sophisticated code generation system:
- Theories in `/pomagma/theory/*.theory` generate facts, programs, symbols, tasks
- All generated code must be vetted using `./vet.py` before committing
- Use `./diff.py codegen` to review changes to generated code
- Tests will fail until generated code changes are vetted

## Syntax Format Guidance

Choose syntax based on use case:
- **Expression** - Rich APIs for compiler frontends and symbolic manipulation
- **Term Polish notation** - Minimal memory for reduction algorithms  
- **Term S-expressions** - Human-readable for testing and debugging
- **@combinator DSL** - Functional Python syntax compiling to combinatory logic
- **ObTree** - PyTorch integration for machine learning
- **C++ Corpus Term** - Maximum performance for production servers
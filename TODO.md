## Renovation Plan

### Phase 1: update dependencies; get tests to pass

- [ ] **Apply 2to3 and manual Python 2→3 fixes**
  - [ ] Run `2to3` tool, fix print statements, string handling, exception syntax
  - [ ] Update imports: `cPickle` → `pickle`, `xrange` → `range`, etc.

- [ ] **Upgrade protobuf to 3+**
  - [ ] Update `requirements.txt`: `protobuf<3.0` → `protobuf>=3.20.0`
  - [ ] Fix protobuf API changes in Python code
  - [ ] Update install.sh package names

- [ ] **Upgrade googletest/googlemock**
  - [ ] Update to GoogleTest 1.12+, fix API changes in C++ tests

- [ ] **Replace g++ with modern clang++**
  - [ ] Update CMakeLists.txt: `std=c++0x` → `std=c++17`, minimum version to 3.10
  - [ ] Update Ubuntu/macOS package dependencies in install.sh
  - [ ] Replace `python-*` packages with `python3-*` equivalents

### Phase 2: clean up once tests pass

- [ ] **Add python linting & formatting**
  - [ ] **black**: Add to requirements.txt, create make target, format codebase
  - [ ] **ruff**: Replace flake8, configure ruff.toml
  - [ ] **mypy**: Add basic type checking, start with ignore-errors mode

- [ ] **Add C++ linting & formatting**
  - [ ] **clang-format**: Create .clang-format config, format C++ codebase
  - [ ] **clang-tidy**: Add .clang-tidy config and make target

- [ ] **replace python `@inputs` with type hints**
  - [ ] Audit `@inputs` usage, replace with proper `typing` module hints

- [ ] **replace travis.yml with github actions**
  - [ ] Create `.github/workflows/ci.yml`, port test matrix, remove `.travis.yml`

### Phase 3: Testing and validation

- [ ] **Verify all test suites pass**: `make small-test`, `make test`, `make big-test`
- [ ] **Performance regression testing**: Run benchmarks, compare with baseline
- [ ] **Update documentation**: Installation instructions, Python 3.8+ requirements

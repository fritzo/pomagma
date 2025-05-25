# The Pomagma System

- [Dataflow Architecture](#dataflow-architecture)
- [File Organization](#file-organization)
- [Configuring](#configuring)
- [Testing](#testing)
- [Benchmarking](#benchmarking)
- [Vetting changes](#vetting-changes)

## Dataflow Architecture <a name="dataflow"/>

![Architecture](/doc/architecture.png)

### State

- Language - finite generating grammars of combinatory algebras
- Theory - finite relational theories of combinatory algebras
- Corpus - a body of writing expressed in combinatory algebras
- Atlas - a mechanically generated database of facts with short proofs

### Actors

- Surveyor - explores a region of a combinatory algebra via forward chaining
- Cartographer - directs surveyors and incorporates surveys into the atlas
- Linguist - fits languages to analyst workload and proposes new basic terms
- Language Reviewer - ensures new language modifications are safe
- Theorist - makes conjectures and tries to prove them using various strategies
- Theory Reviewer - suggests new inference rules to address open conjectures
- Analyst - services static analysis queries using a read-only atlas
- Editor - interactively annotates the corpus with static analysis results
- Writer - captures and formalizes domain problems in the corpus

### Workflows

- Explore: grow atlas by forward-chaining inference; generate conjectures
- Extend Theory: review cartographer's conjectures; propose new inference rules
- Recover (after inconsistency): scrap atlas; fix error in theory; rebuild
- Edit: write code; respond to static analysis of code
- Fit Language: fit grammar weights to corpus; propose new words

## File Organization

- [/doc](/doc) - developer documentation
- [/data](/data) - generated data, mirroring an S3 bucket
- [/src](/src) - source code (C++, python, DSLs)
  - [/src/theory](/src/theory) -
    theories of ordered combinatory algebras
  - [/src/theorist](/src/theorist) - machine learning for conjecturing theories
  - [/src/language](/src/language) -
    probabilistic grammars representing Solomonoff priors
  - [/src/linguist](/src/linguist) - machine learning for tuning languages
  - [/src/analyst](/src/analyst) -
    combinatory database server and client
  - [/src/examples](/src/examples) - example applications using the analyst
  - [/src/surveyor](/src/surveyor) -
    the main forward-chaining engine for building databases
  - [/src/cartographer](/src/cartographer) - a scalable weaker inference engine
  - [/src/atlas](/src/atlas) -
    data structures for in-memory combinatory databases
  - [/src/io](/src/io) -
    serialization utilities for persisting combinatory databases
  - [/src/compiler](/src/compiler) -
    compiler for forward chaining inference strategies
  - [/src/reducer](/src/reducer) -
    interpreters for &lambda;-calculus with lots of unit tests
  - [/src/corpus](/src/corpus) -
    literate code expressed in combinatory algebra
  - [/src/util](/src/util) - core utilities
- [/bootstrap](/bootstrap) - a small git-cached atlas for testing
- [/build](/build) - destination of C++ builds
- [/pomagma](/pomagma) - a symbolic link to appease `pip install -e`
- [/include/pomagma](/include/pomagma) - a symbolic link to appease g++

## Configuring

To run in debug mode, set the environment variable

    POMAGMA_DEBUG=1

To use specific ports or addresses, override these defaults

    POMAGMA_ANALYST_ADDRESS=tcp://localhost:34936

Pomagma uses even ports for production and odd ports for testing.

### Language Server Support

Pomagma automatically generates a `compile_commands.json` file for language servers
like clangd to provide accurate C++ IntelliSense, error checking, and navigation.
This file is automatically created and symlinked to the project root when running:

    make debug      # creates compile_commands.json -> build/debug/compile_commands.json
    make release    # creates compile_commands.json -> build/release/compile_commands.json

The symlink is ignored by git and will be automatically recreated on each build.

To store data on S3, pomagma needs Amazon AWS credentials and an S3 bucket.
These are specified by environment variables

    AWS_ACCESS_KEY_ID=...
    AWS_SECRET_ACCESS_KEY=...
    POMAGMA_BUCKET=Example-Amazon-S3-bucket

## Testing

Pomagma comes with three default levels of tests:

    make small-test     # runs on travis-ci
    make test
    make big-test       # more expensive with larger atlas

More expensive tests are available via

    pomagma.make test-atlas
    pomagma.make test-analyst

## Benchmarking

Full system profiling information is written to the `INFO` log.
See [/doc/benchmarks.md](/doc/benchmarks.md) for the latest results.

C++ microbenchmarks are available via

    pomagma.make profile-misc

Larger benchmarks for forward-chaining inference are available via

    pomagma.make profile-surveyor
    pomagma.make profile-cartographer

To profile the footprint of memoized functions in the compiler,
define the environment variable

    POMAGMA_PROFILE_MEMOIZED=1

## Vetting Changes

Pomagma includes a vetting system to manage changes in generated code.
To commit changes to [pomagma.compiler](/src/compiler)
or [src/theory/*.theory](/src/theory), you first need to vet the changes using
[vet.py](/vet.py) which updates [vetted_hashes.csv](/vetted_hashes.csv).

    vi src/theory/types.theory      # ...make some changes...
    make codegen                    # rebuilds generated code
    ./vet.py check                  # checks whether anything changed
    ./diff.py codegen               # ...review changes to generated code...
    ./vet.py vet all                # updates vetted_hashes.csv
    git add .                       # commits changes + vetted hashes

Note that `vet.py check` is run automatically during unit tests,
so tests will fail until you vet all changes to generated code.

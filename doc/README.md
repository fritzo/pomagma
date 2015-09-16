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
- [/src](/src) - source code (C++, python)
  - [/src/theory](/src/theory) - theories of combinatory algebras
  - [/src/language](/src/language) - probabilistic grammars
  - [/src/corpus](/src/corpus) - literate code expressed in combinatory algebra
  - [/src/atlas](/src/atlas) - code to manage the atlas
  - [/src/surveyor](/src/surveyor) - the main forward-chaining engine
  - [/src/cartographer](/src/cartographer) - a scalable weaker inference engine
  - [/src/analyst](/src/analyst) - the query server
  - [/src/compiler](/src/compiler) - syntactic algorithms
  - [/src/linguist](/src/linguist) - machine learning for tuning languages
  - [/src/theorist](/src/theorist) - machine learning for conjecturing theories
  - [/src/util](/src/util) - core utilities
  - [/src/io](/src/io) - serialization utilities
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

Pomagma has microbenchmarks available via

    pomagma.make profile-misc

as well as larger benchmarks for forward-chaining inference

    pomagma.make profile-surveyor
    pomagma.make profile-cartographer

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

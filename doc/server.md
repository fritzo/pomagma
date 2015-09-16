# Administering a Pomagma Server

* [File Organization](#files)
* [Testing](#testing)
* [Configuring](#configuring)
* [Dataflow Architecture](#dataflow)

## File Organization <a name="files"/>

- [/src](/src) - source code (C++, python, javascript)
- [/doc](/doc) - developer documentation
- [/data](/data) - generated data, mirroring an S3 bucket
- [/bootstrap](/bootstrap) - a small git-cached atlas for testing
- [/build](/build) - destination of C++ builds
- [/pomagma](/pomagma) - a symbolic link to appease `pip install -e`
- [/include/pomagma](/include/pomagma) - a symbolic link to appease g++

## Testing <a name="testing"/>

Pomagma comes with three default levels of tests:

    make small-test     # runs on travis-ci
    make test
    make big-test       # more expensive with larger atlas

## Configuring <a name="configuring"/>

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
- Edit: write code; respond to static analysis of code
- Fit Language: fit grammar weights to corpus; propose new words
- Recover (after Fregean collapse): assess damage; pinpoint problem; rebuild

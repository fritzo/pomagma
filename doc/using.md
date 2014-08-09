# Using Pomagma

* [Configuring](#configuring)
* [Client API](#client)
* [File Organization](#files)
* [Dataflow Architecture](#dataflow)

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

## Client API <name="client"/>

See [test.py](/src/analyst/test.py) for example python usage.
See [test.js](/src/analyst/test.js) for example node.js usage.

## File Organization <a name="files"/>

- [/src](/src) - source code (C++, python, javascript)
- [/doc](/doc) - developer documentation
- [/data](/data) - generated data, mirroring an S3 bucket
- [/bootstrap](/bootstrap) - a small git-cached atlas for testing
- [/build](/build) - destination of C++ builds
- [/pomagma](/pomagma) - a symbolic link to appease `pip install -e`
- [/include/pomagma](/include/pomagma) - a symbolic link to appease g++

## Dataflow Architecture <a name="dataflow"/>

![Architecture](/doc/architecture.png)

### State

- Languages - finite generating grammars of combinatory algebras
- Theory - finite relational theories of combinatory algebras
- Atlas - an algebraic knowledge bases of relations in each algebra

### Actors

- Compiler - creates core theory and surveying strategies
- Surveyors - explore a region of a combinatory algebra via forward chaining
- Cartographers - direct surveyors and incorporate surveys into the atlas
- Linguist - fits languages to analyst workload and proposes new basic terms
- Language Reviewer - ensures new language modifications are safe
- Theorist - makes conjectures and tries to prove them using various strategies
- Theory Reviewer - suggests new inference stragies to address open conjectures
- Analyst - performs deeper static analysis to support clients

### Workflows

- Compile: interpret theory to create core facts and inference strategies
- Explore: expand atlas by surveying and inferring global facts
- Analyze: provide static analysis server to analyst clients
- Evolve Language: tune grammar weights based on analyst; propose new words
- Recover (after Fregean collapse): assess damage; pinpoint problem; rebuild

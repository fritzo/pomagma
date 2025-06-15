# Pomagma

[![Tests](https://github.com/fritzo/pomagma/actions/workflows/test.yml/badge.svg)](https://github.com/fritzo/pomagma/actions/workflows/test.yml)
[![PyPI Version](https://badge.fury.io/py/pomagma.svg)](https://pypi.python.org/pypi/pomagma)

Pomagma is an inference engine for
[extensional untyped &lambda;-join-calculus](/doc/philosophy.md),
a simple model of computation in which nondeterminism gives rise to
an elegant gradual type system.

Pomagma can:

- simplify code fragments expressed in &lambda;-join-calculus
- validate codebases of programs and assertions
- solve systems of inequalities and horn clauses
- synthesize code from sketches and inequality constraints

Pomagma's base theory has been partially verified in Coq
([hstar](https://github.com/fritzo/hstar)) and Z3
([hstar-z3](https://github.com/fritzo/hstar-z3)).

Pomagma's architecture follows a client-server model,
where a Python client library performs high-level syntactic tasks,
and a shared C++ database server performs low-level inference work.

- [Installing](#installing)
- [Quick Start](#quick-start)
- [Get An E-graph](#get-an-e-graph)
- [Using The Client Library](/doc/client.md)
- [Using the PyTorch front end](/src/torch/README.md)
- [Developing](/doc/README.md)
  - [Architecture](/doc/README.md#dataflow-architecture)
  - [Organization](/doc/README.md#file-organization)
  - [Configuring](/doc/README.md#configuring)
  - [Testing](/doc/README.md#testing)
  - [Benchmarking](/doc/README.md#benchmarking)
  - [Vetting changes](/doc/README.md#vetting-changes)
- [Philosophy](/doc/philosophy.md)

## Installing

The server targets Ubuntu 24.04, and installs in a uv virtual environment

    git clone https://github.com/fritzo/pomagma
    cd pomagma
    . install.sh
    make small-test     # takes ~5 CPU minutes
    make test           # takes ~1 CPU hour

The client library supports Python 3.12.

    pip install pomagma

## Quick Start

Start a local analysis server with the tiny pre-built E-graph

    pomagma analyze             # starts server, Ctrl-C to quit

Then in another terminal, start an interactive python client session

    $ pomagma connect           # starts a client session, Ctrl-D to quit
    >>> simplify(['APP I I'])
    [I]
    >>> validate(['I'])
    [{'is_bot': False, 'is_top': False}]
    >>> solve('x', 'EQUAL x APP x x', max_solutions=4)
    ['I', 'BOT', 'TOP', 'V']
    >>> validate_facts(['EQUAL x TOP', 'LESS x BOT'])
    False

Alternatively, connect using the Python client library

    python
    from pomagma import analyst
    with analyst.connect() as db:
        print(db.simplify(["APP I I"]))
        print(db.validate(["I"]))
        print(db.solve('x', 'EQUAL x APP x x', max_solutions=4))
        print(db.validate_facts(['EQUAL x TOP', 'LESS x BOT']))

## Get an E-graph

Pomagma reasons about large programs by approximately locating code fragments
in an **E-graph** of 10<sup>3</sup>-10<sup>5</sup> basic programs.
The more basic programs in an E-graph,
the more accurate pomagma's analysis will be.
Pomagma ships with a tiny pre-built E-graph of ~2000 basic programs.

To get a large pre-built E-graph, put your AWS credentials in the environment and

    export AWS_ACCESS_KEY_ID=...        # put your id here
    export AWS_SECRET_ACCESS_KEY=...    # put your hey here
    pomagma pull                        # downloads latest E-graph from S3

To start building a custom E-graph from scratch

    pomagma make max_size=10000         # kill and restart at any time

Pomagma is parallelized and needs lots of memory to build a large E-graph.

| E-graph Size      | Compute Time | Memory Space | Storage Space |
|-------------------|--------------|--------------|---------------|
| 1 000 E-classes   | ~1 CPU hour  | ~10MB        | ~1MB          |
| 10 000 E-classes  | ~1 CPU week  | ~1GB         | ~100MB        |
| 100 000 E-classes | ~1 CPU year  | ~100GB       | ~10GB         |

## License

Copyright (c) 2005-2025 Fritz Obermeyer.<br/>
Pomagma is licensed under the [Apache 2.0 License](/LICENSE).

Pomagma ships with the [Google Farmhash](https://github.com/google/farmhash)
library, licensed under the [MIT](/src/third_party/farmhash/COPYING) license.

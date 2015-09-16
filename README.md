[![Build Status](https://travis-ci.org/fritzo/pomagma.svg?branch=master)](https://travis-ci.org/fritzo/pomagma)
[![PyPI Version](https://badge.fury.io/py/pomagma.svg)](https://pypi.python.org/pypi/pomagma)

# Pomagma

Pomagma is an inference engine for
[extensional untyped &lambda;-calculus](/doc/philosophy.md).
Pomagma is useful for:

- simplifying code fragments expressed in pure &lambda;-join calculus
- validating entire codebases of &lambda;-terms and inequalities
- testing and validating systems of inequalities
- solving systems of inequalities

Pomagma follows a client-server database architecture
with a Python client library backed by a C++ database server.
The correctness of Pomagma's theory is being verified in the
[Hstar project](https://github.com/fritzo/hstar).

- [Installing](#installing)
- [Quick Start](#quick-start)
- [Get An Atlas](#get-an-atlas)
- [Using The Client Library](/doc/client.md)
- [Developing](/doc/README.md)
  - [Dataflow Architecture](/doc/README.md#dataflow)
  - [File Organization](/doc/README.md#files)
  - [Configuring](/doc/README.md#configuring)
  - [Testing](/doc/README.md#testing)
  - [Benchmarking](/doc/README.md#benchmarking)
  - [Vetting changes to generated code](/doc/README.md#vetting)
- [Philosophy](/doc/philosophy.md)

## Installing <a name="installing"/>

The server targets Ubuntu 14.04 and 12.04, and installs in a python virtualenv.

    git clone https://github.com/fritzo/pomagma
    cd pomagma
    . install.sh
    make small-test     # takes ~5 CPU minutes
    make test           # takes ~1 CPU hour

The client library supports Python 2.7.

    pip install pomagma

## Quick Start <a name="quick-start"/>

Start a local analysis server with the tiny default atlas

    pomagma analyze             # starts server, Ctrl-C to quit

Then in another terminal, start an interactive python client session

    $ pomagma connect           # starts a client session, Ctrl-D to quit
    >>> simplify(['APP I I'])
    [I]
    >>> validate(['I'])
    [{'is_bot': False, 'is_top': False}]
    >>> solve('x', 'EQUAL x APP x x', max_solutions=4)
    ['I', 'BOT', 'TOP', 'V'],

Alternatively, connect using the Python client library

    python
    from pomagma import analyst
    with analyst.connect() as db:
        print db.simplify(["APP I I"])
        print db.validate(["I"])
        print db.solve('x', 'EQUAL x APP x x', max_solutions=4)

## Get an Atlas to power an analysis server <a name="get-an-atlas"/>

Pomagma reasons about large programs by approximately locating code fragments
in an **atlas** of 10<sup>3</sup>-10<sup>5</sup> basic programs.
The more basic programs in an atlas,
the more accurate pomagma's analysis will be.
Pomagma ships with a tiny default atlas of ~2000 basic programs.

To get a large prebuilt atlas, put your AWS credentials in the environment and

    pomagma pull                  # downloads latest atlas from S3 bucket

To start building a custom atlas from scratch

    pomagma make max_size=10000   # kill and restart at any time

Pomagma is parallelized and needs lots of memory to build a large atlas.

| Atlas Size    | Compute Time | Memory Space | Storage Space |
|---------------|--------------|--------------|---------------|
| 1 000 atoms   | ~1 CPU hour  | ~10MB        | ~1MB          |
| 10 000 atoms  | ~1 CPU week  | ~1GB         | ~100MB        |
| 100 000 atoms | ~1 CPU year  | ~100GB       | ~10GB         |

## License <a name="license"/>

Copyright 2005-2015 Fritz Obermeyer.<br/>
All code is licensed under the [Apache 2.0 License](/LICENSE).

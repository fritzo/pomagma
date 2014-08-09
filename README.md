# Pomagma [![Build Status](https://travis-ci.org/fritzo/pomagma.svg?branch=master)](https://travis-ci.org/fritzo/pomagma) [![Code Quality](http://img.shields.io/scrutinizer/g/fritzo/pomagma.svg)](https://scrutinizer-ci.com/g/fritzo/pomagma) [![PyPI Version](https://pypip.in/version/pomagma/badge.svg)](https://pypi.python.org/pypi/pomagma) [![NPM Version](https://badge.fury.io/js/pomagma.svg)](https://badge.fury.io/js/pomagma)

Pomagma is an inference engine for
[extensional &lambda;-calculus](/doc/philosophy.md).
Pomagma's server provides code analysis services including:

* simplification of code fragments
* validation of entire codebases
* search / code completion / program refinement

Pomagma has client libraries in python and Node.js, and powers the
[Puddle](https://github.com/fritzo/puddle) reactive coding environment.

## Documentation

* [Philosophy](/doc/philosophy.md)
* [Using a client library](/doc/client.md)
* [Administering a server](/doc/server.md)

## Installing

The server targets Ubuntu 12.04 and 14.04.

    git clone https://github.com/fritzo/pomagma
    cd pomagma
    . install.sh
    make && make test

Client libraries support Python 2.7 and Node.js.

    pip install pomagma
    npm install pomagma

## Quick Start

Start a local analysis server with the tiny default atlas

    python -m pomagma analyze       # starts server, Ctrl-C to quit

Query the server using the python client

    python
    from pomagma import analyst
    with analyst.connect() as db:
        print db.simplify(["APP I I"])      # prints [I]
        print db.validate(["I"])            # prints [{"is_bot": False, "is_top": False}]

or the Node.js client

    nodejs
    var analyst = require("pomagma").analyst;
    var db = analyst.connect();
    console.log(db.simplify(["APP I I"]));  // prints [I]
    console.log(db.validate(["I"]));        // prints [{"is_bot": false, "is_top": false}]
    db.close();

## Building a larger atlas to power deeper analysis

Pomagma reasons about large programs by comparing code fragments
to an atlas of 10<sup>3</sup>-10<sup>5</sup> basic programs.
The tiny default atlas starts with ~2000 basic programs.

Start building a bigger atlas

    python -m pomagma make max_size=10000   # kill and restart at any time

Pomagma is parallelized and needs lots of memory to build a large atlas.

| Atlas Size    | Compute Time | Memory Space | Storage Space        |
|---------------|--------------|--------------|----------------------|
| 1 000 atoms   | ~1 CPU hour  | ~10MB        | ~1MB uncompressed    |
| 10 000 atoms  | ~1 CPU week  | ~1GB         | ~100MB uncompressed  |
| 100 000 atoms | ~5 CPU years | ~50GB        | ~10GB uncompressed   |

## License

Copyright 2005-2014 Fritz Obermeyer.<br/>
All code is licensed under the [MIT license](/LICENSE) unless otherwise noted.

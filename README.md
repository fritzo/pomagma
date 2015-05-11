[![Build Status](https://travis-ci.org/fritzo/pomagma.svg?branch=master)](https://travis-ci.org/fritzo/pomagma)
[![Code Quality](https://scrutinizer-ci.com/g/fritzo/pomagma/badges/quality-score.png?b=master)](https://scrutinizer-ci.com/g/fritzo/pomagma)
[![PyPI Version](https://badge.fury.io/py/pomagma.svg)](https://pypi.python.org/pypi/pomagma)
[![NPM Version](https://badge.fury.io/js/pomagma.svg)](https://badge.fury.io/js/pomagma)
[![NPM Dependencies](https://david-dm.org/fritzo/pomagma.svg)](https://www.npmjs.org/package/pomagma)

# Pomagma

Pomagma is an inference engine for
[extensional untyped &lambda;-calculus](/doc/philosophy.md).
Pomagma is useful for:

* simplifying code fragments expressed in pure &lambda;-join calculus
* validating entire codebases of &lambda;-terms and inequalities
* testing and validating systems of inequalities
* solving systems of inequalities

Pomagma has client libraries in python and node.js, and powers the
[Puddle](https://github.com/fritzo/puddle) reactive coding environment.
The correctness of Pomagma's theory is being verified in the
[Hstar project](https://github.com/fritzo/hstar).

## Documentation

* [Philosophy](/doc/philosophy.md)
* [Using a client library](/doc/client.md)
* [Administering a server](/doc/server.md)

## Installing

The server targets Ubuntu 12.04 and 14.04, and installs in a python virtualenv.

    git clone https://github.com/fritzo/pomagma
    cd pomagma
    . install.sh
    make small-test     # takes ~5 CPU minutes
    make test           # takes ~1 CPU hour

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

## Build an Atlas to power an analysis server

Pomagma reasons about large programs by approximately locating code fragments
in an **atlas** of 10<sup>3</sup>-10<sup>5</sup> basic programs.
The more basic programs in an atlas,
the more accurate pomagma's analysis will be.
Pomagma ships with a tiny default atlas of ~2000 basic programs.

Start building a bigger atlas

    python -m pomagma make max_size=10000   # kill and restart at any time

Pomagma is parallelized and needs lots of memory to build a large atlas.

| Atlas Size    | Compute Time | Memory Space | Storage Space        |
|---------------|--------------|--------------|----------------------|
| 1 000 atoms   | ~1 CPU hour  | ~10MB        | ~1MB uncompressed    |
| 10 000 atoms  | ~1 CPU week  | ~1GB         | ~100MB uncompressed  |
| 100 000 atoms | ~5 CPU years | ~100GB       | ~10GB uncompressed   |

## License

Copyright 2005-2015 Fritz Obermeyer.<br/>
All code is licensed under the [MIT license](/LICENSE) unless otherwise noted.

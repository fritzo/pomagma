# Pomagma [![Build Status](https://travis-ci.org/fritzo/pomagma.svg?branch=master)](https://travis-ci.org/fritzo/pomagma)

Pomagma is an inference engine for
[extensional programming](/doc/philosophy.md).
Pomagma's server provides code analysis services including:

* simplification of code fragments
* validation of entire codebases
* code completion / program refinement

Pomagma has client libraries in python and node.js, and powers the
[Puddle](https://github.com/fritzo/puddle) reactive coding environment.

## Documentation

* [Philosophy](/doc/philosophy.md)
* [Using Pomagma](/doc/using.md)

## Installing

The Pomagma server targets Ubuntu 12.04 and 14.04.

    git clone https://github.com/fritzo/pomagma
    cd pomagma
    . install.sh
    make && make test

## Using an analysis server

Start an analysis server with the tiny default atlas

    python -m pomagma analyze       # starts server, Ctrl-C to quit

Then connect with the python client library

    python
    from pomagma import analyst
    with analyst.connect() as db:
        print db.simplify(["APP I I"])      # prints [I]
        print db.validate(["I"])            # prints [{"is_bot": False, "is_top": False}]

Or connect with the nodejs client library

    nodejs
    var analyst = require("pomagma").analyst;
    var db = analyst.connect();
    console.log(db.simplify(["APP I I"]));  # prints [I]
    console.log(db.validate(["I"]));        # prints [{"is_bot": false, "is_top": false}]
    db.close();

## Building a larger atlas to power deeper analysis

Pomagma reasons about large programs by comparing code fragments to an atlas of
10<sup>3</sup>-10<sup>5</sup> basic programs.
The tiny default atlas starts with ~2000 basic programs.

Start building a bigger atlas

    python -m pomagma init      # builds a minimal atlas (a few minutes)
    python -m pomagma explore   # continuously expands (from hours to months)

Kill and restart at any time.
Build a big atlas on a big machine.

| Atlas Size    | Compute Time | Memory Space | Storage Space        |
|---------------|--------------|--------------|----------------------|
| 1 000 atoms   | ~10 minutes  | ~10MB        | ~1MB uncompressed    |
| 10 000 atoms  | ~10 hours    | ~1GB         | ~100MB uncompressed  |
| 100 000 atoms | months       | ~50GB        | ~10GB uncompressed   |

## Using with Puddle front-end

The canonical editor front-end for Oomagma is
[Puddle](https://github.com:fritzo/puddle),
a node.js+browser system that connects to `POMAGMA_ANALYST_ADDRESS`.

## License

Copyright 2005-2014 Fritz Obermeyer.<br/>
All code is licensed under the [MIT license](/LICENSE) unless otherwise noted.

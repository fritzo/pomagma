# Pomagma

An Extensional Development Environment.

Pomagma is an environment for developing computational behaviors.
Computational behaviors can be though of
either as mathematical properties of programs (ignoring runtime complexity)
or as computationally-founded mathematical objects.

Pomagma uses the simplest model of computation,
combinatory algebra (a <b>p</b>artially <b>o</b>rdered <b>magma</b>),
and reasons with an elegantly simple semantic theory
that is strong enough to serve as a foundation for mathematics.

Pomagma began as a PhD [thesis](http://fritzo.org/thesis.pdf) and
[codebase](http://github.com/fritzo/Johann).

## Organization

- [/src](src) - source code (C++, python, javascript)
- [/doc](doc) - developer documentation
- [/data](data) - generated data, mirroring an S3 bucket
- [/build](build) - destination of C++ builds
- [/pomagma](pomagma) - a symbolic link to appease `pip install -e`

## Installing

The Pomagma back end currently targets Ubuntu 12.04 LTS.
To install:

    git clone git@github.com:fritzo/pomagma
    cd pomagma
    ./install.sh    # If mkvirtualenv fails, run manually.  FIXME
    make unit-test  # takes ~2 minutes
    make test       # takes ~30 minutes

## Configuring

To run a full system, pomagma needs Amazon AWS credentials, an S3 bucket,
an SWF domain, and optionally an email address to receive errors.
These are specified by environment variables
 
    AWS_ACCESS_KEY_ID=...
    AWS_SECRET_ACCESS_KEY=...
    POMAGMA_BUCKET=Example-Amazon-S3-bucket
    POMAGMA_DOMAIN=Example-Amazon-SWF-domain
    POMAGMA_EMAIL=example.user@example.com

To run in debug mode, define an environment variable

    POMAGMA_DEBUG=

## License

Copyright 2005-2013 Fritz Obermeyer.<br/>
All code is licensed under the MIT license unless otherwise noted.

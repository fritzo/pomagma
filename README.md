Pomagma
=======

Adventures in Abstractland.

Pomagma is a toy model of human exploration of the abstract universe,
of mathematics as a scientific research program a la Imre Lakatos.
Some of the roles we play as mathematicians are captured as algorithms
performed by software actors in a [system](src/README.md),
while some less well-defined roles are performed by human actors.
The most important, most open-ended, most creative role of all is Adventuring,
and Pomagma aims to make abstract adventuring easy, fun, and safe.

Organization
------------

- [/src](src) - source code: python, C++
- [/pomagma](pomagma) - a symbolic link to appease `pip install -e`
- [/doc](doc) - just figures; see `/src/*` for code documentation
- [/build](build) - destination of C++ builds
- [/data](data) - generated data, mirroring S3 bucket

Installing Full System
----------------------

Pomagma is targeted for Ubuntu 12.04 LTS.
To install:

    git clone git@github.com:fritzo/pomagma
    cd pomagma
    ./install.sh    # If mkvirtualenv fails, run manually.  FIXME
    make unit-test  # takes ~2 minutes
    make test       # takes ~30 minutes

Environment Variables
---------------------

To run a full system, pomagma needs Amazon AWS credentials,
an S3 bucket, an SWF domain, an optionally, an email address to receive errors.
 
    AWS_ACCESS_KEY_ID=XXXXXXXXXXXXXXXXXXXX
    AWS_SECRET_ACCESS_KEY=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
    POMAGMA_BUCKET=Example-Amazon-S3-bucket
    POMAGMA_DOMAIN=Example-Amazon-SWF-domain
    POMAGMA_SPAMEE=example.user@bogus.net

To run actors in debug mode, define an environment variable

    POMAGMA_DEBUG=

License
-------

Copyright (c) 205-2013, Fritz Obermeyer <br/>
Dual licensed under the MIT or GPL Version 2 licenses. <br/>
http://www.opensource.org/licenses/MIT <br/>
http://www.opensource.org/licenses/GPL-2.0

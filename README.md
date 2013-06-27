# Pomagma

An Extensional Development Environment.

Pomagma is an environment for programming behaviors,
or programs modulo observable equivalence.
Pomagma is founded in the simplest model of computation,
combinatory algebra (a <b>p</b>artially <b>o</b>rdered <b>magma</b>),
and reasons with a napkin-sized semantic theory
that is yet strong enough to serve as a foundation for mathematics.

Pomagma began as a PhD [thesis](http://fritzo.org/thesis.pdf) and
[codebase](http://github.com/fritzo/Johann).

## System Architecture

![Architecture](doc/architecture.png)

### State

- Languages - finite generating grammars of combinatory algebras
- Theory - finite relational theories of combinatory algebras
- Atlas - an algebraic knowledge bases of relations in each algebra
- Corpus - collected writings compilable to combinatory algebra expressions

### Actors

- Compiler - creates core theory and surveying strategies
- Surveyors - explore a region of a combinatory algebra via forward chaining
- Cartographers - direct surveyors and incorporate surveys into the atlas
- Linguist - fits languages to the corpus and proposes new basic terms
- Language Reviewer - ensures new language modifications are safe
- Theorist - makes conjectures and tries to prove them using various strategies
- Theory Reviewer - suggests new inference stragies to address open conjectures
- Editor - provides user interface for editing algebraic code
- Analyst - performs deeper static analysis to support editor

### Workflows

- Compile: interpret theory to create core facts and inference strategies
- Survey: select a region; explore nearby regions; add observations to atlas
- Theorize: make conjectures; prove some, ponder others; add theorems to atlas
- Edit: write code; respond to static analysis of code
- Evolve Language: optimize grammar weights based on corpus; propose new words
- Recover (after Fregean collapse): assess damage; pinpoint problem; rebuild

## Milestones 

- Viable - prove concept in prototype DONE
- Parallel - run surveyor system tests (h4, sk, skj) DONE
- Scalable - run surveyor-cartographer loop DONE
- Thrifty - propose new equations based on atlas DONE
- Distributed - run survey workflow on ec2
- Literate - populate corpus by writing code in editor
- Tasteful - fit language parameters to corpus
- Innovative - propose new basic terms based on corpus
- Interactive - show static analysis layer in editor
- Reflective - model pomagma actors in corpus
- Social - integrate with other languages and environments

## Organization

- [/src](src) - source code: C++, python, javascript
- [/pomagma](pomagma) - a symbolic link to appease `pip install -e`
- [/doc](doc) - figures
- [/build](build) - destination of C++ builds
- [/data](data) - generated data, mirroring an S3 bucket

## Installing

Pomagma is targeted for Ubuntu 12.04 LTS.
To install:

    git clone git@github.com:fritzo/pomagma
    cd pomagma
    ./install.sh    # If mkvirtualenv fails, run manually.  FIXME
    make unit-test  # takes ~2 minutes
    make test       # takes ~30 minutes

## Environment Variables

To run a full system, pomagma needs Amazon AWS credentials, an S3 bucket,
an SWF domain, and optionally an email address to receive errors.
 
    AWS_ACCESS_KEY_ID=...
    AWS_SECRET_ACCESS_KEY=...
    POMAGMA_BUCKET=Example-Amazon-S3-bucket
    POMAGMA_DOMAIN=Example-Amazon-SWF-domain
    POMAGMA_EMAIL=example.user@example.com

To run actors in debug mode, define an environment variable

    POMAGMA_DEBUG=

## License

Copyright (c) 2005-2013, Fritz Obermeyer <br/>
Licensed under the MIT license.

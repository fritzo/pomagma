# Pomagma

An integrated development environment for formal mathematics.

## System Architecture

![Architecture](doc/architecture.png)

### State

- Languages - finite generating grammars of combinatory algebras
- Theories - finite relational theories of combinatory algebras
- Atlas - an algebraic knowledge bases of relations in each algebra
- Corpus - collected writings compilable to combinatory algebra expressions

### Actors

- Compiler - creates core theory and surveying strategies
- Surveyors - explore a region of a combinatory algebra
- Cartographers - direct surveyors and incorporate surveys into the atlas
- Linguist - fits language to corpus and proposes new terms
- Language Reviewer - ensure new language modifications are safe
- Theorist - propose new routes between common destinations
- Theory Reviewer - evaluates transportation bills
- Editor - user interface for editing algebraic code
- Analyst - server-side static analyzer for algebraic code

### Workflows

- Compile: interpret theory to create core facts and surveying strategies
- Survey: select a region; survey it; aggregate measurements into atlas
- Edit: write code; respond to static analysis of code
- Learn Language: optimize language weights based on corpus
- Make Language: propose new terms to add to the language; review for safety
- Conjecture: propose new equations; evaluate economic effects; commit
- Recover (after Fregean collapse): assess damage; pinpoint problem; rebuild

## Milestones

The vision for pomagma extends beyond its present codebase.

- Viable - prove concept in prototype [DONE](http://github.com/fritzo/Johann)
- Parallel - run surveyor system tests (h4, sk, skj) DONE
- Scalable - run surveyor-cartographer loop DONE
- Economical - propose new equations based on atlas DONE
- Literate - populate corpus by writing code in editor
- Efficient - fit language parameters to corpus
- Innovative - propose new basic terms based on corpus
- Interactive - show static analysis layer in editor
- Reflective - model pomagma actors in corpus
- Distributed - run survey workflow on ec2

## Organization

- [/src](src) - source code: python, C++
- [/pomagma](pomagma) - a symbolic link to appease `pip install -e`
- [/doc](doc) - figures
- [/build](build) - destination of C++ builds
- [/data](data) - generated data, mirroring S3 bucket

## Installing Full System

Pomagma is targeted for Ubuntu 12.04 LTS.
To install:

    git clone git@github.com:fritzo/pomagma
    cd pomagma
    ./install.sh    # If mkvirtualenv fails, run manually.  FIXME
    make unit-test  # takes ~2 minutes
    make test       # takes ~30 minutes

## Environment Variables

To run a full system, pomagma needs Amazon AWS credentials, an S3 bucket,
an SWF domain, an optionally an email address to receive errors.
 
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

#!/bin/sh

# Set up a new machine from a fresh Ubuntu 12.04 LTS image
sudo apt-get update
sudo apt-get install -y git-core
git clone git@github.com:fritzo/pomagma
cd pomagma
./requirements.sh


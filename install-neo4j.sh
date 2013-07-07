#!/bin/sh

sudo -s

# Install oracle java 7
# from https://github.com/flexiondotorg/oab-java6
cd ~/
wget https://github.com/flexiondotorg/oab-java6/raw/0.2.8/oab-java.sh -O oab-java.sh
chmod +x oab-java.sh
./oab-java.sh -7

# Give neo4j permissions to load more files
# recommended by http://stackoverflow.com/questions/15519891
echo 'neo4j   soft    nofile  40000' >> /etc/security/limits.conf 
echo 'neo4j   hard    nofile  40000' >> /etc/security/limits.conf 

# Install neo4j
# from http://www.neo4j.org/download/linux
wget -O - http://debian.neo4j.org/neotechnology.gpg.key | apt-key add - 
echo 'deb http://debian.neo4j.org/repo stable/' > /etc/apt/sources.list.d/neo4j.list
apt-get update
apt-get install neo4j
service neo4j-service start


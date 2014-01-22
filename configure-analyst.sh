#!/bin/sh

PORT=34936
MASTER=$(getent ahosts pomagma.org | grep -o '\<[0-9.]*\>' | head -n 1)
echo restricting port $PORT to $MASTER

# see http://serverfault.com/questions/30026
# see http://nixcraft.com/showthread.php/479-Blocking-ports-in-linux

# Flush existing rules
iptables -F INPUT
# Set up default
iptables -P INPUT DROP
# Allow existing connections to continue
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
# Allow ssh from anywhere
iptables -A INPUT -p tcp --dport 22 -j ACCEPT
# Allow analyst connections from MASTER
iptables -A INPUT -p tcp --dport $PORT -s $MASTER -j ACCEPT
# Allow analyst connections from from the 192.168.0.x network
iptables -A INPUT -p tcp --dport $PORT -s 192.168.0.0/24 -j ACCEPT

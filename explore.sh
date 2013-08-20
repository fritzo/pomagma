#!/bin/bash

. ~/.bashrc
ulimit -c unlimited
cd ~/pomagma/data
tmux new-session -d -s pomagma 'python -m pomagma.batch explore skj'
tmux split-window -d 'tail -f atlas/skj/survey.log'
tmux split-window -d 'tail -f atlas/skj/infer.log'
tmux select-layout even-vertical

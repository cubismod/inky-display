#!/bin/bash
TASK_BIN=$HOME/.local/bin/task

pushd "$HOME/git/inky-display/"
source ./venv/bin/activate
$TASK_BIN run
popd

#!/bin/bash
pushd "$HOME/git/inky-display/"
source ./venv/bin/activate
task run
popd

#!/bin/bash
# Opens virtual environment, so as to refer to the right packages.
source ./venv/bin/activate
pip freeze | grep -v "pkg-resources" |
grep -v "protobuf-to-dict" > requirements.txt
# Adds the protobuf line.
echo "git+https://git@github.com/wearefair/protobuf-to-dict" >> \
    requirements.txt

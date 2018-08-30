#!/bin/bash
# If this is run using source rather than the usual, the original shell will
# go into the virtual environment.
source ./venv/bin/activate
pip install -r requirements.txt
export FLASK_APP=app.py
export FLASK_DEBUG=1
python -m flask run

#!/bin/bash

export PYTHONPATH="$(pwd)/src"
python ui/app.py


source venv/bin/activate
python app.py

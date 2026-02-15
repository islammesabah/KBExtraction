#!/bin/bash

# Because kbdebugger lives here:
# /home/abuali/projects/KBExtraction/src/kbdebugger
# We want Python to see:
# /home/abuali/projects/KBExtraction/src
export PYTHONPATH="$(pwd)/src"
# python ui/app.py
python -m ui.app

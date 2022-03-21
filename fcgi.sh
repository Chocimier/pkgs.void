#!/bin/sh
[ -d venv ] && . venv/bin/activate
./serve.py flup_socket

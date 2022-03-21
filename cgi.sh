#!/bin/sh
[ -d venv ] && . venv/bin/activate
python serve.py cgi

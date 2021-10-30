#!/bin/sh
python -m celery -A workers.buildlog.buildlog -b "$(./settings.py BROKER buildlog)" worker -P solo "$@"

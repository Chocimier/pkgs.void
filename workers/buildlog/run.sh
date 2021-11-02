#!/bin/sh
mkdir -p data/logs
python -m celery -A workers.buildlog.buildlog -b "$(./settings.py BROKER buildlog)" worker -P solo -B -f data/logs/worker-buildlog.log "$@"

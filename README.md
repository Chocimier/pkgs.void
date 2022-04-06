Web catalog of Void Linux packages.

# Visiting

[http://54.37.137.89/pkgs.void](http://54.37.137.89/pkgs.void)


# Running

See also [Running with docker](#running-with-docker).

1. Clone and enter repo: `git clone https://github.com/Chocimier/pkgs.void && cd pkgs.void`
2. Create and activate Python 3 virtualenv:
 `python3 -m virtualenv -p python3 venv && . venv/bin/activate`
3. Install dependencies: `pip install -r requirements.txt`
 Used non-python tools are git, rsync, xbps, xtools and wget.
4. Clone https://github.com/void-linux/void-packages .
5. Generate database: `./update.sh`. This step publish whole directory on your
 instance of catalog, accordingly to AGPL license.
 This modifies void-packages clone. Either make sure that xdistdir will find
 clone of void-packages, or disable repo parsing with `-T` flag.
6. Run: `./serve.py`

There is a CGI script `cgi.sh` and FCGI script: `fcgi.sh`.

## Configuration:

Settings in `config.ini`, if any, overrride setttings in `configs/defaults.ini`

## Buildlog worker

Optional worker collecting build logs info from official Void builder
requires a queue server. By default it's redis, but can be configured
to other supported by Celery.

## Running with docker

1. Run `docker-compose up`.

This starts webserver listening on port 7547, two instances of webapp,
cron for updating database, buildlog worker and a queue server.
Containers communicate through shared voulems, so need to be run on
same host.

Configuration of webserver is loaded from volume mounted from
`misc/docker/volumes/webserver-cfg`. It specifies count of webapp
instances and logging level.

Container that updates database builds minimal database on every
startup within 3 minutes, then full database two times an hour. Webapp
fails before first database is created.

# Developing
Lint hooks are installed by symlinking `.git/hooks` to `git_hooks`.
They use tools specified in `requirements-dev.txt`.
Pylint takes few seconds on commit to scan code.
Profiling script use graphviz.

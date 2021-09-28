Web catalog of Void Linux packages.

# Visiting

[http://54.37.137.89/pkgs.void](http://54.37.137.89/pkgs.void)


# Running

1. Clone and enter repo: `git clone https://github.com/Chocimier/pkgs.void && cd pkgs.void`
2. Create and activate Python 3 virtualenv:
 `python3 -m virtualenv -p python3 venv && . venv/bin/activate`
3. Install dependencies: `pip install -r requirements.txt`
 From non-python tools, rsync, xtools and wget is needed.
 Graphviz is used by profiling script.
4. Clone https://github.com/void-linux/void-packages .
5. Generate database: `./update.sh`. This step publish whole directory on your
 instance of catalog, accordingly to AGPL license.
 This modifies void-packages clone. Either make sure that xdistdir will find
 clone of void-packages, or disable repo parsing with `-T` flag.
6. Run: `./serve.py`

There is a CGI script `cgi.sh` and FCGI script: `fcgi.sh`.

# Configuration:

Settings in `config.ini`, if any, overrride setttings in `configs/defaults.ini`

Web catalog of Void Linux packages.

# Visiting

[http://54.37.137.89/pkgs.void](http://54.37.137.89/pkgs.void)


# Running

1. Clone and enter repo: `git clone https://github.com/Chocimier/pkgs.void && cd pkgs.void`
2. Create and activate Python 3 virtualenv:
 `python3 -m virtualenv -p python3 venv && . venv/bin/activate`
3. Install dependencies: `pip install -r requirements.txt`
 From non-python tools, rsync and wget is needed.
 Graphviz is used by profiling script.
4. Generate database: `./update.sh`. This step publish whole directory on your
 instance of catalog, accordingly to AGPL license.
5. Run: `./serve.py`

There is a CGI script `cgi.sh` and FCGI script: `fcgi.sh`.

from yanko.cli import cli
from yanko import start
from sys import argv

if len(argv) > 1:
    cli()
else:
    start()

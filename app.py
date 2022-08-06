from yanko.cli import cli
from sys import argv

if len(argv) > 1:
    cli()
else:
    from yanko import start
    start()

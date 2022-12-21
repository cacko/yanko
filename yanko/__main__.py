from sys import argv
import os
from subprocess import run


if len(argv) > 1:
    from yanko.cli import cli

    cli()
else:
    from yanko import start

    run(["sudo", "renice", "-20", f"{os.getpid()}"])
    start()

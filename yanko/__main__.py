from sys import argv
import os
from subprocess import run


if len(argv) > 1:
    from yanko.cli import cli

    cli()
else:
    from yanko import start

    run(["sudo", "renice", "-10", f"{os.getpid()}"])
    start()

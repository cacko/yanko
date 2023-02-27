import logging
from sys import argv, exit
import os
from yanko.core import pid_file, check_pid

if len(argv) > 1:
    from yanko.cli import cli
    cli()
else:
    from yanko import start
    if check_pid():
        logging.warning("App already running")
        exit(1)
    else:
        pid_file.write_text(f"{os.getpid()}")
        start()

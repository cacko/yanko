import logging
from sys import argv, exit
import os

logging.info({k: v for k, v in os.environ.items()})


from yanko.core import pid_file, check_pid, show_alert
from subprocess import run

if len(argv) > 1:
    from yanko.cli import cli
    run(["sudo", "renice", "15", f"{os.getpid()}"])
    cli()
else:
    from yanko import start
    if check_pid():
        show_alert("Yanko already running.")
        exit(1)
    else:
        pid_file.write_text(f"{os.getpid()}")
        start()

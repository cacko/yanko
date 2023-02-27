from sys import argv, exit
import os
from yanko.core import pid_file, check_pid, show_alert


if len(argv) > 1:
    from yanko.cli import cli
    cli()
else:
    from yanko import start
    if check_pid():
        show_alert("Yanko already running.")
        exit(1)
    else:
        pid_file.write_text(f"{os.getpid()}")
        start()

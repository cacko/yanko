# nuitka-project: --macos-create-app-bundle
# nuitka-project: --macos-app-name=Yanko
# nuitka-project: --macos-app-mode=ui-element
# nuitka-project: --product-name=Yanko
# nuitka-project: --macos-signed-app-name=net.cacko.yanko
# nuitka-project: --macos-sign-identity=4751CAA3DF53B17285571167EBD6261C5DF9E022
# nuitka-project: --file-description=Yanko
# nuitka-project: --include-data-files={MAIN_DIRECTORY}/icon.png=data/icon.png
# nuitka-project: --include-data-dir={MAIN_DIRECTORY}/yanko/resources=data/resources/
# nuitka-project: --macos-app-icon={MAIN_DIRECTORY}/icon.png
# nuitka-project: --file-version="1.2.0"
# nuitka-project: --product-version="1.2.0"
# nuitka-project: --macos-app-version="1.2.0"
# nuitka-project: --python-flag=no_site 
# nuitka-project: --python-flag=no_warnings 
# nuitka-project: --static-libpython=yes 
# nuitka-project: --include-package=numba
# nuitka-project: --follow-stdlib

from sys import argv, exit
import os
from yanko.core import pid_file, check_pid, show_alert
from subprocess import run


if len(argv) > 1:
    from yanko.cli import cli
    run(["sudo", "renice", "15", f"{os.getpid()}"])
    cli()
else:
    from yanko import start
    from yanko.resources import bin_path
    pth = os.environ['PATH']
    os.environ['PATH'] = f"{bin_path.as_posix()}:{pth}"
    if check_pid():
        show_alert("Yanko already running.")
        exit(1)
    else:
        pid_file.write_text(f"{os.getpid()}")
        start()

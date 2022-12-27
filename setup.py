import sys
from pathlib import Path

import semver
from setuptools import setup

from yanko import __name__
from yanko.version import __version__


def resolve_libs(libs):
    env = Path(sys.executable)
    root = env.parent.parent / "lib"
    return [(root / f).as_posix() for f in libs]


def version():
    if len(sys.argv) > 1 and sys.argv[1] == "py2app":
        init = Path(__file__).parent / __name__.lower() / "version.py"
        _, v = init.read_text().split(" = ")
        cv = semver.VersionInfo.parse(v.strip('"'))
        nv = f"{cv.bump_patch()}"
        init.write_text(f'__version__ = "{nv}"')
        return nv
    from yanko.version import __version__

    return __version__


APP = ["app.py"]
DATA_FILES = []
OPTIONS = {
    "iconfile": "icon.icns",
    "argv_emulation": False,
    "emulate_shell_environment": True,
    "plist": {
        "LSUIElement": True,
        "CFBundleIdentifier": "net.cacko.yanko",
        "CFBundleVersion": f"{version()}",
        "LSEnvironment": dict(
            PATH="/opt/homebrew/bin:/opt/homebrew/sbin", YANKO_LOG_LEVEL="FATAL"
        ),
    },
    "packages": [
        "_sounddevice_data",
        "PIL",
        "cv2",
        "numpy",
        "sounddevice",
        "pycparser",
    ],
    "frameworks": resolve_libs(
        [
            "libffi.8.dylib",
            "libtcl8.6.dylib",
            "libtk8.6.dylib",
            "libssl.3.dylib",
            "libcrypto.3.dylib",
            "libsqlite3.dylib",
        ]
    ),
}
setup(
    app=APP,
    name=__name__,
    install_requires=[
        "rumps >= 5.14.23",
        "dataclasses_json >= 0.5.7",
        "requests >= 2.28.1",
        "tld >= 0.12.6",
        "Pillow >= 9.2.0",
        "appdir >= 0.2",
        "pyotp >= 2.6.0",
        "click >= 8.1.3",
        "pixelme>= 0.4.7",
        "opencv-python >= 4.6.0.66",
        "bs4 >= 0.0.1",
        "ffmpeg-python>=0.2.0",
        "numpy>=1.23.2",
        "sounddevice>=0.4.4",
        "cffi >= 1.15.1",
        "pycparser >= 2.21",
        "olefile >= 0.46",
        "pantomime >= 0.5.1",
        "pyfiglet>=0.7",
        "questionary>=1.10.0",
        "butilka>=0.1.18",
        "pyyaml>=6.0",
        "redis>=4.3.4",
        "hiredis>=2.0.0",
        "cachable == 0.3.34",
        "arrow>=1.2.2",
        "structlog>=22.1.0",
        "black>=22.8.0",
        "progressor>=1.0.14",
        "peewee>=3.15.2",
        "coretime==0.1.4",
        "corestring==0.1.2",
        "colorama==0.4.6",
    ],
    python_requires=">=3.10",
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app", "Pillow", "cffi", "pycparser"],
)

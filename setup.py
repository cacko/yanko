import sys
from pathlib import Path

import semver
from setuptools import setup
from yanko import __name__


def resolve_libs(libs):
    env = Path(sys.executable)
    root = env.parent.parent / "lib"
    return [(root / f).as_posix() for f in libs]


def version():
    if len(sys.argv) > 1 and sys.argv[1] == "py2app":
        init = Path(__file__).parent / __name__.lower() / "version.py"
        _, v = init.read_text().split("=")
        cv = semver.VersionInfo.parse(v.strip().strip('"'))
        nv = f"{cv.bump_patch()}"
        init.write_text(f'__version__ = "{nv}"')
        return nv
    from yanko.version import __version__

    return __version__


APP = ["app.py"]
DATA_FILES: list[tuple[str, list[str]]] = []
OPTIONS = {
    "iconfile": "icon.icns",
    "argv_emulation": False,
    "emulate_shell_environment": True,
    "plist": {
        "LSUIElement": True,
        "CFBundleIdentifier": "net.cacko.yanko",
        "CFBundleVersion": f"{version()}",
        "LSEnvironment": dict(
            PATH="@executable_path/../Frameworks:/usr/.local/bin:/opt/homebrew/bin:/opt/homebrew/sbin",
            YANKO_LOG_LEVEL="CRITICAL",
            LD_LIBRARY_PATH="@executable_path/../Frameworks:/Users/jago/.local/lib:$LD_LIBRARY_PATH",
        ),
    },
    "packages": ["_sounddevice_data","blis", "cymem", "PIL", "cv2", "uvicorn", "anyio", "pysqlite3"],
    "frameworks": resolve_libs(
        [
            "libffi.dylib",
            "libssl.dylib",
            "libcrypto.dylib",
            "libsqlite3.dylib",
            "libssl.3.dylib",
            "libcrypto.3.dylib",
        ]
    ),
    # ),
}
setup(
    app=APP,
    name=__name__,
    python_requires=">=3.11",
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    package_data={"yanko.resources": ["*"]},
)

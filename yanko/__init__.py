import logging
from os import environ
from yanko.core.cachable import Cachable
from yanko.ui.app import YankoApp
from yanko.core.config import app_config

logging.basicConfig(
    level=getattr(logging, environ.get("YANKO_LOG_LEVEL", "DEBUG")),
    format="%(filename)s %(message)s",
    datefmt="YANKO %H:%M:%S",
)


def start():
    cache_dir = app_config.app_dir / "cache"
    if not cache_dir.parent.exists():
        cache_dir.parent.mkdir(parents=True)
    Cachable.register(cache_dir.as_posix())
    try:
        app = YankoApp()
        threads = app.threads
        app.run()
    except KeyboardInterrupt:
        for th in threads:
            try:
                th.stop()
            except:
                pass

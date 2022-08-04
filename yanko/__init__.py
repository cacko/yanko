import logging
from os import environ
from cachable.cacheable import Cachable
from yanko.ui.app import YankoApp
from yanko.core.config import app_config

logging.basicConfig(
    filename="/tmp/yanko.log",
    level=getattr(logging, environ.get("YANKO_LOG_LEVEL", "INFO")),
    format="%(filename)s %(message)s",
    datefmt="YANKO %H:%M:%S",
)


def start():
    cache_dir = app_config.app_dir / "cache"
    if not cache_dir.parent.exists():
        cache_dir.parent.mkdir(parents=True)
    Cachable.register(app_config.get(
        "redis", {}).get("url"), cache_dir.as_posix())
    try:
        app = YankoApp()
        app.run()
    except:
        YankoApp.quit()
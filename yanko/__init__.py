__name__ = "Yanko"
import logging
from os import environ
from tkinter import N
from cachable.cacheable import Cachable
from yanko.db.base import YankoDb
from yanko.ui.app import YankoApp
from yanko.core.config import app_config
import sys
import signal
import logging
import colorlog

log_config = {
    "level": getattr(logging, environ.get("YANKO_LOG_LEVEL", "DEBUG")),
    "format": "%(filename)s:%(lineno)d %(message)s",
    "datefmt": "YANKO %H:%M:%S",
    "force": True
}
if __file__.startswith("/Applications/"):
    log_config['filename'] = '/tmp/yanko.log'

logging.basicConfig(**log_config)
handler = colorlog.StreamHandler()
handler.setFormatter(colorlog.ColoredFormatter(
	'%(log_color)s%(filename)s:%(lineno)d %(message)s'))

logging.root.addHandler(handler)


def start():
    cache_dir = app_config.cache_dir
    if not cache_dir.parent.exists():
        cache_dir.parent.mkdir(parents=True)
    Cachable.register(redis_url=app_config.get("redis", {}).get("url"),
                        storage_dir=cache_dir.as_posix())
    try:
        app = YankoApp()

        def handler_stop_signals(signum, frame):
            app.terminate()
            YankoDb.close()
            sys.exit(0)

        signal.signal(signal.SIGINT, handler_stop_signals)
        signal.signal(signal.SIGTERM, handler_stop_signals)
        app.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logging.exception(e)
    finally:
        app.terminate()

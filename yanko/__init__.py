__name__ = "yanko"

from yanko.core import logger
from cachable.cacheable import Cachable
from yanko.db.base import YankoDb
from yanko.ui.app import YankoApp
from yanko.core.config import app_config
import sys
import signal


def start():
    cache_dir = app_config.cache_dir
    if not cache_dir.parent.exists():
        cache_dir.parent.mkdir(parents=True)
    Cachable.register(
        redis_url=app_config.get("redis", {}).get("url"),
        storage_dir=cache_dir.as_posix(),
    )
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
        logger.exception(e)
    finally:
        app.terminate()

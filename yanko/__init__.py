__name__ = "Yanko"
import logging
from os import environ
from cachable.cacheable import Cachable
from yanko.db.base import YankoDb
from yanko.ui.app import YankoApp
from yanko.core.config import app_config
import sys
import signal
import logging
import structlog

formatter = structlog.stdlib.ProcessorFormatter(
    processors=[
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M.%S"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.dev.ConsoleRenderer(),
    ]
)
handler = logging.StreamHandler()
handler.setFormatter(formatter)

logging.basicConfig(
    level=getattr(logging, environ.get("YANKO_LOG_LEVEL", "DEBUG")), handlers=[handler]
)


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
        logging.exception(e)
    finally:
        app.terminate()

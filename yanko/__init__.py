__name__ = "Yanko"

from pathlib import Path
from cachable.storage.file import FileStorage
from yanko.db.base import YankoDb
from yanko.ui.app import YankoApp
from yanko.core.config import app_config
from yanko.sonic.coverart import CoverArtFile
import sys
import signal
import traceback
import structlog
import logging
import os


structlog.configure(
    processors=[
        # Prepare event dict for `ProcessorFormatter`.
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
)

formatter = structlog.stdlib.ProcessorFormatter(
    processors=[
        structlog.stdlib.ProcessorFormatter.remove_processors_meta,
        structlog.dev.ConsoleRenderer()
    ],
)

handler = logging.StreamHandler()
# Use OUR `ProcessorFormatter` to format all `logging` entries.
handler.setFormatter(formatter)
root_logger = logging.getLogger()
root_logger.addHandler(handler)
root_logger.setLevel(
    getattr(logging, os.environ.get("YANKO_LOG_LEVEL", "INFO"))
)

def start():
    cache_dir = app_config.cache_dir
    if not cache_dir.parent.exists():
        cache_dir.parent.mkdir(parents=True)
    CoverArtFile.register(storage=FileStorage.register(storage_path=cache_dir))
    try:
        app = YankoApp()

        def handler_stop_signals(signum, frame):
            app.terminate()
            YankoDb.close()
            sys.exit(0)

        signal.signal(signal.SIGINT, handler_stop_signals)
        signal.signal(signal.SIGTERM, handler_stop_signals)
        app.run()
        app.terminate()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        with Path("/tmp/yanko.log").open("a") as fp:
            fp.writelines(traceback.format_exc())
        logging.exception(e)

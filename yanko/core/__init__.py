import logging
import time
from contextlib import contextmanager
from os import environ

import structlog

logging.basicConfig(level=getattr(logging, environ.get("YANKO_LOG_LEVEL", "DEBUG")))


logger = structlog.wrap_logger(
    logger=logging.getLogger("yanko"),
      processors=[
        structlog.stdlib.filter_by_level,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="YANKO %m/%d|%H:%M.%S"),
        structlog.dev.ConsoleRenderer()
    ],  
)

@contextmanager
def perftime(name, silent=False):
    st = time.perf_counter()
    try:
        yield
    finally:
        if not silent:
            total = time.perf_counter() - st
            logger.debug(f"{name} -> {total}s")

def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]
import logging
import time
from contextlib import contextmanager
import os
from .config import app_config


log_level = os.environ.get("YANKO_LOG_LEVEL", "INFO")
pid_file = app_config.data_dir / "yanko.pid"


@contextmanager
def perftime(name, silent=False):
    st = time.perf_counter()
    try:
        yield
    finally:
        if not silent:
            total = time.perf_counter() - st
            logging.debug(f"{name} -> {total}s")


def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def check_pid():
    try:
        assert pid_file.exists()
        pid = pid_file.read_text()
        print(pid)
        assert pid
        os.kill(int(pid), 0)
        return True
    except (AssertionError, ValueError, OSError):
        return False

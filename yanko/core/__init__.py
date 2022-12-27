import logging
import time
from contextlib import contextmanager

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
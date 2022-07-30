import threading
from contextlib import contextmanager
from subprocess import Popen
from os import environ


@contextmanager
def process(params, ):
    env = dict(
        environ,
        PATH=f"{environ.get('HOME')}/.local/bin:/usr/bin:/usr/local/bin:{environ.get('PATH')}",
    )
    proc = Popen(params, env=env)
    try:
        yield proc
    finally:
        proc.terminate()


class StoppableThread(threading.Thread):
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""

    def __init__(self,  *args, **kwargs):
        kwargs['daemon'] = True
        super(StoppableThread, self).__init__(*args, **kwargs)
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

import logging
from queue import Queue
from traceback import print_exc
import requests
from requests import ConnectionError
from yanko.core.config import app_config
from yanko.core.thread import StoppableThread
from yanko.sonic import Track
from pathlib import Path
from base64 import b64encode


class AnnounceMeta(type):

    _instance = None

    def __call__(self, *args, **kwds):
        if not self._instance:
            self._instance = super().__call__(*args, **kwds)
        return self._instance

    def announce(cls, track: Track):
        if not cls().is_alive():
            cls().start()
        return cls().queue.put_nowait(track)

class Announce(StoppableThread, metaclass=AnnounceMeta):

    __to = []
    queue: Queue = None

    def __init__(self):
        self.queue = Queue()
        self.__to = [v for v in app_config.get("announce", {}).values()]
        super().__init__()

    def run(self):
        while not self.stopped():
            track = self.queue.get()
            self.post(track=track)
            self.queue.task_done()

    def post(self, track: Track):
        if not len(self.__to):
            return
        payload = track.to_dict()
        payload["coverArt"] = b64encode(
            Path(payload["coverArt"]).read_bytes()).decode()
        for url in self.__to:
            try:
                resp = requests.post(url, json=payload)
                logging.debug(resp.status_code)
            except ConnectionError as e:
                print_exc(e)

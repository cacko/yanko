from base64 import b64encode
from pathlib import Path
from queue import Queue

import requests
from requests import ConnectionError
import logging
from yanko.core.config import app_config
from yanko.core.thread import StoppableThread
from yanko.sonic import Track

class Payload(Track):
    pass

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
    queue: Queue

    def __init__(self):
        self.queue = Queue()
        self.__to = app_config.get("announce",[])
        super().__init__()

    def run(self):
        while not self.stopped():
            track = self.queue.get()
            self.post(track=track)
            self.queue.task_done()

    def post(self, track: Track):
        if not len(self.__to):
            return
        payload = track.dict()
        payload["coverArt"] = b64encode(
            Path(payload["coverArt"]).read_bytes()).decode()
        for url in self.__to:
            try:
                resp = requests.post(url, json=Payload(**payload).json())
                logging.debug(resp.status_code)
            except ConnectionError:
                logging.warn(f"Announer failer for {url}")

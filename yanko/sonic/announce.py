from base64 import b64encode
from pathlib import Path
from queue import Queue

import requests
from requests import ConnectionError
import logging
from yanko.core.config import app_config
from yanko.core.thread import StoppableThread
from yanko.sonic import Track
import json


class Payload(Track):

    @property
    def payload(self) -> dict:
        return self.model_dump(mode='json')


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

    queue: Queue

    def __init__(self):
        self.queue = Queue()
        self.__to = app_config.get("announce", [])
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
                logging.warning(payload)
                requests.put(url, json=Payload(**payload).payload)
            except ConnectionError:
                logging.warn(f"Announcer failer for {url}")

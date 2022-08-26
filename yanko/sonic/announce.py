import logging
from traceback import print_exc
import requests
from requests import ConnectionError
from yanko.core.config import app_config
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
        return cls().post(track)


class Announce(object, metaclass=AnnounceMeta):

    __to = []

    def __init__(self):
        self.__to = [v for v in app_config.get("announce", {}).values()]

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

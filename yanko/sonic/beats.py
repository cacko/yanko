import logging
from yanko.core.cachable import CachableFile
from yanko.core.string import string_hash
from yanko.znayko import Znayko
from yanko.core.thread import StoppableThread
import json

class Beats(CachableFile):

    __path: str = None

    def __init__(self, path) -> None:
        self.__path = path
        super().__init__()


    def tocache(self, res):
        self.storage_path.write_bytes(json.dumps(res).encode())
        return res

    def fromcache(self):
        if self.isCached:
            return json.loads(self.storage_path.read_bytes())
        return None

    @property
    def filename(self):
        return f"{string_hash(self.__path)}.json"

    def fetch(self):
        logging.debug(f"Fetching beats for {self.__path}")
        beats = Znayko.beats(self.__path)
        return beats

    @property
    def content(self) -> list[float]:
        self._init()
        return self._struct

    def _init(self):
        if self.isCached:
            self._struct = self.fromcache()
            return 
        resp = self.fetch()
        if resp:
            self._struct = resp
            self.tocache(self._struct)


class Fetcher(StoppableThread):

    __paths: list[str] = None

    def __init__(self, paths: list[str], *args, **kwargs):
        self.__paths = paths
        super().__init__(*args, **kwargs)

    def run(self):
        print("fetcher start")
        for path in self.__paths:
            beats = Beats(path=path)
            if not beats.isCached:
                beats.content
        print("fetcher end")

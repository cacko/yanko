import logging
from queue import Queue, Empty
from yanko.core.cachable import CachableFile
from yanko.core.string import string_hash
from yanko.znayko import Znayko
from yanko.core.thread import StoppableThread
from time import sleep
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

class FetcherMeta(type):

    __instance: 'Fetcher' = None
    __queue: Queue = None

    def __call__(cls, *args, **kwds):
        if not cls.__instance or not cls.__instance.is_alive():
            cls.__instance = type.__call__(cls, *args, **kwds)
        return cls.__instance

    @property
    def queue(cls):
        if not cls.__queue:
            cls.__queue = Queue()
        return cls.__queue

    def add(cls, paths: list[str]):
        for pth in paths:
            cls.queue.put_nowait(pth)
        instance = cls()
        if not instance.is_alive():
            instance.start(cls.queue)
        
     
class Fetcher(StoppableThread, metaclass=FetcherMeta):

    __queue: Queue = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def start(self, queue) -> None:
        self.__queue = queue
        return super().start()

    def run(self):
        while True:
            try:
                audio_path = self.__queue.get_nowait()
                beats = Beats(path=audio_path)
                if not beats.isCached:
                    beats.content
                self.__queue.task_done()
            except Empty:
                return
            finally:
                sleep(0.1)


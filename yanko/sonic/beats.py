import logging
from queue import Queue, Empty
from yanko.core.cachable import CachableDb
from yanko.znayko import Znayko
from yanko.core.thread import StoppableThread
from yanko.db.models.beets import Beats as BeatsModel
from time import sleep

class Beats(CachableDb):

    __path: str = None
    _struct: BeatsModel = None

    def __init__(self, path) -> None:
        self.__path = path
        super().__init__(model=BeatsModel, id_key="path", id_value=path)

    @property
    def beats(self) -> list[float]:
        self._init()
        return self._struct.beats

    def fetch(self):
        resp = self.__fetch()
        if resp:
            self._struct = self.tocache(resp)        

    def __fetch(self):
        logging.debug(f"Fetching beats for {self.__path}")
        beats = Znayko.beats(self.__path)
        return beats

    def _init(self):
        if self.isCached:
            self._struct = self.fromcache()
            logging.debug(f"In DB beats for {self.__path}")
            return 
        self.fetch()

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
        logging.warning(instance.is_alive())
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
                    beats.fetch()
                self.__queue.task_done()
            except Empty:
                return
            finally:
                sleep(0.1)


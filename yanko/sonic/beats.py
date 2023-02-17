from queue import Queue, Empty
from yanko.core.cachable import CachableDb
from yanko.znayko import Znayko
from yanko.core.thread import StoppableThread
from yanko.db.models import Beats as BeatsModel
from time import sleep
from multiprocessing.pool import ThreadPool
from typing import Optional
import logging


def resolveBeats(audio_path):
    beats = Beats(path=audio_path)
    if not beats.isCached:
        beats.fetch()
    return beats


class Beats(CachableDb):

    __path: str
    _struct: Optional[BeatsModel] = None

    def __init__(self, path) -> None:
        self.__path = path
        super().__init__(
            model=BeatsModel,
            id_key="path",
            id_value=path
        )

    @classmethod
    def store_beats(cls, data: dict):
        obj = cls(data.get("path"))
        obj.tocache(data)
        return ["OK", obj.path]

    @property
    def beats(self) -> list[float]:
        try:
            self._init()
            assert self._struct
            assert isinstance(self._struct.beats, list)
            return self._struct.beats
        except AssertionError:
            return []

    @property
    def path(self):
        self._init()
        return self._struct.path if self._struct else None

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

    __instance: Optional["Fetcher"] = None
    __queue: Optional[Queue] = None

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
        cls.queue.put_nowait(paths)
        instance = cls()
        logging.warning(instance.is_alive())
        if not instance.is_alive():
            instance.start(cls.queue)


class Fetcher(StoppableThread, metaclass=FetcherMeta):

    __queue: Optional[Queue] = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def start(self, queue) -> None:
        self.__queue = queue
        return super().start()

    def run(self):
        try:
            assert self.__queue
            while True:
                try:
                    audio_paths = self.__queue.get_nowait()
                    logging.debug(audio_paths)
                    with ThreadPool(2) as pool:
                        jobs = pool.map(resolveBeats, audio_paths)
                        for res in jobs:
                            logging.debug(f"BEATS Extracted for {res.path}")
                        pool.close()
                        pool.join()
                        self.__queue.task_done()
                except Empty:
                    return
                except Exception:
                    self.__queue.task_done()
                finally:
                    sleep(0.1)
        except AssertionError:
            return

from queue import Queue, Empty
from yanko.core.cachable import CachableDb
from yanko.core.config import app_config
from yanko.core.thread import StoppableThread
from yanko.db.models import Beats as BeatsModel
from yanko.player.bpm import Beats as BeatsExtractor, BeatsStruct
from time import sleep
from typing import Optional
import logging
from yanko.sonic import Command


class Beats(CachableDb):

    _struct: Optional[BeatsModel] = None

    def __init__(
        self,
        path,
        allow_extract: Optional[bool] = None,
        extractor: Optional[BeatsExtractor] = None
    ) -> None:
        self.__path = path.split("Music/")[-1]
        if allow_extract is None:
            allow_extract = app_config.get("beats", {}).get("extract", False)
        self.__allow_extract = allow_extract
        self.__extractor = extractor
        super().__init__(
            model=BeatsModel,  # type: ignore
            id_key="path",
            id_value=path
        )

    @classmethod
    def store_beats(cls, data: dict):
        obj = cls(path=data.get("path"))
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
    def fast_bpm(self) -> int:
        try:
            self._init()
            assert self._struct
            assert isinstance(self._struct.tempo, float)
            return int(self._struct.tempo)
        except AssertionError:
            return 120

    @property
    def model(self):
        try:
            self._init()
            assert self._struct
            return BeatsStruct(**self._struct.to_dict())
        except AssertionError:
            return None

    @property
    def path(self):
        self._init()
        return self._struct.path if self._struct else None

    def fetch(self):
        try:
            resp = self.__fetch()
            assert resp
            self._struct = self.tocache(resp)
        except AssertionError:
            pass

    def __fetch(self):
        if not self.__extractor:
            self.__extractor = BeatsExtractor(self.__path)
        result = None
        result = self.__extractor.fast_bpm().dict()
        result["path"] = self.__path
        if self.__allow_extract:
            logging.debug(f"Extracting beats for {self.__path}")
            result = self.__extractor.extract().dict()
            result["path"] = self.__path
        return result

    def extract(self) -> BeatsStruct:
        self._init()
        print(self._struct)
        if not self._struct or not self._struct.beats:
            self.fetch()
        assert self._struct
        data = self._struct.to_dict()
        return BeatsStruct(**data)

    def _init(self):
        if self.isCached:
            self._struct = self.fromcache()
            return
        self.fetch()


class FetcherMeta(type):

    __instance: Optional["Fetcher"] = None
    __queue: Optional[Queue] = None
    __manager_queue: Optional[Queue] = None
    __do_extract: bool = False

    def __call__(cls, *args, **kwds):
        if not cls.__instance or not cls.__instance.is_alive():
            cls.__instance = type.__call__(cls, *args, **kwds)
        return cls.__instance

    def register(cls, manager_queue: Queue, do_extract: bool = False):
        cls.__manager_queue = manager_queue
        cls.__do_extract = do_extract
        return cls()

    @property
    def do_extract(cls) -> bool:
        return cls.__do_extract

    @property
    def manager_queue(cls) -> Optional[Queue]:
        return cls.__manager_queue

    @property
    def queue(cls):
        if not cls.__queue:
            cls.__queue = Queue()
        return cls.__queue

    def add(cls, paths: list[str]):
        cls.queue.queue.clear()
        for p in paths:
            cls.queue.put_nowait(p)


class Fetcher(StoppableThread, metaclass=FetcherMeta):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

    def resolveBeats(
        self,
        extractor: BeatsExtractor,
        allow_extract: Optional[bool] = None
    ):
        beats = Beats(
            path=extractor.requested_path,
            extractor=extractor,
            allow_extract=allow_extract
        )
        return beats

    def run(self):
        while True:
            try:
                audio_path = Fetcher.queue.get_nowait()
                extractor = BeatsExtractor(path=audio_path)
                assert Fetcher.manager_queue
                beats = self.resolveBeats(extractor=extractor)
                Fetcher.manager_queue.put_nowait(
                    (
                        Command.PLAYER_RESPONSE,
                        BeatsStruct(
                            tempo=float(beats.fast_bpm),
                            beats=None,
                            path=audio_path
                        ),
                    )
                )
                if app_config.get("beats", {}).get("extract", False):
                    beats = self.resolveBeats(extractor=extractor)
                    Fetcher.manager_queue.put_nowait(
                        (
                            Command.PLAYER_RESPONSE,
                            beats.model,
                        )
                    )
                Fetcher.queue.task_done()
            except Empty:
                pass
            except AssertionError as e:
                logging.exception(e)
                Fetcher.queue.task_done()
            except Exception:
                Fetcher.queue.task_done()
            finally:
                sleep(0.1)

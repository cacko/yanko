from asyncio.log import logger
from time import sleep
from threading import Event

from yanko.core.thread import StoppableThread


class BPMMeta(type):

    __instance: 'BPM' = None
    __ui_event: Event = None

    def __call__(cls, *args, **kwds):
        if not cls.__instance or cls.__instance.stopped():
            cls.__instance = type.__call__(cls, cls.__ui_event, *args, **kwds)
        return cls.__instance

    def register(cls, ui_event: Event):
        cls.__ui_event = ui_event

    def on(cls, bpm: int):
        logger.debug(f"START BPM {bpm}")
        if not cls().stopped():
            cls().stop()
        cls().start(bpm)

    def off(cls):
        cls().stop()

class BPM(StoppableThread, metaclass=BPMMeta):

    __ui_event: Event = None
    running = False
    bpm = None

    def __init__(self, ui_event):
        self.__ui_event = ui_event
        super().__init__()

    def start(self, bpm) -> None:
        self.bpm = bpm
        return super().start()

    def run(self):
        while not self.stopped():
            self.__ui_event.set()
            sleep(60 / self.bpm)

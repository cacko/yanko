from asyncio.log import logger
from time import sleep
from tkinter.messagebox import NO


class BPMMeta(type):

    __instance: 'BPM' = None

    def __call__(cls, *args, **kwds):
        if not cls.__instance:
            cls.__instance = type.__call__(cls, *args, **kwds)
        return cls.__instance

    def register(cls, app_callback):
        cls(app_callback).wait()

    def start(cls, bpm: int):
        logger.debug(f"START BPM {bpm}")
        cls.__instance.bpm = bpm

    def stop(cls):
        cls.__instance.bpm = None


class BPM(object, metaclass=BPMMeta):

    __callback = None
    running = False
    bpm = None

    def __init__(self, app_callback):
        self.__callback = app_callback

    def wait(self):
        sl = 0.05
        while True:
            if self.bpm is not None:
                self.__callback()
                sl = 60 / self.bpm
            else:
                sl = 0.05
            sleep(sl)

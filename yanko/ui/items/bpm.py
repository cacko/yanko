from queue import Queue
from threading import Event
from time import sleep, time
from typing import Optional
from yanko.player.device import Device
import logging
from yanko.core.thread import StoppableThread
from yanko.sonic import NowPlaying
from yanko.ui.icons import AnimatedIcon, Symbol
from pydantic import BaseModel


PausingIcon = AnimatedIcon(icons=[Symbol.GRID1, Symbol.GRID4])

PlayingIcon = AnimatedIcon(icons=[Symbol.GRID2, Symbol.GRID3])


class BPMEvent(BaseModel):
    icon: str
    tempo: str
    beat_no: int
    time_elapsed: int
    expires: float

    @property
    def hasExpired(self) -> bool:
        return time() > self.expires


class BPM(StoppableThread):

    time_event: Event
    __ui_queue: Queue
    __now_playing: Optional[NowPlaying] = None
    __time_start: float = 0
    __time_paused: float = 0
    __time_current: float = 0
    __time_total: float = 0
    __bpm: int = 0
    __beats: Optional[list[float]] = None
    __last_measure: float = 0
    __beat_count: int = 0

    def __init__(self, ui_queue: Queue, *args, **kwargs):
        self.time_event = Event()
        self.__ui_queue = ui_queue
        super().__init__(*args, **kwargs)

    @property
    def now_playing(self) -> Optional[NowPlaying]:
        return self.__now_playing

    @now_playing.setter
    def now_playing(self, np: NowPlaying):
        self.__now_playing = np
        self.__time_start = 0
        self.__time_current = 0
        self.__time_paused = 0
        self.__time_total = np.track.duration
        self.__last_measure = 0
        self.__bpm = np.bpm
        self.__beats = np.extracted_beats
        self.__beat_count = 1
        if self.__beats:
            total_beats = len(self.__beats)
            beats_bmp = total_beats / (self.__time_total / 60)
            np.setBpm(int(beats_bmp))
        else:
            self.__beats = self.get_static_beats()

    def get_static_beats(self):
        bps = self.__bpm / 60
        return [round(x / bps, 2) for x in range(0, int(self.__time_total * bps))]

    def run(self):
        while not self.stopped():
            try:
                if not self.__beats:
                    sleep(0.5)
                elif not self.time_event.is_set():
                    if self.__time_start is not None:
                        if self.__last_measure:
                            self.__time_paused += time() - self.__last_measure
                        if round(self.__time_paused) in self.__beats:
                            self.__addToQueue(icon=next(PausingIcon).value)
                        self.__last_measure = time()
                else:
                    if not self.__time_start:
                        self.__time_start = time() + Device.latency
                    self.__time_current = (
                        time() - self.__time_start - self.__time_paused
                    )
                    self.__last_measure = None
                    if self.__time_total < self.__time_current:
                        logging.debug(
                            f"current time {self.__time_current:.2f} outside durection {self.__time_total} "
                        )
                    delta = abs(self.__time_current - self.__beats[0])
                    if round(delta) < 0.07:
                        self.__addToQueue(next(PlayingIcon).value)
                        self.__beats.pop(0)
                        self.__beat_count += 1
            except Exception as e:
                logging.error(e, exc_info=True)
            finally:
                sleep(0.1)

    def __addToQueue(self, icon):
        self.__ui_queue.put_nowait(
            BPMEvent(
                icon=icon,
                beat_no=self.__beat_count,
                tempo=str(self.__bpm),
                time_elapsed=int(self.__time_current),
                expires=time() + 0.14,
            )
        )

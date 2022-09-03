import logging
from queue import Queue
from threading import Event
from yanko.core.thread import StoppableThread
from dataclasses_json import dataclass_json, Undefined
from dataclasses import dataclass
from time import time, sleep
from yanko.sonic import NowPlaying
from yanko.ui.models import AnimatedIcon, Symbol

PausingIcon = AnimatedIcon(icons=[Symbol.GRID1, Symbol.GRID4])

PlayingIcon = AnimatedIcon(icons=[Symbol.GRID2, Symbol.GRID3])


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class BPMEvent:
    icon: str
    tempo: str
    beat_no: int
    time_elapsed: int


class BPM(StoppableThread):

    time_event: Event = None
    __ui_queue: Queue = None
    __now_playing: NowPlaying = None
    __time_start: int = None
    __time_paused: int = None
    __time_current: int = None
    __time_total: int = None
    __bpm: int = None
    __beats: list[float] = None
    __last_measure: float = 0
    __beat_count: int = 0

    def __init__(self, ui_queue: Queue, *args, **kwargs):
        self.time_event = Event()
        self.__ui_queue = ui_queue
        super().__init__(*args, **kwargs)

    @property
    def now_playing(self) -> NowPlaying:
        return self.__now_playing

    def get_static_beats(self):
        bps = self.__bpm / 60
        return [
            round(x / bps, 2) for x in range(0, int(self.__time_total * bps))
        ]

    @now_playing.setter
    def now_playing(self, np: NowPlaying):
        self.__now_playing = np
        self.__time_start = None
        self.__time_current = None
        self.__time_paused = 0
        self.__time_total = np.track.duration
        self.__last_measure = None
        self.__bpm = np.bpm
        self.__beats = np.beats
        self.__beat_count = 1
        if self.__beats:
            total_beats = len(self.__beats)
            beats_bmp = total_beats / (self.__time_total / 60)
            np.bpm = int(beats_bmp)
            logging.debug(f"USING {beats_bmp} BEATS for BPM {self.__bpm}")
        else:
            self.__beats = self.get_static_beats()
            logging.debug(f"USING BPM {self.__bpm}")
        

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
                        self.__time_start = time()
                    self.__time_current = time(
                    ) - self.__time_start - self.__time_paused
                    self.__last_measure = None
                    if self.__time_total < self.__time_current:
                        logging.warning(
                            f"current time {self.__time_current:.2f} outside durection {self.__time_total} "
                        )
                    delta = abs(self.__time_current - self.__beats[0])
                    if round(delta) < 0.07:
                        self.__addToQueue(next(PlayingIcon).value)
                        self.__beats.pop(0)
                        self.__beat_count += 1
            except Exception as e:
                logging.error(e)
            finally:
                sleep(0.1)

    def __addToQueue(self, icon):
        self.__ui_queue.put_nowait(
            BPMEvent(icon=icon,
                     beat_no=self.__beat_count,
                     tempo=self.__bpm,
                     time_elapsed=self.__time_current))

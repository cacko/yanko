from queue import Empty
from typing import Optional, Any
import numpy as np
import sounddevice as sd
import logging
from queue import Queue
from corethread import StoppableThread
from threading import Event
from yanko.player.device import Device
from yanko.sonic import Action, Command, Playstatus, Status, VolumeStatus
from .exceptions import StreamEnded


class Output(StoppableThread):

    data_queue: Queue
    control_queue: Queue
    time_event: Event
    paused_event: Event
    end_event: Event
    muted: bool
    volume: int
    needs_buffering = True
    __stream: sd.RawOutputStream

    def __init__(
        self,
        time_event: Event,
        end_event: Event,
        volume: int,
        muted: bool,
        *args,
        **kwargs,
    ):
        self.volume = volume
        self.muted = muted
        self.data_queue = Queue(maxsize=100)
        self.control_queue = Queue()
        self.time_event = time_event
        self.end_event = end_event
        self.paused_event = Event()
        self.__stream = sd.RawOutputStream(
            samplerate=Device.samplerate,
            blocksize=Device.blocksize,
            device=Device.index,
            channels=Device.output_channels,
            dtype="float32",
        )
        super().__init__(*args, **kwargs)

    @property
    def samplesize(self) -> int:
        return self.__stream.samplesize

    def run(self):
        logging.info(f"Output thead started")
        self.__stream.start()
        with self.__stream:
            logging.debug(f"Buffering {Device.buffsize} blocks")
            while self.needs_buffering:
                sd.sleep(10)
                self.needs_buffering = self.data_queue.qsize() < Device.buffsize
            logging.debug(f"Buffered {self.data_queue.qsize()} blocks")
            while not self.stopped():
                try:
                    if self.paused_event.is_set():
                        sd.sleep(50)
                    else:
                        self.__output()
                except Empty:
                    self.end_event.set()
                    break
            self.__stream.close()

    def __output(self):
        data = self.data_queue.get_nowait()
        data_array = np.frombuffer(data, dtype="float32")
        volume_norm = data_array * (0 if self.muted else self.volume)
        self.__stream.write(volume_norm.tobytes())
        self.time_event.set()
        self.data_queue.task_done()

    def __control(self):
        try:
            cmd = self.control_queue.get_nowait()
            self.control_queue.task_done()
        except Empty:
            pass

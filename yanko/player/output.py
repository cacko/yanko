from queue import Empty
import numpy as np
import sounddevice as sd
import logging
from queue import Queue
from corethread import StoppableThread
from threading import Event
from yanko.player.device import Device
from yanko.sonic import Action


class Output(StoppableThread):

    data_queue: Queue
    control_queue: Queue
    time_event: Event
    end_event: Event
    paused: bool
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
        self.paused = False
        self.data_queue = Queue(maxsize=Device.buffsize)
        self.control_queue = Queue()
        self.time_event = time_event
        self.end_event = end_event
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
                sd.sleep(500)
                self.needs_buffering = self.data_queue.qsize() < Device.buffsize
            logging.debug(f"Buffered {self.data_queue.qsize()} blocks")
            while not self.stopped():
                try:
                    if self.paused:
                        self.time_event.clear()
                        sd.sleep(100)
                    else:
                        self.__output()
                    self.__control()
                except Empty:
                    self.end_event.set()
                    break
            self.__stream.close()

    def __output(self):
        data = self.data_queue.get()
        data_array = np.frombuffer(data, dtype="float32")
        volume_norm = data_array * (0 if self.muted else self.volume)
        self.__stream.write(volume_norm.tobytes())
        self.time_event.set()
        self.data_queue.task_done()

    def __control(self):
        try:
            command, payload = self.control_queue.get_nowait()
            match (command):
                case Action.VOLUME_DOWN:
                    self.volume = payload
                case Action.VOLUME_UP:
                    self.volume = payload
                case Action.MUTE:
                    self.muted = payload
                case Action.PAUSE:
                    self.paused = True
                case Action.RESUME:
                    self.paused = False
                case _:
                    return None
        except Empty:
            pass

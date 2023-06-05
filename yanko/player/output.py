from queue import Empty
import numpy as np
import sounddevice as sd
import logging
from queue import Queue
from corethread import StoppableThread
from threading import Event
from yanko.player.device import Device
from yanko.sonic import Action
import osascript


class Output(StoppableThread):

    needs_buffering = True
    __volume: float = 1.0
    __muted: bool = False

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
        self.data_queue: Queue = Queue()
        self.control_queue: Queue = Queue()
        self.time_event = time_event
        self.end_event = end_event
        self.__stream = sd.RawOutputStream(
            samplerate=Device.samplerate,
            blocksize=Device.blocksize,
            extra_settings=(
                sd.CoreAudioSettings(
                    change_device_parameters=True
                )
            ),
            device=Device.index,
            channels=Device.output_channels,
            dtype="float32",
            dither_off=True,
            clip_off=True,
        )
        super().__init__(*args, **kwargs)

    @property
    def volume(self) -> int:
        return int(self.__volume)

    @volume.setter
    def volume(self, val: float = 1.0):
        self.__volume = int(50 * val)
        osascript.osascript(f"set volume output volume {self.__volume}")

    @property
    def muted(self) -> bool:
        return self.__muted

    @muted.setter
    def muted(self, val: bool = False):
        self.__muted = val
        mode = "with" if val else "without"
        osascript.osascript(f"set volume {mode} output muted")

    @property
    def samplesize(self) -> int:
        return self.__stream.samplesize  # type: ignore

    def run(self):
        logging.info("Output thead started")
        self.__stream.start()
        with self.__stream:
            logging.debug(f"Buffering {Device.buffsize} blocks")
            while self.needs_buffering:
                sd.sleep(20)
                self.needs_buffering = self.data_queue.qsize() < Device.buffsize
            logging.debug(f"Buffered {self.data_queue.qsize()} blocks")
            while not self.stopped():
                try:
                    if self.paused:
                        sd.sleep(100)
                    else:
                        self.__output()
                    self.__control()
                except Empty:
                    logging.debug(f"empty bufff {self.data_queue.qsize()}")
                    break
        logging.debug("Writing finished")
        self.end_event.set()

    def __output(self):
        data = self.data_queue.get_nowait()
        data_array = np.frombuffer(data, dtype="float32")
        self.time_event.set()
        self.__stream.write(data_array.tobytes())
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
                    self.time_event.clear()
                case Action.RESUME:
                    self.paused = False
                case _:
                    return None
        except Empty:
            pass

import queue
import sys
import time as _time
from dataclasses import dataclass, field
from queue import Empty
from typing import Optional
import ffmpeg
import numpy as np
import sounddevice as sd
from dataclasses_json import Undefined, dataclass_json

from yanko.core.bytes import nearest_bytes
from yanko.player.base import BasePlayer
from yanko.sonic import Action, Command, Playstatus, Status, VolumeStatus
import logging


def int_or_str(text):
    """Helper function for argument parsing."""
    try:
        return int(text)
    except ValueError:
        return text


class BpmExeNotFound(Exception):
    pass


class StreamEnded(Exception):
    pass


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class OutputDevice:
    name: Optional[str] = None
    index: Optional[int] = None
    hostapi: Optional[int] = None
    max_input_channels: Optional[int] = None
    max_output_channels: Optional[int] = None
    default_low_input_latency: Optional[float] = None
    default_low_output_latency: Optional[float] = None
    default_high_input_latency: Optional[float] = None
    default_high_output_latency: Optional[float] = None
    default_samplerate: Optional[float] = None
    prime_output_buffers_using_stream_callback: bool = field(default=True)

    def __post_init__(self):
        if not self.default_samplerate:
            self.default_samplerate = 44100.0

    @property
    def blocksize(self) -> int:
        return nearest_bytes(int(self.samplerate * self.latency))

    @property
    def latency(self) -> float:
        if not self.default_high_output_latency:
            self.default_high_output_latency = 1
        if not self.default_low_output_latency:
            self.default_low_output_latency = 1
        return max(
            filter(
                lambda x: x,
                [self.default_high_output_latency, self.default_low_output_latency],
            )
        )

    @property
    def output_channels(self) -> int:
        if not self.max_output_channels:
            return 2
        return int(self.max_output_channels)

    @property
    def input_channels(self) -> int:
        if not self.max_input_channels:
            return 2
        return int(self.max_input_channels)

    @property
    def samplerate(self) -> float:
        if not self.default_samplerate:
            return 0
        return float(self.default_samplerate)

    @property
    def buffsize(self) -> int:
        return 20


class FFMPeg(BasePlayer):

    VOLUME_STEP = 0.05
    q: queue.Queue
    __volume = 1
    __muted = False
    __status: Status
    _start = 0

    @property
    def status(self) -> Status:
        return self.__status

    @status.setter
    def status(self, val: Status):
        self.__status = val
        self._manager_queue.put_nowait(
            (Command.PLAYER_RESPONSE, Playstatus(status=val))
        )

    @property
    def volume(self):
        return self.__volume

    @volume.setter
    def volume(self, val):
        self.__volume = val
        self._manager_queue.put_nowait(
            (
                Command.PLAYER_RESPONSE,
                VolumeStatus(
                    volume=self.__volume, muted=self.__muted, timestamp=_time.time()
                ),
            )
        )

    @property
    def muted(self):
        return self.__muted

    @muted.setter
    def muted(self, val):
        self.__muted = val
        self._manager_queue.put_nowait(
            (
                Command.PLAYER_RESPONSE,
                VolumeStatus(
                    volume=self.__volume, muted=self.__muted, timestamp=_time.time()
                ),
            )
        )

    @property
    def device(self) -> OutputDevice:
        _, device = sd.default.device
        device_spec = sd.query_devices(device, "output")
        return OutputDevice(**device_spec)  # type: ignore

    def probe(self):
        try:
            info = ffmpeg.probe(self.stream_url)
            streams = info.get("streams", [])
            stream = streams[0]
            logging.warning(stream)
            if stream.get("codec_type") != "audio":
                logging.warning("The stream must be an audio stream")
                return Status.STOPPED
            return stream
        except ffmpeg.Error as e:
            sys.stderr.buffer.write(e.stderr)

    def play(self):
        device = self.device
        logging.debug(device)
        self.q = queue.Queue(maxsize=device.buffsize)
        try:
            logging.debug("Opening stream ...")
            process = (
                ffmpeg.input(
                    self.stream_url,
                    tcp_nodelay=1,
                    reconnect_on_network_error=1,
                    reconnect_streamed=1,
                    multiple_requests=1,
                    reconnect_delay_max=5,
                )
                .output(
                    "pipe:",
                    format="f32le",
                    acodec="pcm_f32le",
                    ac=device.output_channels,
                    ar=device.samplerate,
                    loglevel="quiet",
                )
                .run_async(pipe_stdout=True)
            )
            stream = sd.RawOutputStream(
                samplerate=device.samplerate,
                blocksize=device.blocksize,
                device=device.index,
                channels=device.output_channels,
                dtype="float32",
                callback=self.callback,
            )
            read_size = device.blocksize * device.output_channels * stream.samplesize
            logging.debug("Buffering ...")
            for _ in range(device.buffsize):
                self.q.put_nowait(process.stdout.read(read_size))
            logging.debug("Starting Playback ...")
            with stream:
                self.status = Status.PLAYING
                timeout = device.blocksize * device.buffsize / device.samplerate
                while True:
                    if not stream.active:
                        raise StreamEnded
                    if self.status == Status.PAUSED:
                        self._time_event.clear()
                        sd.sleep(50)
                    else:
                        self.q.put(process.stdout.read(read_size), timeout=timeout)
                    if queue_action := self.process_queue():
                        self._time_event.clear()
                        process.terminate()
                        stream.close()
                        self.status = Status.STOPPED
                        return queue_action
        except queue.Full:
            pass
        except StreamEnded:
            pass
        except Exception as e:
            logging.error(e)
        self._time_event.clear()
        return Status.PLAYING

    def callback(self, outdata, frames, time, status):
        while self.status == Status.PAUSED:
            self._time_event.clear()
            sd.sleep(50)
        assert frames == self.device.blocksize
        if status.output_underflow:
            logging.debug("Output underflow: increase blocksize?")
            raise sd.CallbackAbort
        assert not status
        try:
            data = self.q.get_nowait()
        except queue.Empty as e:
            logging.debug("Buffer is empty: increase buffersize?")
            raise sd.CallbackAbort from e
        except ValueError as e:
            logging.error(3)
            raise StreamEnded
        assert len(data) == len(outdata)
        data_array = np.frombuffer(data, dtype="float32")
        volume_norm = data_array * (0 if self.muted else self.volume)
        self._time_event.set()
        outdata[:] = volume_norm.tobytes()[: len(outdata)]

    def process_queue(self):
        try:
            command = self._queue.get_nowait()
            match (command):
                case Action.RESTART:
                    self._queue.task_done()
                    return self._restart()
                case Action.NEXT:
                    self._queue.task_done()
                    return self._next()
                case Action.PREVIOUS:
                    self._queue.task_done()
                    return self._previous()
                case Action.STOP:
                    self._queue.task_done()
                    return self._stop()
                case Action.EXIT:
                    self._queue.task_done()
                    return self.exit()
                case Action.PAUSE:
                    self.status = Status.PAUSED
                case Action.RESUME:
                    self.status = Status.RESUMED
                case Action.VOLUME_DOWN:
                    self.volume = max(0, self.volume - self.VOLUME_STEP)
                case Action.VOLUME_UP:
                    self.volume = min(2, self.volume + self.VOLUME_STEP)
                case Action.MUTE:
                    self.muted = not self.muted
                case _:
                    return None
        except Empty:
            return None
        self._queue.task_done()

    def _stop(self):
        return Status.STOPPED

    def _restart(self):
        return self.play()

    def _next(self):
        return Status.NEXT

    def _previous(self):
        return Status.PREVIOUS

    def pause(self):
        self._queue.put_nowait(Action.PAUSE)

    def resume(self):
        self._queue.put_nowait(Action.RESUME)

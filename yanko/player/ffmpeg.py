from dataclasses import dataclass
from dataclasses_json import dataclass_json, Undefined
import queue
import sys
import ffmpeg
import sounddevice as sd
import logging
import numpy as np
import time
from yanko.player.base import BasePlayer
from yanko.sonic import Status, Action, VolumeStatus
from yanko.player.base import BasePlayer
from typing import Optional
from yanko.core.bytes import nearest_bytes


def int_or_str(text):
    """Helper function for argument parsing."""
    try:
        return int(text)
    except ValueError:
        return text


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

    def __post_init__(self):
        if not self.default_samplerate:
            self.default_samplerate = 44100.0

    @property
    def blocksize(self) -> int:
        latency = max(filter(lambda x: x, [
            self.default_high_output_latency,
            self.default_low_output_latency
        ]))
        return nearest_bytes(int(self.default_samplerate * latency))

    @property
    def output_channels(self) -> int:
        return int(self.max_output_channels)

    @property
    def input_channels(self) -> int:
        return int(self.max_input_channels)

    @property
    def samplerate(self) -> float:
        return float(self.default_samplerate)

    @property
    def buffsize(self) -> int:
        return 20


class FFMPeg(BasePlayer):

    VOLUME_STEP = 0.05
    q: queue.Queue = None
    status: Status = None
    __volume = 1
    __muted = False

    @property
    def volume(self):
        return self.__volume

    @volume.setter
    def volume(self, val):
        self.__volume = val
        self._manager_queue.put_nowait(
            VolumeStatus(
                volume=self.__volume,
                muted=self.__muted,
                timestamp=time.time()
            )
        )

    @property
    def muted(self):
        return self.__muted

    @muted.setter
    def muted(self, val):
        self.__muted = val
        self._manager_queue.put_nowait(
            VolumeStatus(
                volume=self.__volume,
                muted=self.__muted,
                timestamp=time.time()
            )
        )

    @property
    def device(self) -> OutputDevice:
        _, device = sd.default.device
        device_spec = sd.query_devices(device, 'output')
        return OutputDevice(**device_spec)

    def probe(self):
        try:
            info = ffmpeg.probe(self.stream_url)
        except ffmpeg.Error as e:
            sys.stderr.buffer.write(e.stderr)
        streams = info.get('streams', [])
        stream = streams[0]
        if stream.get('codec_type') != 'audio':
            logging.warning('The stream must be an audio stream')
            return Status.STOPPED
        return stream

    def play(self):
        device = self.device
        logging.debug(device)
        self.q = queue.Queue(maxsize=device.buffsize)
        self.status = Status.PLAYING
        try:
            logging.debug('Opening stream ...')
            process = ffmpeg.input(self.stream_url).filter(
                'loudnorm', I=-16, LRA=11, tp=-1.5
            ).filter(
                'virtualbass'
            ).output(
                'pipe:',
                format='f32le',
                acodec='pcm_f32le',
                ac=device.output_channels,
                ar=device.samplerate,
                loglevel='quiet',
            ).run_async(pipe_stdout=True)
            stream = sd.RawOutputStream(
                samplerate=device.samplerate,
                blocksize=device.blocksize,
                device=device.index,
                channels=device.output_channels,
                dtype='float32',
                callback=self.callback
            )
            read_size = device.blocksize * device.output_channels * stream.samplesize
            logging.debug('Buffering ...')
            for _ in range(device.buffsize):
                self.q.put_nowait(process.stdout.read(read_size))
            logging.debug('Starting Playback ...')
            with stream:
                timeout = device.blocksize * device.buffsize / device.samplerate
                while True:
                    if self.status == Status.PAUSED:
                        sd.sleep(50)
                    else:
                        self.q.put(process.stdout.read(
                            read_size), timeout=timeout)
                    if queue_action := self.process_queue():
                        self.status = Status.STOPPED
                        process.terminate()
                        stream.close()
                        return queue_action
            process.wait()
        except queue.Full:
            pass
        except Exception as e:
            logging.error(e)
        return Status.PLAYING

    def callback(self, outdata, frames, time, status):
        while self.status == Status.PAUSED:
            sd.sleep(50)
        assert frames == self.device.blocksize
        if status.output_underflow:
            logging.debug(
                'Output underflow: increase blocksize?', file=sys.stderr)
            raise sd.CallbackAbort
        assert not status
        try:
            data = self.q.get_nowait()
            data_array = np.frombuffer(data, dtype='float32')
            volume_norm = data_array * (0 if self.muted else self.volume)
            outdata[:] = volume_norm.tobytes()
        except queue.Empty as e:
            logging.debug(
                'Buffer is empty: increase buffersize?', file=sys.stderr)
            raise sd.CallbackAbort from e

    def process_queue(self):
        if self._queue.empty():
            return None
        command = self._queue.get_nowait()
        self._queue.task_done()
        match (command):
            case Action.RESTART:
                return self._restart()
            case Action.NEXT:
                return self._next()
            case Action.PREVIOUS:
                return self._previous()
            case Action.STOP:
                return self._stop()
            case Action.EXIT:
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
        return None

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

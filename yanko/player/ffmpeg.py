import queue
import sys
import time as _time
from queue import Empty
from typing import Optional
import ffmpeg
import numpy as np
import sounddevice as sd
from .device import Device
from yanko.player.base import BasePlayer
from yanko.sonic import Action, Command, Playstatus, Status, VolumeStatus
import logging
from .input import Input
from .output import Output
from .exceptions import StreamEnded
from threading import Event


def int_or_str(text):
    """Helper function for argument parsing."""
    try:
        return int(text)
    except ValueError:
        return text


class FFMPeg(BasePlayer):

    __status: Optional[Status] = None
    __reader: Optional[Input] = None
    __writer: Optional[Output] = None
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
        try:
            end_event = Event()
            self.__writer = Output(
                time_event=self._time_event,
                volume=self.volume,
                muted=self.muted,
                end_event=end_event,
            )
            logging.debug("Opening stream ...")
            self.__reader = Input(
                url=self.stream_url,
                outputQueue=self.__writer.data_queue,
                blocksize=Device.blocksize,
                output_channels=Device.output_channels,
                samplerate=Device.samplerate,
                samplesize=self.__writer.samplesize,
            )
            self.__writer.start()
            self.__reader.start()
            while not end_event.is_set():
                if queue_action := self.process_queue():
                    self._time_event.clear()
                    self.__reader.stop()
                    self.__writer.stop()
                    self.status = Status.STOPPED
                    return queue_action
        except StreamEnded:
            pass
        except Exception as e:
            logging.error(e)
        self.__reader.stop()
        self.__writer.stop()
        self._time_event.clear()
        return Status.PLAYING

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
                    self.__writer.paused_event.set()
                    self.status = Status.PAUSED
                case Action.RESUME:
                    self.__writer.paused_event.clear()
                    self.status = Status.RESUMED
                # case Action.VOLUME_DOWN:
                #     self.volume = max(0, self.volume - self.VOLUME_STEP)
                #     self.__writer.volume = self.volume
                # case Action.VOLUME_UP:
                #     self.volume = min(2, self.volume + self.VOLUME_STEP)
                #     self.__writer.volume = self.volume
                # case Action.MUTE:
                #     self.muted = not self.muted
                #     self.__writer.muted = self.muted
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

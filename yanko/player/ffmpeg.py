import sys
import time as _time
from queue import Empty
from typing import Optional
import ffmpeg
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
            self._control = self.__writer.control_queue
            logging.debug("Opening stream ...")
            self.__reader = Input(
                url=self.stream_url,
                outputQueue=self.__writer.data_queue,
                samplesize=self.__writer.samplesize,
            )
            self.__writer.start()
            self.__reader.start()
            self.status = Status.PLAYING
            while not end_event.is_set():
                if queue_action := self.process_queue():
                    self._time_event.clear()
                    self.__reader.stop()
                    self.__writer.stop()
                    self.status = Status.STOPPED
                    return queue_action
                _time.sleep(0.1)
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
            command, payload = self._queue.get()
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
                    self._control.put_nowait((Action.PAUSE, None))
                    self.status = Status.PAUSED
                case Action.RESUME:
                    self._control.put_nowait((Action.RESUME, None))
                    self.status = Status.RESUMED
                case Action.VOLUME_DOWN:
                    self._control.put_nowait((Action.VOLUME_DOWN, payload))
                case Action.VOLUME_UP:
                    self._control.put_nowait((Action.VOLUME_UP, payload))
                case Action.MUTE:
                    self._control.put_nowait((Action.MUTE, payload))
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

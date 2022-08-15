import logging
from yanko.sonic import Status, Action
from yanko.player.base import BasePlayer
import miniaudio
import urllib.request
from miniaudio import SeekOrigin, FileFormat
from time import sleep


class SubsonicSource(miniaudio.StreamableSource):

    paused = False

    def __init__(self, filename: str) -> None:
        self.file = urllib.request.urlopen(filename)

    def read(self, num_bytes: int) -> bytes:
        return self.file.read(num_bytes)

    def seek(self, offset: int, origin: SeekOrigin) -> bool:
        return True

    def close(self) -> None:
        self.file.close()


class Miniplay(BasePlayer):

    __paused = False
    __return = None
    __device = None

    def stream_progress_callback(self, framecount: int) -> None:
        while self.__paused:
            sleep(0.05)

    def play(self, stream_url, track_data):
        stream_url = self.get_stream_url(stream_url, track_data, format="flac")
        with SubsonicSource(stream_url) as source:
            stream = miniaudio.stream_any(
                source, source_format=FileFormat.FLAC)
            callbacks_stream = miniaudio.stream_with_callbacks(
                stream, progress_callback=self.stream_progress_callback, end_callback=None)
            next(callbacks_stream)
            with miniaudio.PlaybackDevice() as device:
                self.__device = device
                device.start(callbacks_stream)
                while device.running:
                    if self._queue.empty():
                        sleep(0.05)
                    else:
                        command = self._queue.get_nowait()
                        self._queue.task_done()
                        match (command):
                            case Action.RESTART:
                                self._restart(
                                    stream_url, track_data)
                            case Action.NEXT:
                                self._next()
                            case Action.PREVIOUS:
                                self._previous()
                            case Action.STOP:
                                self._stop()
                            case Action.EXIT:
                                self.exit()
                            case Action.PAUSE:
                                self.__paused = True
                            case Action.RESUME:
                                self.__paused = False
        self.__paused = False
        return self.__return if self.__return else Status.PLAYING

    def __terminate(self):
        if self.__device:
            self.__device.stop()
        return Status.STOPPED

    def exit(self):
        self.__return = Status.EXIT
        self.__terminate()

    def _stop(self):
        self.__return = Status.STOPPED
        self.__terminate()

    def _restart(self, stream_url, track_data):
        self.__return = Status.LOADING
        self.__terminate()
        return self.play(stream_url, track_data)

    def _next(self):
        self.__return = Status.NEXT
        self.__terminate()

    def _previous(self):
        self.__return = Status.PREVIOUS
        self.__terminate()

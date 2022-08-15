import logging
from yanko.sonic import Status, Action
from yanko.player.base import BasePlayer
import miniaudio
import urllib.request
from miniaudio import SeekOrigin, FileFormat
from time import sleep


class FileSource(miniaudio.StreamableSource):

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

    __source: FileSource = None
    __has_finished = False
    __paused = False

    def stream_end_callback(self) -> None:
        self.__has_finished = True

    def stream_progress_callback(self, framecount: int) -> None:
        while self.__paused:
            sleep(0.01)

    def play(self, stream_url, track_data):
        stream_url = self.get_stream_url(stream_url, track_data, format="flac")
        self.__has_finished = False
        with FileSource(stream_url) as source:
            self.__source = source
            stream = miniaudio.stream_any(
                source, source_format=FileFormat.FLAC)
            callbacks_stream = miniaudio.stream_with_callbacks(
                stream, self.stream_progress_callback, self.stream_end_callback)
            next(callbacks_stream)
            with miniaudio.PlaybackDevice() as device:
                device.start(callbacks_stream)
                while True:
                    if self.__has_finished:
                        break
                    elif self._queue.empty():
                        sleep(0.01)
                    else:
                        command = self._queue.get_nowait()
                        self._queue.task_done()
                        match (command):
                            case Action.RESTART:
                                return self._restart(stream_url, track_data)
                            case Action.NEXT:
                                return self._next()
                            case Action.PREVIOUS:
                                return self._previous()
                            case Action.STOP:
                                return self._stop()
                            case Action.EXIT:
                                return self.exit()
                            case Action.PAUSE:
                                self.__paused = True
                            case Action.RESUME:
                                self.__paused = False
        return Status.PLAYING

    def __terminate(self):
        if self.__source:
            self.__source.close()
        return Status.STOPPED

    def exit(self):
        self.__terminate()
        return Status.EXIT

    def _stop(self):
        return self.__terminate()

    def _restart(self, stream_url, track_data):
        self.__terminate()
        self.status = Status.LOADING
        return self.play(stream_url, track_data)

    def _next(self):
        self.__terminate()
        return Status.NEXT

    def _previous(self):
        self.__terminate()
        return Status.PREVIOUS

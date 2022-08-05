from subprocess import Popen
from queue import Queue
from yanko.sonic import Status, Action
from pathlib import Path
from yanko.core.config import app_config
from os import environ
import time


class FFPlay(object):

    __proc: Popen = None
    __queue: Queue = None

    def __init__(self, queue):
        self.lock_file.unlink(missing_ok=True)
        self.__queue = queue

    @property
    def lock_file(self) -> Path:
        return app_config.app_dir / "play.lock"

    def play(self, stream_url, track_data):

        song_id = track_data.get("id")

        params = [
            'ffplay',
            '-i',
            '{}&id={}&format=raw'.format(stream_url, song_id),
            '-autoexit',
            '-nodisp',
            '-nostats',
            '-hide_banner',
            '-loglevel',
            'fatal',
            '-infbuf',
            '-af',
            'stereowiden'
        ]
        env = dict(
            environ,
            PATH=f"/opt/homebrew/bin/:{environ.get('HOME')}/.local/bin:/usr/bin:/usr/local/bin:{environ.get('PATH')}",
        )
        self.__proc = Popen(params, env=env)

        has_finished = None
        self.lock_file.open("w+").close()

        while has_finished is None:
            has_finished = self.__proc.poll() if self.__proc else True
            if self.__queue.empty():
                time.sleep(0.1)
                continue

            command = self.__queue.get_nowait()
            self.__queue.task_done()

            match (command):
                case Action.RESTART:
                    return self.__restart(stream_url, track_data)
                case Action.NEXT:
                    return self.__next()
                case Action.STOP:
                    return self.__stop()
                case Action.EXIT:
                    return self.exit()
        self.lock_file.unlink(missing_ok=True)
        return Status.PLAYING

    def send_signal(self, signal):
        if self.__proc:
            return self.__proc.send_signal(signal)

    def __terminate(self):
        self.lock_file.unlink(missing_ok=True)
        if self.__proc:
            self.__proc.terminate()
            self.__proc = None
        return Status.STOPPED

    def exit(self):
        self.__terminate()
        return Status.EXIT

    def __stop(self):
        return self.__terminate()

    def __restart(self, stream_url, track_data):
        self.__terminate()
        self.status = Status.LOADING
        return self.play(stream_url, track_data)

    def __next(self):
        self.__terminate()
        return Status.NEXT

from subprocess import Popen, run
from queue import Queue
from yanko.sonic import Status, Action
from pathlib import Path
from yanko.core.config import app_config
from urllib.parse import urlparse, parse_qs, urlencode
from os import environ
from time import sleep


class FFPlay(object):

    __proc: Popen = None
    __queue: Queue = None
    __url = None

    def __init__(self, queue):
        self.lock_file.unlink(missing_ok=True)
        self.__queue = queue

    @property
    def lock_file(self) -> Path:
        return app_config.app_dir / "play.lock"

    @property
    def hasFinished(self):
        if not self.__proc:
            return True
        return self.__proc.poll() is None

    def play(self, stream_url, track_data):
        song_id = track_data.get("id")
        url = urlparse(stream_url)
        query = parse_qs(url.query)
        query = {"id": song_id, "format": "raw", **query}
        self.__url = f"{url.scheme}://{url.netloc}{url.path}?{urlencode(query, doseq=True)}"
        params = [
            'ffplay',
            '-i',
            self.__url,
            '-t',
            f'{track_data.get("duration")}',
            '-autoexit',
            '-nodisp',
            '-nostats',
            '-hide_banner',
            '-loglevel',
            'fatal',
            '-infbuf',
            '-sn',
            '-af',
            'loudnorm=I=-16:LRA=11:TP=-1.5',
            '-af',
            'virtualbass',
        ]
        env = dict(
            environ,
            PATH=f"{environ.get('HOME')}/.local/bin:/usr/bin:/usr/local/bin:{environ.get('PATH')}",
        )
        self.__proc = Popen(params, env=env)
        self.lock_file.open("w+").close()
        run(['sudo', 'renice', '-5', f"{self.__proc.pid}"])
        while self.hasFinished:
            if self.__queue.empty():
                sleep(0.1)
                continue

            command = self.__queue.get_nowait()
            self.__queue.task_done()
            match (command):
                case Action.RESTART:
                    return self.__restart(stream_url, track_data)
                case Action.NEXT:
                    return self.__next()
                case Action.PREVIOUS:
                    return self.__previous()
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

    def __previous(self):
        self.__terminate()
        return Status.PREVIOUS

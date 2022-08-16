from configparser import NoSectionError
from subprocess import Popen, run, PIPE
from yanko.sonic import Status, Action
from os import environ
from signal import SIGSTOP, SIGCONT
from yanko.player.base import BasePlayer
from time import sleep
import requests


class FFStream():

    __req = None
    __input: PIPE = None

    def __init__(self, url, input):
        self.__req = requests.get(url, stream=True)
        self.__input = input

    def __enter__(self):
        print('enter method called')
        return self

    def fragments(self):
        for frag in self.__req.iter_content(1024):
            self.__input.write(frag)
            yield len(frag)

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.__req.close()


class FFPlay(BasePlayer):

    __proc: Popen = None
    __paused = False
    __url = None
    __track = NoSectionError

    @property
    def process_has_finished(self):
        if not self.__proc:
            return True
        return self.__proc.poll() is None

    def play(self, stream_url, track_data):
        self.__track = track_data
        self.__url = self.get_stream_url(stream_url, track_data)
        params = [
            'ffplay',
            '-i',
            'pipe:0',
            '-autoexit',
            '-nodisp',
            '-nostats',
            '-hide_banner',
            '-loglevel',
            'fatal',
            '-noinfbuf',
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
        self.__proc = Popen(params, stdin=PIPE, env=env)
        self.lock_file.open("w+").close()
        run(['sudo', 'renice', '-5', f"{self.__proc.pid}"])

        with FFStream(self.__url, self.__proc.stdin) as stream:
            for _ in stream.fragments():
                if queue_action := self.process_queue():
                    return queue_action
        while not self.process_has_finished:
            if queue_action := self.process_queue():
                return queue_action
            sleep(0.05)
        return Status.PLAYING

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
                self.__paused = True
            case Action.RESUME:
                self.__paused = False

    def __terminate(self):
        self.lock_file.unlink(missing_ok=True)
        if self.__proc:
            self.__proc.terminate()
            self.__proc = None
        return Status.STOPPED

    def exit(self):
        self.__terminate()
        return Status.EXIT

    def _stop(self):
        return self.__terminate()

    def _restart(self):
        self.__terminate()
        self.status = Status.LOADING
        return self.play(self.__url, self.__track)

    def _next(self):
        self.__terminate()
        return Status.NEXT

    def _previous(self):
        self.__terminate()
        return Status.PREVIOUS

    def pause(self):
        if not self.__paused:
            self._queue.put_nowait(Action.PAUSE)

    def resume(self):
        if self.__paused:
            self._queue.put_nowait(Action.RESUME)

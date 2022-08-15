from http.cookiejar import DefaultCookiePolicy
from subprocess import Popen, run, PIPE
from yanko.sonic import Status, Action
from os import environ
from signal import SIGSTOP, SIGCONT
from yanko.player.base import BasePlayer
from time import sleep
import requests


class FFStream():

    __req = None

    def __init__(self, url):
        self.__req = requests.get(url, stream=True)

    def __enter__(self):
        print('enter method called')
        return self.gen()

    def gen(self):
        for frag in self.__req.iter_content(192000):
            yield frag

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.__req.close()


class FFPlay(BasePlayer):

    __proc: Popen = None

    @property
    def hasFinished(self):
        if not self.__proc:
            return True
        return self.__proc.poll() is None

    def play(self, stream_url, track_data):
        stream_url = self.get_stream_url(stream_url, track_data)
        params = [
            'ffplay',
            '-i',
            'pipe:0',
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
        self.__proc = Popen(params, stdin=PIPE, env=env)
        self.lock_file.open("w+").close()
        run(['sudo', 'renice', '-5', f"{self.__proc.pid}"])

        with FFStream(stream_url) as stream:
            for frag in stream:
                self.__proc.stdin.write(frag)
                if self._queue.empty():
                    sleep(0.05)
                    continue

                command = self._queue.get_nowait()
                self._queue.task_done()
                match (command):
                    case Action.RESTART:
                        return self._restart(stream_url, track_data)task DefaultCookiePolicy
                    case Action.NEXT:
                        return self._next()
                    case Action.PREVIOUS:
                        return self._previous()
                    case Action.STOP:
                        return self._stop()
                    case Action.EXIT:
                        return self.exit()

        return Status.PLAYING

    def __send_signal(self, signal):
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

    def pause(self):
        return self.__send_signal(SIGSTOP)

    def resume(self):
        return self.__send_signal(SIGCONT)

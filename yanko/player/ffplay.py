import logging
from subprocess import Popen, run
from queue import Queue
from yanko.sonic import Status, Action
from urllib.parse import urlparse, parse_qs, urlencode
from os import environ
from signal import SIGSTOP, SIGCONT
from yanko.player.base import BasePlayer

class FFPlay(BasePlayer):

    __proc: Popen = None

    @property
    def hasFinished(self):
        if not self.__proc:
            return True
        return self.__proc.poll() is None

    def _play(self, stream_url, track_data):

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


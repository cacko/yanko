

import logging
from queue import Queue
from traceback import print_exc
from pynput import keyboard
from pynput.keyboard import Key, HotKey
from pynput.keyboard._darwin import (
    NX_KEYTYPE_PLAY,
    NX_KEYTYPE_MUTE,
    NX_KEYTYPE_SOUND_DOWN,
    NX_KEYTYPE_SOUND_UP,
    NX_KEYTYPE_NEXT,
    NX_KEYTYPE_PREVIOUS,
)
from yanko.sonic import Command

from pynput import keyboard



class HotKeysMeta(type):

    _instance = None
    _queue: Queue = None

    def __call__(self, *args, **kwds):
        if not self._instance:
            self._instance = super().__call__(*args, **kwds)
        return self._instance

    def start(cls, queue=None):
        cls._queue = queue
        return cls().listen()

    def stop(cls):
        return cls().stop_listen()


class HotKeys(object, metaclass=HotKeysMeta):

    def listen(self):
        with keyboard.GlobalHotKeys({
                f'<{NX_KEYTYPE_PLAY}>': self.on_media_play_pause,
                f'<cmd>+<{NX_KEYTYPE_PLAY}>': self.on_cmd_media_play_pause,
                f'<{NX_KEYTYPE_NEXT}>': self.on_media_next,
                f'<cmd>+<{NX_KEYTYPE_NEXT}>': self.on_cmd_media_next,
                f'<{NX_KEYTYPE_PREVIOUS}>': self.on_media_prev,
                f'<cmd>+<{NX_KEYTYPE_PREVIOUS}>': self.on_cmd_media_prev,

        }, force_hotkeys=True) as h:
            try:
                h.join()
                print("ended")
            except Exception as e:
                print_exc(e)

    def on_media_play_pause(self):
        __class__._queue.put_nowait(
            (Command.TOGGLE, None)
        )

    def on_cmd_media_play_pause(self):
        __class__._queue.put_nowait(
            (Command.RANDOM, None)
        )

    def on_media_next(self):
        __class__._queue.put_nowait(
            (Command.NEXT, None)
        )

    def on_cmd_media_next(self):
        __class__._queue.put_nowait(
            (Command.RANDOM_ALBUM, None)
        )

    def on_media_prev(self):
        __class__._queue.put_nowait(
            (Command.PREV, None)
        )

    def on_cmd_media_prev(self):
        __class__._queue.put_nowait(
            (Command.RESTART, None)
        )
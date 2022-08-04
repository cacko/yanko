

from queue import Queue
from traceback import print_exc
from pynput import keyboard
from pynput.keyboard import Key
from yanko.sonic import Command
import Quartz

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

    __cmd_pressed = False
    __listener = None

    def listen(self):
        try:
            self.__listener = keyboard.Listener(
                on_press=self.on_press,
                on_release=self.on_release,
                )
            self.__listener.start()
        except Exception as e:
            print_exc(e)

    def stop_listen(self):
        try:
            self.__listener.stop()
        except Exception as e:
            print_exc(e)

    def on_press(self, key):
        if key == Key.cmd:
            self.__cmd_pressed = True

    def on_release(self, key):
        match(key):
            case Key.cmd:
                self.__cmd_pressed = False
            case Key.media_play_pause:
                __class__._queue.put_nowait(
                    (Command.RANDOM if self.__cmd_pressed else Command.TOGGLE, None)
                )
            case Key.media_next:
                __class__._queue.put_nowait(
                    (Command.RANDOM_ALBUM if self.__cmd_pressed else Command.NEXT, None)
                )
            case Key.media_previous:
                __class__._queue.put_nowait(
                    (Command.RESTART if self.__cmd_pressed else Command.PREV, None)
                )

from queue import Queue
from quickmachotkey import quickHotKey, mask
from quickmachotkey.constants import (
    kVK_F12,
    kVK_F11,
    kVK_F8,
    cmdKey
)
from yanko.sonic import Command


def register(queue: Queue):

    @quickHotKey(virtualKey=kVK_F12, modifierMask=mask())
    def volup() -> None:
        queue.put_nowait((Command.VOLUME_UP, None))

    @quickHotKey(virtualKey=kVK_F11, modifierMask=mask())
    def voldown() -> None:
        queue.put_nowait((Command.VOLUME_DOWN, None))

    @quickHotKey(virtualKey=kVK_F8, modifierMask=mask())
    def toggle() -> None:
        queue.put_nowait((Command.TOGGLE, None))

    @quickHotKey(virtualKey=kVK_F8, modifierMask=mask(cmdKey))
    def random() -> None:
        queue.put_nowait((Command.RANDOM, None))

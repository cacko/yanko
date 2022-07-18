from re import U
from sys import prefix
from rumps import MenuItem
from pathlib import Path
from enum import Enum
from dataclasses_json import dataclass_json, Undefined
from dataclasses import dataclass
from typing import Optional
import arrow
from yanko.core.string import name_to_code


class Label(Enum):
    PLAY = 'Play'
    STOP = 'Stop'
    FIND = 'Find'
    RANDOM = 'Random'
    ALBUM = 'Album'
    NEXT = 'Next Song'
    RESTART = 'Replay'
    QUIT = 'Quit'


class Icon(Enum):
    PLAY = 'play.png'
    STOP = 'stop.png'
    FIND = 'find.png'
    QUIT = 'quit.png'
    RANDOM = 'random.png'
    ALBUM = 'album.png'
    NEXT = 'next.png'
    RESTART = 'restart.png'
    NOT_PLAYING = 'not_playing.png'
    PLAYING = 'playing.png'

    def __new__(cls, *args):
        icons_path: Path = Path(__file__).parent / "icons"
        value = icons_path / args[0]
        obj = object.__new__(cls)
        obj._value_ = value.as_posix()
        return obj


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class ApiStats:
    activeWorkers: int
    lastSeen: int
    usdPerMin: float
    averageHashrate: float
    currentHashrate: float
    pool: str


class ActionItemMeta(type):

    _instances = {}

    def __call__(cls, name, *args, **kwds):
        if name not in cls._instances:
            cls._instances[name] = super().__call__(*args, **kwds)
        return cls._instances[name]

    @property
    def play(cls) -> 'ActionItem':
        return cls("start", Label.PLAY.value, icon=Icon.PLAY.value)

    @property
    def stop(cls) -> 'ActionItem':
        return cls("stop", Label.STOP.value, icon=Icon.STOP.value)

    @property
    def next(cls) -> 'ActionItem':
        return cls("next", Label.NEXT.value, icon=Icon.NEXT.value)

    @property
    def restart(cls) -> 'ActionItem':
        return cls("restart", Label.RESTART.value, icon=Icon.RESTART.value)

    @property
    def find(cls) -> 'ActionItem':
        return cls("find", Label.FIND.value, icon=Icon.FIND.value)

    @property
    def quit(cls) -> 'ActionItem':
        return cls("quit", Label.QUIT.value, icon=Icon.QUIT.value)

    @property
    def random(cls) -> 'ActionItem':
        return cls("random", Label.RANDOM.value, icon=Icon.RANDOM.value)


class ActionItem(MenuItem, metaclass=ActionItemMeta):
    pass


class ToggleAction(ActionItem):
    _states = ['hide', 'show']

    def toggle(self, state: bool):
        getattr(self, self._states[int(state)])()


class StatItem(ActionItem):

    prefix: str = None

    def __init__(self, title, prefix: str = None, **kwargs):
        self.prefix = prefix
        super().__init__(title, **kwargs)

    def number(self, value=None):
        if prefix:
            self.title = f"{self.prefix}: {value}"
        else:
            self.template = f"{value}"
        self.set_callback(lambda x: True)

    def relative_time(self, value=None):
        self.title = arrow.get(value).humanize(arrow.utcnow())
        self.set_callback(lambda x: True)

    def money(self, value=None):
        self.title = F"{float(value):.5f}$"
        self.set_callback(lambda x: True)

    def hashrate(self, value=None):
        value = value / 1000000
        self.title = f"{value:.3f} MH/s"
        self.set_callback(lambda x: True)


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class BarStats:
    local_hr: Optional[float] = None
    preset: Optional[str] = "default"
    remote_hr: Optional[float] = None

    @property
    def display(self):
        parts = filter(None, [
            f"{name_to_code(self.preset).upper()}",
            f"{self.local_hr:.2f}MH/s" if self.local_hr else None,
            f"{self.remote_hr:.2f}MH/s" if self.remote_hr else None,
        ])
        return " | ".join(parts)

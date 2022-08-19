from re import I
from rumps import MenuItem
from pathlib import Path
from enum import Enum


class Label(Enum):
    PLAY = 'Play'
    PAUSE = 'Pause'
    STOP = 'Stop'
    FIND = 'Find'
    RANDOM = 'Random Songs'
    ALBUM = 'Album'
    NEXT = 'Next Song'
    RESTART = 'Replay'
    QUIT = 'Quit'
    LAST_ADDED = 'Last addded'
    RECENT = 'Recently played'
    ARTIST = 'Artist'
    RESCAN = 'Rescan'
    RANDOM_ALBUM = "Random Album"
    MOST_PLAYED = 'Most played'


class Symbol(Enum):
    STOPPED = "figure.dress.line.vertical.figure"
    PLAY = 'play'
    STOP = 'stop'
    FIND = 'find.png'
    QUIT = 'power'
    RANDOM = 'dice'
    ALBUM = 'opticaldisc'
    NEXT = 'forward'
    PREVIOUS = 'backward'
    RESTART = 'gobackward'
    PLAYING = 'speaker.wave.3'
    LAST_ADDED = 'wand.and.stars'
    ARTIST = 'guitars'
    NOWPLAYING = 'speaker.wave.3'
    RECENT = 'clock.arrow.circlepath'
    PAUSE = 'pause'
    RESCAN = 'lifepreserver'
    RANDOM_ALBUM = 'die.face.5'
    MOST_PLAYED = 'arrow.clockwise.heart'
    MUTED = 'muted.png'
    WAVE1 = 'speaker.wave.1'
    WAVE2 = 'speaker.wave.2'
    WAVE3 = 'speaker.wave.3'
    WAVEFORM = "waveform"
    WAVEFORM_PATH = "waveform.path"
    GRID1 = "circle.grid.cross.left.filled"
    GRID2 = "circle.grid.cross.up.filled"
    GRID3 = "circle.grid.cross.right.filled"
    GRID4 = "circle.grid.cross.down.filled"


class Icon(Enum):

    def __new__(cls, *args):
        icons_path: Path = Path(__file__).parent / "icons"
        value = icons_path / args[0]
        obj = object.__new__(cls)
        obj._value_ = value.as_posix()
        return obj


class AnimatedIcon:

    __items: list[Symbol] = []
    __idx = 0
    __offset = 1

    def __init__(self, icons: list[Symbol]) -> None:
        self.__items = icons

    def __iter__(self):
        self.__idx = 0
        return self

    def __next__(self):
        res = self.__items[self.__idx]
        if self.__offset > 0 and self.__idx + self.__offset == len(self.__items):
            self.__offset = -1
        elif self.__idx == 0:
            self.__offset = 1

        self.__idx += self.__offset

        return res


class ProgressIcon:

    __items: list[Symbol] = []
    __idx = 0

    def __init__(self, icons: list[Symbol]) -> None:
        self.__items = icons

    def __iter__(self):
        self.__idx = 0
        return self

    def __next__(self):
        res = self.__items[self.__idx]
        self.__idx += 1
        if self.__idx == len(self.__items):
            self.__idx = 0
        return res

class ActionItemMeta(type):

    _instances = {}

    def __call__(cls, name, *args, **kwds):
        if name not in cls._instances:
            cls._instances[name] = super().__call__(*args, **kwds)
        return cls._instances[name]

    @property
    def next(cls) -> 'ActionItem':
        return cls("next", Label.NEXT.value, icon=Symbol.NEXT.value)

    @property
    def restart(cls) -> 'ActionItem':
        return cls("restart", Label.RESTART.value, icon=Symbol.RESTART.value)

    @property
    def quit(cls) -> 'ActionItem':
        return cls("quit", Label.QUIT.value, icon=Symbol.QUIT.value)

    @property
    def random(cls) -> 'ActionItem':
        return cls("random", Label.RANDOM.value, icon=Symbol.RANDOM.value)

    @property
    def random_album(cls) -> 'ActionItem':
        return cls("random_album", Label.RANDOM_ALBUM.value, icon=Symbol.RANDOM_ALBUM.value)

    @property
    def last_added(cls) -> 'ActionItem':
        return cls("newest", Label.LAST_ADDED.value, icon=Symbol.LAST_ADDED.value)

    @property
    def artist(cls) -> 'ActionItem':
        return cls("artist", Label.ARTIST.value, icon=Symbol.ARTIST.value)

    @property
    def recent(cls) -> 'ActionItem':
        return cls("recent", Label.RECENT.value, icon=Symbol.RECENT.value)

    @property
    def most_played(cls) -> 'ActionItem':
        return cls("most_played", Label.MOST_PLAYED.value, icon=Symbol.MOST_PLAYED.value)

    @property
    def rescan(cls) -> 'ActionItem':
        return cls("rescan", Label.RESCAN.value, icon=Symbol.RESCAN.value)


class ActionItem(MenuItem, metaclass=ActionItemMeta):

    def __init__(self, title, callback=None, key=None, icon=None, dimensions=None, template=None):
        template = True
        super().__init__(title, callback, key, icon, dimensions, template)

    def setAvailability(self, enabled: bool):
        self._menuitem.setEnabled_(enabled)


class MusicItem(MenuItem):

    __id = None

    def __init__(self, title, id, callback=None, key=None, icon=None, dimensions=None, template=None):
        self.__id = id
        super().__init__(title, callback=callback, key=key,
                         icon=icon, dimensions=dimensions, template=template)

    @property
    def id(self):
        return self.__id

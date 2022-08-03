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
    NEWEST = 'Last addded'
    RECENT = 'Recently played'
    ARTIST = 'Artist'
    RESCAN = 'Rescan'
    RANDOM_ALBUM = "Random Album"
    MOST_PLAYED = 'Most played'


class Icon(Enum):
    PLAY = 'play.png'
    STOP = 'stop.png'
    FIND = 'find.png'
    QUIT = 'quit.png'
    RANDOM = 'random.png'
    ALBUM = 'album.png'
    NEXT = 'next.png'
    RESTART = 'restart.png'
    PLAYING = 'playing.png'
    STOPPED = 'stopped.png'
    NEWEST = 'newest.png'
    ARTIST = 'artist.png'
    NOWPLAYING = 'nowplaying.png'
    DEFAULT_ART = 'default_art.png'
    RECENT = 'recents.png'
    PAUSE = 'pause.png'
    RESCAN = 'rescan.png'
    RANDOM_ALBUM = 'random_album.png'
    MOST_PLAYED = 'most_played.png'

    def __new__(cls, *args):
        icons_path: Path = Path(__file__).parent / "icons"
        value = icons_path / args[0]
        obj = object.__new__(cls)
        obj._value_ = value.as_posix()
        return obj


class ActionItemMeta(type):

    _instances = {}

    def __call__(cls, name, *args, **kwds):
        if name not in cls._instances:
            cls._instances[name] = super().__call__(*args, **kwds)
        return cls._instances[name]

    @property
    def next(cls) -> 'ActionItem':
        return cls("next", Label.NEXT.value, icon=Icon.NEXT.value)

    @property
    def restart(cls) -> 'ActionItem':
        return cls("restart", Label.RESTART.value, icon=Icon.RESTART.value)

    @property
    def quit(cls) -> 'ActionItem':
        return cls("quit", Label.QUIT.value, icon=Icon.QUIT.value)

    @property
    def random(cls) -> 'ActionItem':
        return cls("random", Label.RANDOM.value, icon=Icon.RANDOM.value)

    @property
    def random_album(cls) -> 'ActionItem':
        return cls("random_album", Label.RANDOM_ALBUM.value, icon=Icon.RANDOM_ALBUM.value)

    @property
    def newest(cls) -> 'ActionItem':
        return cls("newest", Label.NEWEST.value, icon=Icon.NEWEST.value)

    @property
    def artist(cls) -> 'ActionItem':
        return cls("artist", Label.ARTIST.value, icon=Icon.ARTIST.value)

    @property
    def recent(cls) -> 'ActionItem':
        return cls("recent", Label.RECENT.value, icon=Icon.RECENT.value)

    @property
    def most_played(cls) -> 'ActionItem':
        return cls("most_played", Label.MOST_PLAYED.value, icon=Icon.MOST_PLAYED.value)

    @property
    def rescan(cls) -> 'ActionItem':
        return cls("rescan", Label.RESCAN.value, icon=Icon.RESCAN.value)


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

from rumps import MenuItem
from pathlib import Path
from enum import Enum

class Label(Enum):
    PLAY = 'Play'
    STOP = 'Stop'
    FIND = 'Find'
    RANDOM = 'Random'
    ALBUM = 'Album'
    NEXT = 'Next Song'
    RESTART = 'Replay'
    QUIT = 'Quit'
    NEWEST = 'Last addded'
    RECENT = 'Recently played'
    ARTIST = 'Artist'


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
    def quit(cls) -> 'ActionItem':
        return cls("quit", Label.QUIT.value, icon=Icon.QUIT.value)

    @property
    def random(cls) -> 'ActionItem':
        return cls("random", Label.RANDOM.value, icon=Icon.RANDOM.value)

    @property
    def newest(cls) -> 'ActionItem':
        return cls("newest", Label.NEWEST.value, icon=Icon.NEWEST.value)

    @property
    def artist(cls) -> 'ActionItem':
        return cls("artist", Label.ARTIST.value, icon=Icon.ARTIST.value)

    @property
    def recent(cls) -> 'ActionItem':
        return cls("recent", Label.RECENT.value, icon=Icon.RECENT.value)


class ActionItem(MenuItem, metaclass=ActionItemMeta):

    def __init__(self, title, callback=None, key=None, icon=None, dimensions=None, template=None):
        template = True
        super().__init__(title, callback, key, icon, dimensions, template)


class MusicItem(MenuItem):

    __id = None

    def __init__(self, title, id, callback=None, key=None, icon=None, dimensions=None, template=None):
        self.__id = id
        super().__init__(title, callback=callback, key=key,
                         icon=icon, dimensions=dimensions, template=template)


    @property
    def id(self):
        return self.__id


class ToggleAction(ActionItem):
    _states = ['hide', 'show']

    def toggle(self, state: bool):
        getattr(self, self._states[int(state)])()

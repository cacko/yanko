from pathlib import Path
from enum import Enum


class Label(Enum):
    PLAY = "Play"
    PAUSE = "Pause"
    STOP = "Stop"
    FIND = "Find"
    RANDOM = "Random Songs"
    ALBUM = "Album"
    NEXT = "Next Song"
    PREVIOUS = "Previous Song"
    RESTART = "Replay"
    QUIT = "Quit"
    LAST_ADDED = "Last addded"
    RECENT = "Recently played"
    ARTIST = "Artist"
    RESCAN = "Rescan"
    RANDOM_ALBUM = "Random Album"
    MOST_PLAYED = "Most played"
    CACHE = "Image Cache"
    ADVANCED = "Advanced"


class Symbol(Enum):
    STOPPED = "speaker.zzz.fill"
    PLAY = "play"
    STOP = "stop"
    FIND = "find.png"
    QUIT = "power"
    RANDOM = "dice"
    ALBUM = "opticaldisc"
    NEXT = "forward"
    PREVIOUS = "backward"
    RESTART = "restart"
    PLAYING = "speaker.wave.3"
    LAST_ADDED = "wand.and.stars"
    ARTIST = "guitars"
    NOWPLAYING = "speaker.wave.3"
    RECENT = "clock.arrow.circlepath"
    PAUSE = "pause"
    RESCAN = "lifepreserver"
    RANDOM_ALBUM = "die.face.5"
    MOST_PLAYED = "arrow.clockwise.heart"
    MUTED = "muted.png"
    WAVE1 = "wave.1.forward"
    WAVE2 = "wave.2.forward"
    WAVE3 = "wave.3.forward"
    GRID1 = "circle.grid.2x1"
    GRID2 = "circle.grid.2x1.left.filled"
    GRID3 = "circle.grid.2x1.right.filled"
    GRID4 = "circle.grid.2x1.fill"
    VOLUME1 = "speaker.wave.1"
    VOLUME2 = "speaker.wave.2"
    VOLUME3 = "speaker.wave.3"
    CACHE = "photo"
    ADVANCED = "hammer"


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

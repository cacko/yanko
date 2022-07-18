from dataclasses import dataclass
from dataclasses_json import dataclass_json, Undefined
from yanko.sonic import Track
from rumps import Menu


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class PlaylistItem:
    track: Track
    key: str


class Playlist:

    __items: list[PlaylistItem] = []
    __menu: Menu = None

    def __init__(self, menu: Menu) -> None:
        self.__menu = Menu

    def __len__(self):
        return len(self.__items)

    def __getitem__(self, key):
        # if key is of invalid type or value, the list values will raise the error
        return self.__items[key]

    def __setitem__(self, key, value):
        self.__items[key] = value

    def __delitem__(self, key):
        del self.__items[key]

    def __iter__(self):
        return iter(self.__items)

    def __reversed__(self):
        return reversed(self.__items)

    def append(self, item: PlaylistItem):
        self.__items.append(item)

    def reset(self):
        for item in self.__items:
            self.__menu.pop(item.key)

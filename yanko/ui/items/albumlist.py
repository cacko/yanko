from dataclasses import dataclass
from dataclasses_json import dataclass_json, Undefined
from yanko.sonic import Album
from rumps import Menu, MenuItem
from yanko.ui.models import MusicItem


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class AlbumItem:
    album: Album
    key: str


class Albumlist:

    __items: list[AlbumItem] = []
    __menu: Menu = None

    def __init__(self, menu: Menu) -> None:
        self.__menu = menu

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

    def append(self, item: AlbumItem):
        self.__items.append(item)

    def update(self, albums: Album, callback):
        if len(self.__menu.keys()):
            self.__menu.clear()
        menu = []
        for album in albums:
            menu.append(MusicItem(
                f"{album.artist} 💿 {album.title}",
                id=album.id,
                callback=callback)
            )
        self.__menu.update(menu)

    def reset(self):
        for item in self.__items:
            self.__menu.pop(item.key)

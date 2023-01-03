from typing import Optional
from pydantic import BaseModel
from yanko.sonic import Track
from .actions import MusicItem
from .baseitem import Font


class PlaylistItem(BaseModel):
    key: str
    track: Optional[Track] = None


class PlaylistMenuItem(MusicItem):
    pass


class Playlist:

    __items: list[PlaylistItem] = []
    __insert_before: str
    __isAlbum = False

    def __init__(self, insert_before: str, app) -> None:
        self.__insert_before = insert_before
        self.__app = app

    def __len__(self):
        return len(self.__items)

    def __getitem__(self, key):
        # if key is of invalid type or value, the list values will raise the error
        return self.__items[key]

    def __setitem__(self, key, value):
        self.__items[key] = value

    def __delitem__(self, key):
        try:
            itm = self.__items[key]
            del self.__items[key]
            del self.__app.menu[itm.key]
        except KeyError:
            pass
        del self.__items[key]

    def __iter__(self):
        return iter(self.__items)

    def __reversed__(self):
        return reversed(self.__items)

    def append(self, item: PlaylistItem):
        self.__items.append(item)

    @property
    def insert_before(self):
        if not len(self.__items):
            return self.__insert_before
        return self.__items[0].key

    def update(self, tracks: list[Track], callback, isAlbum=False):
        menu = self.__app.menu
        self.reset()
        self.__isAlbum = isAlbum
        insert_before = self.__insert_before
        insert_after = ""
        for idx, track in enumerate(tracks):
            if insert_after:
                insert_after = menu.insert_after(
                    insert_after,
                    PlaylistMenuItem(
                        track.displayTitle(idx, isAlbum=self.__isAlbum),
                        callback=callback,
                        id=track.id,
                    ),
                )
            elif insert_before:
                insert_after = menu.insert_before(
                    insert_before,
                    PlaylistMenuItem(
                        track.displayTitle(idx, isAlbum=self.__isAlbum),
                        callback=callback,
                        id=track.id,
                    ),
                )
            self.append(PlaylistItem(track=track, key=insert_after))
        self.append(PlaylistItem(key=menu.insert_after(insert_after, None)))

    def reset(self):
        menu = self.__app.menu
        if not len(self.__items):
            return
        items = self.__items[:]
        self.__items = []
        for item in items:
            try:
                del menu[item.key]
            except KeyError:
                pass

    def setNowPlaying(self, track: Track):
        menu = self.__app.menu
        for idx, item in enumerate(self.__items):
            menu_item = menu.get(item.key)
            if isinstance(menu_item, PlaylistMenuItem) and menu_item.id:
                if menu_item.id == track.id:
                    menu_item.setAttrTitle(
                        item.track.displayTitle(idx, isAlbum=self.__isAlbum),
                        Font.BOLD,
                    )
                    menu_item.state = 1
                else:
                    menu_item.setAttrTitle(
                        item.track.displayTitle(idx, isAlbum=self.__isAlbum)
                    )
                    menu_item.state = 0

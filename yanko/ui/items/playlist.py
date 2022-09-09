from dataclasses import dataclass
from dataclasses_json import dataclass_json, Undefined
from yanko.sonic import Track
from rumps import App
from .actions import MusicItem
from Cocoa import NSFont, NSFontAttributeName
from PyObjCTools.Conversion import propertyListFromPythonCollection
from AppKit import NSAttributedString
from typing import Optional
from enum import Enum

class Font(Enum):
    REGULAR = NSFont.fontWithName_size_("MesloLGS NF", 12)
    BOLD = NSFont.fontWithName_size_("MesloLGS NF Bold", 12)


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class PlaylistItem:
    key: str
    track: Optional[Track] = None


class PlaylistMenuItem(MusicItem):

    __attributes = None

    def __init__(self, title, id, callback=None, key=None, icon=None, dimensions=None, template=None):
        super().__init__(title, id, callback, key, icon, dimensions, template)
        self.setAttrTitle()

    def string_attributes(self, font: Font):
        return propertyListFromPythonCollection({
                NSFontAttributeName: font.value,
            }, conversionHelper=lambda x: x)

    def setAttrTitle(self, title=None, font: Font = None):
        if not title:
            title = self.title
        if not font:
            font = Font.REGULAR
        tt = NSAttributedString.alloc().initWithString_attributes_(
            title, self.string_attributes(font))
        self._menuitem.setAttributedTitle_(tt)


class Playlist:

    __items: list[PlaylistItem] = []
    __app: App = None
    __insert_before: str = None
    __isAlbum = False

    def __init__(self, app: App, insert_before: str) -> None:
        self.__app = app
        self.__insert_before = insert_before

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

    def update(self, tracks: list[Track], callback, isAlbum=False):
        self.reset()
        menu = self.__app.menu
        self.__isAlbum = isAlbum
        insert_before = self.__insert_before
        insert_after = None
        for idx, track in enumerate(tracks):
            if insert_after:
                insert_after = menu.insert_after(
                    insert_after,
                    PlaylistMenuItem(
                        track.displayTitle(idx, isAlbum=self.__isAlbum),
                        callback=callback,
                        id=track.id
                    )
                )
            elif insert_before:
                insert_after = menu.insert_before(
                    insert_before,
                    PlaylistMenuItem(
                        track.displayTitle(idx, isAlbum=self.__isAlbum),
                        callback=callback,
                        id=track.id
                    )
                )
            self.append(PlaylistItem(
                track=track,
                key=insert_after
            ))
        self.append(PlaylistItem(key=menu.insert_after(insert_after, None)))

    def reset(self):
        if not len(self.__items):
            return
        menu = self.__app.menu
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
                    menu_item.setAttrTitle(f"🔈 {item.track.displayTitle(isAlbum=self.__isAlbum)}", Font.BOLD)
                else:
                    menu_item.setAttrTitle(item.track.displayTitle(idx, isAlbum=self.__isAlbum))

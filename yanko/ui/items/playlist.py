from dataclasses import dataclass
from enum import Enum
from typing import Optional

from AppKit import (
    NSAttributedString,
    NSFont,
    NSFontAttributeName,
    NSBackgroundColorAttributeName,
    NSColor
)
from dataclasses_json import Undefined, dataclass_json
from PyObjCTools.Conversion import propertyListFromPythonCollection
from rumps import App, Menu

from yanko.sonic import Track

from .actions import MusicItem


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

    def __init__(
        self,
        title,
        id,
        callback=None,
        key=None,
        icon=None,
        dimensions=None,
        template=None,
    ):
        super().__init__(title, id, callback, key, icon, dimensions, template)
        self.setAttrTitle()

    def string_attributes(self, font: Font, backgroundColor: Optional[NSColor] = None):
        if backgroundColor:
            return propertyListFromPythonCollection(
                {
                    NSFontAttributeName: font.value,
                    NSBackgroundColorAttributeName: backgroundColor
                },
                conversionHelper=lambda x: x,
            )
        return propertyListFromPythonCollection(
            {
                NSFontAttributeName: font.value,
            },
            conversionHelper=lambda x: x,
        )

    def setAttrTitle(
        self, 
        title=None, 
        font: Optional[Font] = None,
        backgroundColor: Optional[NSColor] = None
    ):
        if not title:
            title = self.title
        if not font:
            font = Font.REGULAR
        tt = NSAttributedString.alloc().initWithString_attributes_(
            title, self.string_attributes(font, backgroundColor=backgroundColor)
        )
        self._menuitem.setAttributedTitle_(tt)


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

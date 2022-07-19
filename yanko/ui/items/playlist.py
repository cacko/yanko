from dataclasses import dataclass
from dataclasses_json import dataclass_json, Undefined
from yanko.sonic import Track
from rumps import Menu
from yanko.ui.models import Icon, MusicItem
from Cocoa import NSFont, NSFontAttributeName
from PyObjCTools.Conversion import propertyListFromPythonCollection
from AppKit import NSAttributedString


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class PlaylistItem:
    track: Track
    key: str


class PlaylistMenuItem(MusicItem):

    __font: NSFont = None
    __attributes = None

    def __init__(self, title, id, callback=None, key=None, icon=None, dimensions=None, template=None):
        super().__init__(title, id, callback, key, icon, dimensions, template)
        self.setAttrTitle()

    @property
    def font(self):
        if not self.__font:
            self.__font = NSFont.fontWithName_size_("MesloLGS NF", 12)
        return self.__font

    @property
    def string_attributes(self):
        if not self.__attributes:
            self.__attributes = propertyListFromPythonCollection({
                NSFontAttributeName: self.font,
            }, conversionHelper=lambda x: x)
        return self.__attributes

    def setAttrTitle(self, title=None):
        if not title:
            title = self.title
        tt = NSAttributedString.alloc().initWithString_attributes_(
            self.title, self.string_attributes)
        self._menuitem.setAttributedTitle_(tt)


class Playlist:

    __items: list[PlaylistItem] = []
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

    def append(self, item: PlaylistItem):
        self.__items.append(item)

    def update(self, tracks: list[Track], callback):
        self.reset()
        insert_before = self.__menu.keys()[0]
        insert_after = None
        for idx, track in enumerate(tracks):
            if insert_after:
                insert_after = self.__menu.insert_after(
                    insert_after,
                    PlaylistMenuItem(
                        track.displayTitle(idx),
                        callback=callback,
                        id=track.id
                    )
                )
            elif insert_before:
                insert_after = self.__menu.insert_before(
                    insert_before,
                    PlaylistMenuItem(
                        track.displayTitle(idx),
                        callback=callback,
                        id=track.id
                    )
                )
            self.append(PlaylistItem(
                track=track,
                key=insert_after
            ))
        self.__menu.insert_after(insert_after, None)

    def reset(self):
        for item in self.__items:
            self.__menu.pop(item.key)

    def setNowPlaying(self, track: Track):
        for idx, item in enumerate(self.__items):
            menu_item = self.__menu.get(item.key)
            if isinstance(menu_item, PlaylistMenuItem):
                if menu_item.id == track.id:
                    menu_item.set_icon(Icon.NOWPLAYING.value, template=True)
                    menu_item.setAttrTitle(item.track.displayTitle())
                else:
                    menu_item.set_icon(None)
                    menu_item.setAttrTitle(item.track.displayTitle(idx))

from dataclasses import dataclass
from dataclasses_json import dataclass_json, Undefined
from yanko.sonic import Album, ArtistInfo
from rumps import Menu
from yanko.ui.models import MusicItem
from rumps import App
from AppKit import NSAttributedString
from bs4 import BeautifulSoup
from textwrap import wrap


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class AlbumItem:
    album: Album
    key: str


class ArtistInfoItem(MusicItem):
    def __init__(self, id, artist: str, info: ArtistInfo, callback=None, key=None, icon=None, dimensions=None, template=None):
        bio_bs = BeautifulSoup(info.biography, features="html.parser")
        biography = "\n".join(wrap(bio_bs.get_text(), width=50, max_lines=4))
        title = f"{artist} - {biography}"
        dimensions = [70, 70]
        icon = info.image
        super().__init__(title, id, callback, key, icon, dimensions, template)
        tt = NSAttributedString.alloc().initWithString_(
            f"{artist.upper()}\n{biography}")
        self._menuitem.setAttributedTitle_(tt)


class AlbumMenuItem(MusicItem):

    def __init__(self, album: Album, callback=None, key=None, icon=None, dimensions=None, template=None):
        title = f"{album.album} / {album.title}"
        icon = album.coverArt
        id = album.id
        dimensions = [35, 35]
        super().__init__(title, id, callback, key, icon, dimensions, template)
        tt = NSAttributedString.alloc().initWithString_(
            f"{album.artist}\n{album.title} ({album.year})")
        self._menuitem.setAttributedTitle_(tt)


class Albumlist:

    items: list[AlbumItem] = []
    app: App = None
    menu_key: str = None

    def __init__(self, app: App, menu_key: str) -> None:
        self.app = app
        self.menu_key = menu_key

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

    @property
    def menu(self) -> Menu:
        return self.app.menu.get(self.menu_key)

    def append(self, item: AlbumItem):
        self.__items.append(item)

    def update(self, albums: Album, callback):
        if len(self.menu.keys()):
            self.menu.clear()
        menu = []
        for album in albums:
            menu.append(AlbumMenuItem(album, callback=callback))
        self.menu.update(menu)
        self.menu._menuitem.setEnabled_(True)

    def reset(self):
        for item in self.__items:
            self.menu.pop(item.key)


class ArtistAlbumsList(Albumlist):

    def update(self, info: ArtistInfo, albums: Album, callback, callback_artist):
        try:
            self.menu._menu.removeAllItems()
        except AttributeError:
            pass
        self.menu.add(ArtistInfoItem(
            id=albums[0].artistId,
            artist=albums[0].artist,
            info=info,
            callback=callback_artist
        ))
        for album in albums:
            self.menu.add(AlbumMenuItem(album, callback=callback))
        self.menu._menuitem.setEnabled_(True)

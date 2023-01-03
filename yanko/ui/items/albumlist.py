from textwrap import wrap
from bs4 import BeautifulSoup
from rumps import App, Menu
from pydantic import BaseModel
from yanko.sonic import Album, ArtistInfo

from .actions import MusicItem


class AlbumItem(BaseModel):
    album: Album
    key: str


class ArtistInfoItem(MusicItem):
    def __init__(
        self,
        id,
        artist: str,
        info: ArtistInfo,
        callback=None,
        key=None,
        icon=None,
        dimensions=None,
        template=False,
    ):
        bio_bs = BeautifulSoup(info.biography, features="html.parser")  # type: ignore
        biography = "\n".join(wrap(bio_bs.get_text(), width=50, max_lines=4))
        title = f"{artist} - {biography}"
        dimensions = [70, 70]
        icon = info.image
        super().__init__(title, id, callback, key, icon, dimensions, template)
        self.setAttrTitle(f"{artist.upper()}\n{biography}")


class AlbumMenuItem(MusicItem):
    def __init__(
        self,
        album: Album,
        callback=None,
        key=None,
        icon=None,
        dimensions=None,
        template=False,
    ):
        title = f"{album.album} / {album.title}"
        icon = album.coverArt
        id = album.id
        dimensions = [35, 35]
        super().__init__(title, id, callback, key, icon, dimensions, template)
        self.setAttrTitle(f"{album.artist}\n{album.title} ({album.year})")


class Albumlist:

    items: list[AlbumItem] = []
    app: App
    menu_key: str

    def __init__(self, app: App, menu_key: str) -> None:
        self.app = app
        self.menu_key = menu_key

    def __len__(self):
        return len(self.items)

    def __getitem__(self, key):
        # if key is of invalid type or value, the list values will raise the error
        return self.items[key]

    def __setitem__(self, key, value):
        self.items[key] = value

    def __delitem__(self, key):
        del self.items[key]

    def __iter__(self):
        return iter(self.items)

    def __reversed__(self):
        return reversed(self.items)

    @property
    def menu(self) -> Menu:
        return self.app.menu.get(self.menu_key)  # type: ignore

    def append(self, item: AlbumItem):
        self.items.append(item)

    def update(self, albums: list[Album], callback):
        if len(self.menu.keys()):
            self.menu.clear()
        menu = []
        for album in albums:
            menu.append(AlbumMenuItem(album, callback=callback))
        self.menu.update(menu)
        self.menu._menuitem.setEnabled_(True)  # type: ignore

    def reset(self):
        for item in self.items:
            self.menu.pop(item.key)


class ArtistAlbumsList(Albumlist):
    def update(self, info: ArtistInfo, albums: list[Album], callback, callback_artist):
        try:
            self.menu._menu.removeAllItems()
        except AttributeError:
            pass
        self.menu.add(
            ArtistInfoItem(
                id=albums[0].artistId,
                artist=albums[0].artist,
                info=info,
                callback=callback_artist,
            )
        )
        for album in albums:
            self.menu.add(AlbumMenuItem(album, callback=callback))
        self.menu._menuitem.setEnabled_(True)  # type: ignore

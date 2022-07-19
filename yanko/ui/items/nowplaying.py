from yanko.ui.models import MusicItem
from yanko.sonic import Track, Album
from AppKit import NSAttributedString


class NowPlayingItem(MusicItem):
    __track: Track
    def __init__(self, track: Track, callback=None, key=None, icon=None, dimensions=None, template=None):
        self.__track = track
        title = f"{track.artist} - {track.title} - {track.album}"
        id = track.albumId
        dimensions = [50, 50]
        icon = track.coverArt
        super().__init__(title, id, callback, key, icon, dimensions, template)
        tt = NSAttributedString.alloc().initWithString_(f"{track.artist}\n{track.title}\n{track.album}")
        self._menuitem.setAttributedTitle_(tt)
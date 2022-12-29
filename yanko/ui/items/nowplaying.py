import logging
from .actions import MusicItem
from yanko.sonic import NowPlaying, Track
from AppKit import NSAttributedString
from Cocoa import NSFont, NSFontAttributeName  # type: ignore
from corestring import truncate_to_rows
from PyObjCTools.Conversion import propertyListFromPythonCollection
from enum import Enum


class Font(Enum):
    REGULAR = NSFont.fontWithName_size_("Atami", 14)


class NowPlayingItem(MusicItem):
    __track: Track

    def __init__(
        self,
        np: NowPlaying,
        callback=None,
        key=None,
        icon=None,
        dimensions=None,
        template=None,
    ):
        track = np.track
        self.__track = track
        title = f"{track.artist} - {track.title} - {track.album}"
        id = track.albumId
        logging.debug(track)
        dimensions = [80, 80]
        icon = track.coverArt
        super().__init__(title, id, callback, key, icon, dimensions, template)
        rows = [
            f"🎸 {track.artist}",
            f"🎤 {truncate_to_rows(track.title, 40)}",
            f"💿 {truncate_to_rows(track.album, 40)} ({track.year})",
            f"ℹ️ {track.total_time} {track.audioType.upper()} {track.bitRate}kbps / BPM:{np.display_bpm}",
        ]
        tt = NSAttributedString.alloc().initWithString_attributes_(
            "\n".join(rows), self.string_attributes(Font.REGULAR)
        )
        self._menuitem.setAttributedTitle_(tt)

    def string_attributes(self, font: Font):
        return propertyListFromPythonCollection(
            {
                NSFontAttributeName: font.value,
            },
            conversionHelper=lambda x: x,
        )

    @property
    def track(self) -> Track:
        return self.__track

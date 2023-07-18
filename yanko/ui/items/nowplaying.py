from .actions import MusicItem
from yanko.sonic import NowPlaying, Track
from corestring import truncate_to_rows


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
        dimensions = [60, 60]
        icon = track.coverArt
        super().__init__(title, id, callback, key, icon, dimensions, template)
        self.__set_title(np=np)

    def __set_title(self, np: NowPlaying):
        track = self.__track
        rows = [
            f"🎸 {track.artist}",
            f"🎤 {truncate_to_rows(track.title, 40)}",
            f"💿 {truncate_to_rows(track.album, 40)} ({track.year})",
            f"ℹ️ {track.total_time} {track.audioType.upper()} {track.bitRate}kbps / BPM:{np.display_bpm}",
        ]
        self.setAttrTitle("\n".join(rows))

    def update_bpm(self, np: NowPlaying):
        self.__set_title(np)

    @property
    def track(self) -> Track:
        return self.__track

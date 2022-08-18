from datetime import datetime, timedelta, timezone
from enum import Enum
from dataclasses import dataclass, field
from math import floor
from marshmallow import fields
from dataclasses_json import dataclass_json, Undefined, config
from typing import Optional
from yanko.core.string import truncate
from yanko.core.date import isodate_decoder, isodate_encoder
import time

RESULT_KEYS = [
    'searchResult3',
    'playlists',
    'searchResult2',
    'searchResult',
    'nowPlaying',
    'randomSongs',
    'albumList2',
    'albumList',
    'topSongs',
    'similarSongs2',
    'similarSongs',
    'albumInfo',
    'artistInfo2',
    'artistInfo',
    'song',
    'album',
    'artist',
    'artists',
    'topSongs',
    'scanStatus'
]


class Command(Enum):
    TOGGLE = 'toggle'
    PLAY = 'play'
    STOP = 'stop'
    NEXT = 'next'
    PREVIOUS = 'previous'
    VOLUME_UP = 'volume_up'
    VOLUME_DOWN = 'volume_down'
    MUTE = 'mute'
    RANDOM = 'random'
    LAST_ADDED = 'last_added'
    QUIT = 'quit'
    RESTART = 'restart'
    ALBUM = 'album'
    COVER_ART = 'cover_art'
    RECENTLY_PLAYED = 'recent'
    SONG = 'song'
    SEARCH = 'search'
    ALBUMSONG = 'albumsong'
    ARTIST = 'artist'
    ARTIST_ALBUMS = 'artist_albums'
    RANDOM_ALBUM = 'random_album'
    RESCAN = 'rescan'
    MOST_PLAYED = 'most_played'
    LOAD_LASTPLAYLIST = 'load_lastplaylist'
    PLAYLIST = 'playlist'
    CURRENT_ARTIST = 'current_artist'
    CURRENT_ALBUM = 'current_album'
    PLAY_LAST_ADDED = 'play_last_added'
    PLAY_MOST_PLAYED = 'play_most_played'


class Action(Enum):
    NEXT = 'next'
    RESTART = 'restart'
    EXIT = 'exit'
    STOP = 'stop'
    TOGGLE = 'toggle'
    PREVIOUS = 'previous'
    PAUSE = 'pause'
    RESUME = 'resumt'
    VOLUME_UP = 'vol_up'
    VOLUME_DOWN = 'vol_down'
    MUTE = 'mute'


class Status(Enum):
    PLAYING = 'playing'
    PAUSED = 'paused'
    STOPPED = 'stopped'
    LOADING = 'loadng'
    EXIT = 'exit'
    RESUMED = 'resumed'
    NEXT = 'next'
    PREVIOUS = 'previous'


class Subsonic(Enum):
    SIMILAR_SONGS2 = 'getSimilarSongs2'
    RANDOM_SONGS = 'getRandomSongs'
    MUSIC_FOLDERS = 'getMusicFolders'
    ALBUM_LIST = 'getAlbumList'
    ALBUM = 'getAlbum'
    SCROBBLE = 'scrobble'
    SEARCH3 = 'search3'
    ARTISTS = 'getArtists'
    PLAYLISTS = 'getPlaylists'
    ARTIST = 'getArtist'
    PLAYLIST = 'getPlaylist'
    DOWNLOAD = 'download'
    STREAM = 'stream'
    COVER_ART = 'getCoverArt'
    PING = 'ping'
    ARTIST_INFO = 'getArtistInfo'
    TOP_SONGS = 'getTopSongs'
    START_SCAN = 'startScan'
    GET_SCAN_STATUS = 'getScanStatus'


class AlbumType(Enum):
    NEWEST = 'newest'
    RECENT = 'recent'
    RANDOM = 'random'
    FREQUENT = 'frequent'


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class Track:
    id: str
    parent: str
    isDir: bool
    title: str
    album: str
    artist: str

    duration: int
    created: datetime = field(
        metadata=config(
            encoder=isodate_encoder,
            decoder=isodate_decoder,
            mm_field=fields.DateTime(format="iso", tzinfo=timezone.utc),
        )
    )
    size: int
    albumId: Optional[str] = None
    artistId: Optional[str] = None
    track: Optional[int] = None
    year: Optional[int] = None
    genre: Optional[str] = None
    coverArt: Optional[str] = None
    coverArtIcon: Optional[str] = None
    contentType: Optional[str] = None
    suffix: Optional[str] = None
    bitRate: Optional[int] = None
    path: Optional[str] = None
    discNumber: Optional[int] = None

    def displayTitle(self, idx=None, isAlbum=False) -> str:
        parts = [self.artist, truncate(self.title)]
        if isAlbum:
            parts = [self.title]
        if idx is None:
            return f"{' / '.join(parts)}"
        nm = idx + 1
        return f"{nm:02d}. {' / '.join(parts)}"


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class Album:
    id: str
    parent: str
    isDir: bool
    title: str
    album: str
    artist: str
    duration: int
    created: datetime = field(
        metadata=config(
            encoder=isodate_encoder,
            decoder=isodate_decoder,
            mm_field=fields.DateTime(format="iso", tzinfo=timezone.utc),
        )
    )
    artistId: Optional[str] = None
    year: Optional[int] = None
    genre: Optional[str] = None
    coverArt: Optional[str] = None
    coverArtIcon: Optional[str] = None
    songCount: Optional[int] = None


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class Artist:
    id: str
    name: str
    albumCount: Optional[int] = 0
    artistImageUrl: Optional[str] = None
    artist_info: Optional[str] = None
    coverArt: Optional[str] = None
    album: Optional[list[Album]] = None

    def __post_init__(self):
        if not self.album:
            self.album = []


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class ArtistInfo:
    biography: Optional[str] = None
    musicBrainzId: Optional[str] = None
    lastFmUrl: Optional[str] = None
    smallImageUrl: Optional[str] = None
    mediumImageUrl: Optional[str] = None
    largeImageUrl: Optional[str] = None
    image: Optional[str] = None


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class NowPlaying:
    track: Track
    start: datetime

    @property
    def total_length(self) -> str:
        td = timedelta(seconds=int(self.track.duration))
        return str(td)[2:7]

    @property
    def current_position(self) -> str:
        td = datetime.now(tz=timezone.utc) - self.start
        return str(td)[2:7]

    @property
    def menubar_title(self) -> str:
        return f"{self.track.artist} / {truncate(self.track.title)}"


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class Playlist:
    tracks: list[Track]
    start: datetime


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class AlbumPlaylist(Playlist):
    pass


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class Playstatus:
    status: Status


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class VolumeStatus:
    volume: float
    muted: bool
    timestamp: float

    @property
    def hasExpired(self):
        return floor(time.time() - self.timestamp) > 3


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class LastAdded:
    albums: list[Album]


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class RecentlyPlayed:
    albums: list[Album]


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class MostPlayed:
    albums: list[Album]


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class ArtistAlbums:
    albums: list[Album]
    artistInfo: Optional[ArtistInfo] = None


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class SearchItemIcon:
    path: str


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class SearchItem:
    uid: str
    title: str
    subtitle: str
    arg: str
    icon: Optional[SearchItemIcon] = None
    type = "file:skipcheck"


class ArtistSearchItem(SearchItem):
    pass


class AlbumSearchItem(SearchItem):
    pass


class TrackSearchItem(SearchItem):
    pass


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class Search:
    queue_id: str
    items: list[SearchItem]


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class ScanStatus:
    scanning: bool
    count: int


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class Response:
    status: Optional[str] = None
    serverVersion: Optional[str] = None
    type: Optional[str] = None
    version: Optional[str] = None
    error: Optional[dict] = None


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class Search3Response:
    artist: Optional[list[Artist]] = None
    album: Optional[list[Album]] = None
    song: Optional[list[Track]] = None

    def __post_init__(self):
        for k in ['artist', 'album', 'song']:
            if not getattr(self, k):
                setattr(self, k, [])


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class ArtistInfoResponse(Response):
    artistInfo: Optional[ArtistInfo] = None


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class ScanStatusResponse(Response):
    scanStatus: Optional[ScanStatus] = None

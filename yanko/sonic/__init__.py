from datetime import datetime, timezone
from enum import Enum
from dataclasses import dataclass, field
from marshmallow import fields
from dataclasses_json import dataclass_json, Undefined, config
from typing import Optional
from yanko.core.string import truncate
from yanko.core.date import isodate_decoder, isodate_encoder

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
    'topSongs'
]


class Command(Enum):
    PLAY = 'play'
    STOP = 'stop'
    NEXT = 'next'
    RANDOM = 'random'
    NEWEST = 'newest'
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


class Action(Enum):
    NEXT = 'n'
    RESTART = 'b'
    EXIT = 'x'
    STOP = 's'


class Status(Enum):
    PLAYING = 'playing'
    STOPPED = 'stopped'
    EXIT = 'exit'


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
    COVER_ART = 'getCoverArt'
    PING = 'ping'
    ARTIST_INFO = 'getArtistInfo'
    TOP_SONGS = 'getTopSongs'


class AlbumType(Enum):
    NEWEST = 'newest'
    RECENT = 'recent'


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

    def displayTitle(self, idx=None) -> str:
        if idx is None:
            return f"{self.artist} ∕ {truncate(self.title)}"
        nm = idx + 1
        return f"{nm:02d}. {self.artist} ∕ {truncate(self.title)}"


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


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class Playlist:
    tracks: list[Track]
    start: datetime


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class Playstatus:
    status: Status


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
    items: list[SearchItem]


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

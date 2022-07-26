from datetime import datetime, timezone
from enum import Enum
from dataclasses import dataclass, field
from marshmallow import fields
from dataclasses_json import dataclass_json, Undefined, config
from typing import Optional
from yanko.core.string import truncate


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
            encoder=datetime.isoformat,
            decoder=datetime.fromisoformat,
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
            encoder=datetime.isoformat,
            decoder=datetime.fromisoformat,
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

@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class Search:
    items: list[SearchItem]

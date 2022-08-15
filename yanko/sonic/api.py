from dataclasses import dataclass
import hashlib
import logging
from nntplib import ArticleInfo
import string
import sys
import time
from random import SystemRandom, choice
from subprocess import CalledProcessError
from yanko.core.thread import StoppableThread
from dataclasses_json import dataclass_json
from yanko.core import perftime
from ..player.miniplay import Miniplay
from ..player.base import BasePlayer
from yanko.sonic import (
    Action,
    AlbumSearchItem,
    Artist,
    ArtistAlbums,
    ArtistSearchItem,
    Command,
    MostPlayed,
    NowPlaying,
    Playstatus,
    RecentlyPlayed,
    ScanStatus,
    Search,
    Search3Response,
    SearchItemIcon,
    Track,
    Status,
    LastAdded,
    Album,
    Subsonic,
    AlbumType,
    ArtistInfo,
    RESULT_KEYS,
    TrackSearchItem,
    ScanStatusResponse
)
import requests
from queue import Queue
from datetime import datetime, timezone
from yanko.core.config import app_config
import urllib3
from urllib.parse import urlencode
from yanko.core.string import string_hash

from yanko.player.ffplay import FFPlay
from yanko.sonic.playqueue import PlayQueue
urllib3.disable_warnings()


@dataclass_json()
@dataclass()
class ApiArguments:
    u: str
    t: str
    s: str
    v: str
    c: str = "yAnKo"
    f: str = "json"


def get_scan_status(url, manager_queue: Queue):
    while True:
        time.sleep(2)
        res = requests.get(url)
        data = res.json()
        response: ScanStatusResponse = ScanStatusResponse.from_dict(
            data.get("subsonic-response"))
        status: ScanStatus = response.scanStatus
        manager_queue.put_nowait(status)
        if not status.scanning:
            break


class Client(object):
    command_queue: Queue = None
    search_queue: Queue = None
    playback_queue: Queue = None
    manager_queue: Queue = None
    __status: Status = Status.STOPPED
    playqueue: PlayQueue = None
    playidx = 0
    ffplay: BasePlayer = None
    scanning = False
    __threads = []

    BATCH_SIZE = 20

    def __init__(self, manager_queue):
        server_config = app_config.get('server', {})
        self.host = server_config.get('host')
        self.username = server_config.get('username', '')
        self.password = server_config.get('password', '')
        self.api = server_config.get('api', '1.16.0')
        self.ssl = server_config.get('ssl', False)
        self.verify_ssl = server_config.get('verify_ssl', True)

        self.search_results = []

        streaming_config = app_config.get('streaming', {})
        self.invert_random = streaming_config.get('invert_random', False)

        self.command_queue = Queue()
        input_thread = StoppableThread(target=self.add_input)
        input_thread.daemon = True
        input_thread.start()
        self.__threads.append(input_thread)

        self.search_queue = Queue()
        search_thread = StoppableThread(target=self.add_search)
        search_thread.daemon = True
        search_thread.start()
        self.__threads.append(search_thread)

        self.playback_queue = Queue()
        self.ffplay = Miniplay(self.playback_queue)
        self.manager_queue = manager_queue
        self.playqueue = PlayQueue(manager_queue)

    @property
    def api_args(self) -> dict[str, str]:
        token, salt = self.hash_password()
        return ApiArguments(
            u=self.username,
            t=token,
            s=salt,
            v=self.api
        ).to_dict()

    @property
    def status(self) -> Status:
        return self.__status

    @property
    def isPlaying(self) -> bool:
        return self.status not in [Status.STOPPED, Status.EXIT]

    @status.setter
    def status(self, val: Status):
        self.__status = val
        self.manager_queue.put_nowait(
            Playstatus(status=val)
        )
        if val == Status.RESUMED:
            self.status = Status.PLAYING

    def test_config(self):
        return self.make_request(url=self.create_url(Subsonic.PING)) is not None

    def hash_password(self):
        characters = string.ascii_uppercase + string.ascii_lowercase + string.digits
        salt = ''.join(SystemRandom().choice(characters) for i in range(9))  # noqa
        salted_password = self.password + salt
        token = hashlib.md5(salted_password.encode('utf-8')).hexdigest()
        return token, salt

    def create_url(self, endpoint: Subsonic, **kwargs):
        qs = urlencode({
            **kwargs,
            **self.api_args
        })
        return f"https://{self.host}/rest/{endpoint.value}?{qs}"

    def make_request(self, url):
        try:
            r = requests.get(url=url, verify=self.verify_ssl)
        except requests.exceptions.ConnectionError as e:
            logging.exception(e)
            sys.exit(1)

        try:
            response = r.json()
        except ValueError:
            response = {
                'subsonic-response': {
                    'error': {
                        'code': 100,
                        'message': r.text
                    },
                    'status': 'failed'
                }
            }

        subsonic_response = response.get('subsonic-response', {})
        status = subsonic_response.get('status', 'failed')

        if status == 'failed':
            error = subsonic_response.get('error', {})
            logging.error(
                f"Command failed - {error.get('code')} {error.get('message')}")
            return None

        for k, v in subsonic_response.items():
            if k in RESULT_KEYS:
                return v

        return response

    def scrobble(self, song_id):
        self.make_request(self.create_url(Subsonic.SCROBBLE, id=song_id))

    def startScan(self):
        self.make_request(self.create_url(Subsonic.START_SCAN))
        url = self.create_url(Subsonic.GET_SCAN_STATUS)
        get_status = StoppableThread(
            target=get_scan_status, args=(url, self.manager_queue))
        get_status.start()

    def search(self, query):
        with perftime("search"):
            results = self.make_request(
                self.create_url(Subsonic.SEARCH3, query=query))
            if results:
                results: Search3Response = Search3Response.from_dict(results)
                response = []
                for artist in results.artist:
                    iconUrl = self.create_url(
                        Subsonic.ARTIST_INFO, id=artist.id)
                    response.append(ArtistSearchItem(
                        uid=artist.id,
                        title=artist.name.upper(),
                        subtitle=f"Total albums: {artist.albumCount}",
                        arg=f"artist={artist.id}",
                        icon=SearchItemIcon(path=iconUrl)
                    ))
                for album in results.album:
                    iconUrl = self.create_url(
                        Subsonic.COVER_ART, id=album.id, size=200)
                    response.append(AlbumSearchItem(
                        uid=album.id,
                        title=album.title.upper(),
                        subtitle=album.artist,
                        arg=f"album={album.id}",
                        icon=SearchItemIcon(path=iconUrl)
                    ))
                for track in results.song:
                    iconUrl = self.create_url(
                        Subsonic.COVER_ART, id=track.coverArt, size=200)
                    response.append(TrackSearchItem(
                        uid=track.id,
                        title=track.title,
                        subtitle=f"{track.artist} / {track.album}",
                        arg=f"albumsong={track.albumId}/{track.id}",
                        icon=SearchItemIcon(path=iconUrl)
                    ))
                return response
        return []

    def get_artists(self):
        artists = self.make_request(url=self.create_url(Subsonic.ARTISTS))
        if artists:
            return artists.get('index', [])
        return []

    def get_album_list(self, album_type: AlbumType):
        albums = self.make_request(self.create_url(
            Subsonic.ALBUM_LIST, type=album_type.value))
        if albums:
            return albums.get('album', [])
        return []

    def get_last_added(self) -> list[Album]:
        return self.__toAlbums(self.get_album_list, AlbumType.NEWEST)

    def get_recently_played(self) -> list[Album]:
        return self.__toAlbums(self.get_album_list, AlbumType.RECENT)

    def get_most_played(self) -> list[Album]:
        return self.__toAlbums(self.get_album_list, AlbumType.FREQUENT)

    def get_top_songs(self, artist_id):
        artist_info = self.get_artist(artist_id)
        top_songs = self.make_request(
            self.create_url(Subsonic.TOP_SONGS, artist=artist_info.name)
        )
        return top_songs.get("song")

    def get_album_tracks(self, album_id):
        album_info = self.make_request(
            self.create_url(Subsonic.ALBUM, id=album_id))
        songs = album_info.get('song', [])
        return songs

    def get_artist(self, artist_id) -> Artist:
        if not artist_id:
            return
        artist_info = self.make_request(
            self.create_url(Subsonic.ARTIST, id=artist_id))
        if not artist_info:
            return
        return Artist.from_dict(artist_info)

    def get_artist_info(self, artist_id) -> ArticleInfo:
        artist_info = self.make_request(
            self.create_url(Subsonic.ARTIST_INFO, id=artist_id))
        if artist_info:
            return ArtistInfo.from_dict(
                artist_info)

    def get_artist_albums(self, artist_id) -> list[Album]:
        artist = self.get_artist(artist_id)
        albums = artist.album
        for album in albums:
            album.coverArt = self.create_url(
                Subsonic.COVER_ART, id=album.id, size=200)
        return albums

    def play_random_songs(self, fetch=True):
        if fetch:
            random_songs = self.make_request(
                self.create_url(
                    Subsonic.RANDOM_SONGS, size=self.BATCH_SIZE
                )
            )

            if not random_songs:
                return

            self.playqueue.load(random_songs.get(
                'song', []))
        for song in self.playqueue:
            playing = self.play_stream(dict(song))
            if not playing:
                return
        return self.play_random_songs(not self.playqueue.skip_to)

    def play_radio(self, radio_id, fetch=True):
        if fetch:
            similar_songs = self.make_request(self.create_url(
                Subsonic.SIMILAR_SONGS2, id=radio_id, count=self.BATCH_SIZE))
            if not similar_songs:
                return
            songs = similar_songs.get('song', [])
            self.playqueue.load(songs)
        for radio_track in self.playqueue:
            playing = self.play_stream(dict(radio_track))
            if not playing:
                return
        return self.play_radio(radio_id, not self.playqueue.skip_to)

    def play_artist(self, artist_id, fetch=True):
        if fetch:
            self.playqueue.load(self.get_top_songs(artist_id))

        for song in self.playqueue:
            playing = self.play_stream(dict(song))
            if not playing:
                return
        return self.play_artist(artist_id, not self.playqueue.skip_to)

    def play_last_added(self):
        last_added = self.get_last_added()
        self.manager_queue.put_nowait(LastAdded(albums=last_added))
        albums = list(reversed(last_added))
        while album := albums.pop():
            play_next = self.play_album(album.id, endless=len(albums) == 0)
            if not play_next:
                break

    def play_most_played(self):
        most_player = self.get_most_played()
        self.manager_queue.put_nowait(MostPlayed(albums=most_player))
        albums = list(reversed(most_player))
        while album := albums.pop():
            play_next = self.play_album(album.id, endless=len(albums) == 0)
            if not play_next:
                break

    def play_album(self, album_id, endless=True, fetch=True):
        if fetch:
            songs = self.get_album_tracks(album_id)
            self.playqueue.load(songs)

        artist_id = None

        for song in self.playqueue:
            artist_id = song.get("artistId")
            playing = self.play_stream(dict(song))
            if not playing:
                return
        if self.playqueue.skip_to:
            return self.play_album(album_id, endless=endless, fetch=True)
        return self.play_radio(artist_id)

    def play_random_album(self):
        albums = self.get_album_list(AlbumType.RANDOM)
        album = choice(albums)
        return self.play_album(album.get("id"))

    def play_playlist(self, playlist_id):
        playlist_info = self.make_request(
            self.create_url(Subsonic.PLAYLIST, id=playlist_id))
        songs = playlist_info['entry']

        playing = True

        while playing:
            for song in songs:
                if not playing:
                    return
                playing = self.play_stream(dict(song))

    def play_stream(self, track_data):
        stream_url = self.create_url(Subsonic.STREAM)
        song_id = track_data.get('id')
        if not song_id:
            return False

        self.scrobble(song_id)

        try:
            self.status = Status.PLAYING
            coverArt = track_data.get("coverArt")
            coverArtUrl = coverArt
            if coverArt:
                coverArtUrl = self.create_url(
                    Subsonic.COVER_ART,
                    id=coverArt,
                    size=200
                )
            self.manager_queue.put_nowait(
                NowPlaying(
                    start=datetime.now(tz=timezone.utc),
                    track=Track(**{**track_data, "coverArt": coverArtUrl}))
            )

            self.status = self.ffplay.play(stream_url, track_data)

            match(self.status):
                case Status.NEXT:
                    self.playqueue.next()
                case Status.PREVIOUS:
                    self.playqueue.previous()

            return self.status not in [Status.EXIT, Status.STOPPED]

        except OSError as err:
            logging.error(
                f'Could not run ffplay. Please make sure it is installed, {str(err)}'
            )
            return False
        except CalledProcessError as e:
            logging.error(
                'ffplay existed unexpectedly with the following error: {}'.format(e))
            return False

    def add_input(self):
        while True:
            if self.command_queue.empty():
                time.sleep(0.1)
                continue
            cmd, payload = self.command_queue.get_nowait()
            self.command_queue.task_done()
            match(cmd):
                case Command.RANDOM:
                    self.play_random_songs()
                case Command.PLAYLIST:
                    self.play_random_songs(fetch=False)
                case Command.RANDOM_ALBUM:
                    self.play_random_album()
                case Command.ALBUM:
                    self.play_album(payload)
                case Command.ARTIST:
                    self.play_artist(payload)
                case Command.PLAY_LAST_ADDED:
                    self.play_last_added()
                case Command.PLAY_MOST_PLAYED:
                    self.play_most_played()
                case Command.SONG:
                    self.playqueue.skip_to = payload
                case Command.SEARCH:
                    self.manager_queue.put_nowait(
                        Search(queue_id=string_hash(payload), items=self.search(payload)))

    def add_search(self):
        while True:
            if self.search_queue.empty():
                time.sleep(0.1)
                continue
            cmd, payload = self.search_queue.get_nowait()
            match(cmd):
                case Command.SEARCH:
                    self.manager_queue.put_nowait(
                        Search(queue_id=string_hash(payload), items=self.search(payload)))
                case Command.ARTIST_ALBUMS:
                    self.manager_queue.put_nowait(ArtistAlbums(
                        artistInfo=self.get_artist_info(payload),
                        albums=self.get_artist_albums(payload)))
                case Command.QUIT:
                    self.playback_queue.put_nowait(Action.EXIT)
                case Command.RESCAN:
                    self.startScan()
                case Command.TOGGLE:
                    self.togglePlay()
                case Command.RECENTLY_PLAYED:
                    self.manager_queue.put_nowait(RecentlyPlayed(
                        albums=self.get_recently_played()))
                case Command.MOST_PLAYED:
                    self.manager_queue.put_nowait(MostPlayed(
                        albums=self.get_most_played()))
                case Command.LAST_ADDED:
                    self.manager_queue.put_nowait(
                        LastAdded(albums=self.get_last_added()))
            self.search_queue.task_done()

    def exit(self):
        self.ffplay.exit()
        for th in self.__threads:
            try:
                th.stop()
            except:
                pass

    def __toAlbums(self, fnc, *args):
        return [
            Album(
                **{**data, "coverArt": self.create_url(Subsonic.COVER_ART, id=data.get("id"), size=200)})
            for data in fnc(*args)
        ]

    def togglePlay(self):
        if self.status == Status.PLAYING:
            self.playback_queue.put_nowait(Action.PAUSE)
            self.status = Status.PAUSED
        elif self.status == Status.PAUSED:
            self.playback_queue.put_nowait(Action.RESUME)
            self.status = Status.RESUMED

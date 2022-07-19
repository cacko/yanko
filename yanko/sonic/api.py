from dataclasses import dataclass
import hashlib
import logging
import os
from pathlib import Path
import string
import sys
import time
from random import SystemRandom
from subprocess import CalledProcessError, Popen
from threading import Thread
from cachable import CachableFile

from dataclasses_json import dataclass_json
from yanko.sonic import (
    Action,
    Command,
    NowPlaying,
    Playlist,
    Playstatus,
    RecentlyPlayed,
    Track,
    Status,
    LastAdded,
    Album,
    Subsonic,
    AlbumType
)
import requests
from queue import LifoQueue
from datetime import datetime, timezone
from yanko.core.config import app_config
import urllib3
from urllib.parse import urlencode
from hashlib import blake2b
from cachable.request import Request
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


class CoverArtFile(CachableFile):

    _url: str = None
    __filename: str = None

    def __init__(self, url: str) -> None:
        self._url = url

    @property
    def filename(self):
        if not self.__filename:
            h = blake2b(digest_size=20)
            h.update(self._url.encode())
            self.__filename = f"{h.hexdigest()}.png"
        return self.__filename

    @property
    def url(self):
        return self._url

    async def _init(self):
        if self.isCached:
            return
        try:
            req = Request(self.url)
            content = await req.binary
            self.storage_path.write_bytes(content.binary)
            self._struct = self.storage_path.read_bytes()
            self.tocache(self._struct)
        except Exception:
            self._path = self.DEFAULT


class Client(object):
    command_queue: LifoQueue = None
    playback_queue: LifoQueue = None
    manager_queue: LifoQueue = None
    playing: bool = False
    playqueue: list[Track] = []
    skip_to: str = None

    def __init__(self):
        server_config = app_config.get('server', {})
        self.host = server_config.get('host')
        self.username = server_config.get('username', '')
        self.password = server_config.get('password', '')
        self.api = server_config.get('api', '1.16.0')
        self.ssl = server_config.get('ssl', False)
        self.verify_ssl = server_config.get('verify_ssl', True)

        self.search_results = []

        streaming_config = app_config.get('streaming', {})
        self.format = streaming_config.get('format', 'raw')
        self.display = streaming_config.get('display', False)
        self.show_mode = streaming_config.get('show_mode', 0)
        self.invert_random = streaming_config.get('invert_random', False)
        self.command_queue = LifoQueue()
        input_thread = Thread(target=self.add_input)
        input_thread.daemon = True
        input_thread.start()
        self.playback_queue = LifoQueue()

        # remove the lock file if one exists
        if self.lock_file.is_file():
            self.lock_file.unlink()
        client_config = app_config.get('client', {})
        self.pre_exe = client_config.get('pre_exe', '')
        self.pre_exe = self.pre_exe.split(' ') if self.pre_exe != '' else []

    @property
    def lock_file(self) -> Path:
        return app_config.app_dir / "play.lock"

    @property
    def api_args(self) -> dict[str, str]:
        token, salt = self.hash_password()
        return ApiArguments(
            u=self.username,
            t=token,
            s=salt,
            v=self.api
        ).to_dict()

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

        return response

    def scrobble(self, song_id):
        self.make_request(self.create_url(Subsonic.SCROBBLE, id=song_id))

    def search(self, query):
        results = self.make_request(
            self.create_url(Subsonic.SEARCH3, query=query))
        if results:
            return results['subsonic-response'].get('searchResult3', [])
        return []

    def get_artists(self):
        artists = self.make_request(url=self.create_url(Subsonic.ARTISTS))
        if artists:
            return artists['subsonic-response']['artists'].get('index', [])
        return []

    def get_album_list(self, album_type: AlbumType):
        albums = self.make_request(self.create_url(
            Subsonic.ALBUM_LIST, type=album_type.value))
        if albums:
            return albums['subsonic-response']['albumList'].get('album', [])
        return []

    def get_last_added(self):
        return self.get_album_list(AlbumType.NEWEST)

    def get_recently_played(self):
        return self.get_album_list(AlbumType.RECENT)

    def get_playlists(self):
        playlists = self.make_request(url=self.create_url(Subsonic.PLAYLISTS))
        if playlists:
            return playlists['subsonic-response']['playlists'].get('playlist', [])
        return []

    def get_music_folders(self):
        music_folders = self.make_request(
            url=self.create_url(Subsonic.MUSIC_FOLDERS))
        if music_folders:
            return music_folders['subsonic-response']['musicFolders'].get('musicFolder', [])
        return []

    def get_album_tracks(self, album_id):
        album_info = self.make_request(
            self.create_url(Subsonic.ALBUM, id=album_id))
        songs = []

        for song in album_info['subsonic-response']['album'].get('song', []):
            songs.append(song)

        return songs

    def play_random_songs(self, music_folder):
        url = self.create_url(Subsonic.RANDOM_SONGS)

        if music_folder is not None:
            url = '{}&musicFolderId={}'.format(url, music_folder)

        playing = True

        while playing:
            songs = []
            if not self.skip_to:
                random_songs = self.make_request(url)

                if not random_songs:
                    return

                songs = random_songs['subsonic-response']['randomSongs'].get(
                    'song', [])


                self.manager_queue.put_nowait(
                    Playlist(
                        start=datetime.now(tz=timezone.utc),
                        tracks=[Track(**data) for data in songs]
                    )
                )

            for random_song in songs:
                if not playing:
                    return
                if self.skip_to:
                    if self.skip_to != random_song.get("id"):
                        continue
                    else:
                        self.skip_to = None
                playing = self.play_stream(dict(random_song))

    def play_radio(self, radio_id):
        playing = True
        while playing:
            similar_songs = self.make_request(self.create_url(
                Subsonic.SIMILAR_SONGS2, id=radio_id))

            if not similar_songs:
                return

            for radio_track in similar_songs['subsonic-response']['similarSongs2'].get('song', []):
                if not playing:
                    return
                playing = self.play_stream(dict(radio_track))

    def play_artist(self, artist_id):
        artist_info = self.make_request(
            self.create_url(Subsonic.ARTIST, id=artist_id))
        songs = []

        for album in artist_info['subsonic-response']['artist']['album']:
            songs += self.get_album_tracks(album.get('id'))

        playing = True

        while playing:
            for song in songs:
                if not playing:
                    return
                playing = self.play_stream(dict(song))

    def play_album(self, album_id):
        songs = self.get_album_tracks(album_id)
        playing = True

        self.manager_queue.put_nowait(
            Playlist(
                start=datetime.now(tz=timezone.utc),
                tracks=[Track(**data) for data in songs]
            )
        )

        while playing:
            for song in songs:
                if not playing:
                    return
                if self.skip_to:
                    if self.skip_to != song.get("id"):
                        continue
                    else:
                        self.skip_to = None
                playing = self.play_stream(dict(song))
                if self.skip_to:
                    break

    def play_playlist(self, playlist_id):
        playlist_info = self.make_request(
            self.create_url(Subsonic.PLAYLIST, id=playlist_id))
        songs = playlist_info['subsonic-response']['playlist']['entry']

        playing = True

        while playing:
            for song in songs:
                if not playing:
                    return
                playing = self.play_stream(dict(song))

    @property
    def environment(self):
        return dict(
            os.environ,
            PATH=f"{os.environ.get('HOME')}/.local/bin:/usr/bin:/usr/local/bin:{os.environ.get('PATH')}",
        )

    def play_stream(self, track_data):
        stream_url = self.create_url(Subsonic.DOWNLOAD)
        song_id = track_data.get('id')

        if not song_id:
            return False

        self.scrobble(song_id)

        params = [
            'ffplay',
            '-i',
            '{}&id={}&format={}'.format(stream_url, song_id, self.format),
            '-showmode',
            '{}'.format(self.show_mode),
            '-window_title',
            '{} by {}'.format(
                track_data.get('title', ''),
                track_data.get('artist', '')
            ),
            '-autoexit',
            '-hide_banner',
            '-x',
            '500',
            '-y',
            '500',
            '-loglevel',
            'fatal',
            '-infbuf',
        ]

        params = self.pre_exe + params if len(self.pre_exe) > 0 else params

        if not self.display:
            params += ['-nodisp']

        try:
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
            self.manager_queue.put_nowait(
                Playstatus(status=Status.PLAYING)
            )

            ffplay = Popen(params, env=self.environment)

            has_finished = None
            self.playing = True
            self.lock_file.open("w+").close()

            while has_finished is None:
                has_finished = ffplay.poll()
                if self.playback_queue.empty():
                    time.sleep(0.1)
                    continue

                command = self.playback_queue.get_nowait()
                self.playback_queue.task_done()

                match (command):
                    case Action.EXIT:
                        return self.__exit(ffplay)
                    case Action.RESTART:
                        return self.__restart(ffplay, track_data)
                    case Action.NEXT:
                        return self.__next(ffplay)
                    case Action.STOP:
                        return self.__stop(ffplay)

            self.lock_file.unlink(missing_ok=True)
            return True

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
            match(cmd):
                case Command.RANDOM:
                    self.play_random_songs(None)
                case Command.ALBUM:
                    self.play_album(payload)
                case Command.RECENTLY_PLAYED:
                    self.manager_queue.put_nowait(RecentlyPlayed(
                        albums=self.__toAlbums(self.get_recently_played)))
                case Command.NEWEST:
                    self.manager_queue.put_nowait(
                        LastAdded(albums=self.__toAlbums(self.get_last_added)))
                case Command.SONG:
                    self.skip_to = payload

            self.command_queue.task_done()

    def __toAlbums(self, fnc):
        return [
            Album(
                **{**data, "coverArt": self.create_url(Subsonic.COVER_ART, id=data.get("id"), size=200)})
            for data in fnc()
        ]

    def __exit(self, ffplay):
        self.lock_file.unlink(missing_ok=True)
        ffplay.terminate()
        self.manager_queue.put_nowait(
            Playstatus(status=Status.EXIT))
        self.playing = False
        return False

    def __stop(self, ffplay):
        self.lock_file.unlink(missing_ok=True)
        ffplay.terminate()
        self.manager_queue.put_nowait(
            Playstatus(status=Status.STOPPED))
        self.playing = False
        return False

    def __restart(self, ffplay, track_data):
        self.lock_file.unlink(missing_ok=True)
        ffplay.terminate()
        self.manager_queue.put_nowait(
            Playstatus(status=Status.STOPPED))
        self.playing = False
        return self.play_stream(track_data)

    def __next(self, ffplay):
        self.lock_file.unlink(missing_ok=True)
        ffplay.terminate()
        self.manager_queue.put_nowait(
            Playstatus(status=Status.STOPPED))
        self.playing = False
        return True

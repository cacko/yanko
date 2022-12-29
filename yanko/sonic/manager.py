from pathlib import Path
from queue import Queue
from yanko.core import perftime
from yanko.core.thread import StoppableThread
from yanko.sonic import (
    Action,
    ArtistAlbums,
    ArtistSearchItem,
    Command,
    MostPlayed,
    NowPlaying,
    Playstatus,
    LastAdded,
    Search,
    Status,
    RecentlyPlayed,
    ArtistInfo as ArtistInfoData,
    VolumeStatus,
)
from yanko.sonic.announce import Announce
from yanko.sonic.api import Client
from yanko.sonic.coverart import CoverArtFile
from yanko.sonic.artist import ArtistInfo
from multiprocessing.pool import ThreadPool
import logging
import time as _time


def resolveCoverArt(obj):
    ca = CoverArtFile(obj.coverArt)
    res: Path = ca.path
    obj.coverArt = res.as_posix() if res.exists() else None
    icon: Path = ca.icon_path
    if icon:
        obj.coverArtIcon = icon.as_posix()
    else:
        obj.coverArtIcob = None
    return obj


def resolveArtistImage(obj: ArtistInfoData):
    ca = CoverArtFile(obj.largeImageUrl)
    res: Path = ca.path
    obj.image = res.as_posix() if res.exists() else None
    return obj


def resolveIcon(obj):
    if isinstance(obj, ArtistSearchItem):
        url = obj.icon.path
        ai = ArtistInfo(url)
        info: ArtistInfoData = ai.info
        if info:
            obj.icon.path = info.largeImageUrl
    ca = CoverArtFile(obj.icon.path)
    res: Path = ca.path
    obj.icon.path = res.as_posix() if res.exists() else None
    return obj


def find_idx_by_id(items, item, k="id"):
    for idx, itm in enumerate(items):
        if getattr(itm, k) == getattr(item, k):
            return idx


def resolveSearch(items):
    with ThreadPool(10) as pool:
        jobs = pool.map(resolveIcon, items)
        for res in jobs:
            try:
                items[find_idx_by_id(items, res, "uid")] = res
            except Exception as e:
                logging.error(e, exc_info=True)
        pool.close()
        pool.join()
    return items


def resolveAlbums(albums):
    with perftime("resolve albums"):
        with ThreadPool(10) as pool:
            jobs = pool.map(resolveCoverArt, albums)
            for res in jobs:
                try:
                    albums[find_idx_by_id(albums, res)] = res
                except Exception as e:
                    logging.error(e, exc_info=True)
            pool.close()
            pool.join()
        return albums


class ManagerMeta(type):

    _instance = None

    def __call__(self, *args, **kwds):
        if not self._instance:
            self._instance = super().__call__(*args, **kwds)
        return self._instance


class Manager(StoppableThread, metaclass=ManagerMeta):

    commander: Queue
    alfred: Queue
    api: Client
    playing_now: NowPlaying
    __ui_queue: Queue

    def __init__(self, ui_queue, time_event) -> None:
        self.__ui_queue = ui_queue
        self.commander = Queue()
        self.api = Client(
            self.commander,
            time_event,
        )
        super().__init__()


    def run(self):
        while not self.stopped():
            cmd, payload = self.commander.get()
            match (cmd):
                case Command.TOGGLE:
                    self.__toggle()
                case Command.STOP:
                    self.__stop()
                case Command.RANDOM:
                    self.__random()
                case Command.RANDOM_ALBUM:
                    self.__random_album()
                case Command.QUIT:
                    self.__quit()
                case Command.NEXT:
                    self.__next()
                case Command.PREVIOUS:
                    self.__previous()
                case Command.VOLUME_UP:
                    self.__volume_up()
                case Command.VOLUME_DOWN:
                    self.__volume_down()
                case Command.MUTE:
                    self.__mute()
                case Command.RESTART:
                    self.__restart()
                case Command.LAST_ADDED:
                    self.__newest()
                case Command.RECENTLY_PLAYED:
                    self.__recently_played()
                case Command.MOST_PLAYED:
                    self.__most_played()
                case Command.ALBUM:
                    self.__album(payload)
                case Command.ARTIST:
                    self.__artist(payload)
                case Command.SONG:
                    self.__song(payload)
                case Command.SEARCH:
                    self.__search(payload)
                case Command.ALBUMSONG:
                    self.__albumsong(*payload.split("/"))
                case Command.ARTIST_ALBUMS:
                    self.__artist_albums(payload)
                case Command.RESCAN:
                    self.__rescan()
                case Command.CURRENT_ALBUM:
                    self.__current_album()
                case Command.CURRENT_ARTIST:
                    self.__current_artist()
                case Command.PLAY_LAST_ADDED:
                    self.__play_last_added()
                case Command.PLAY_MOST_PLAYED:
                    self.__play_most_played()
                case Command.ANNOUNCE:
                    Announce.announce(payload)
                case Command.PLAYER_RESPONSE:
                    self.player_processor(payload)
            self.commander.task_done()

    def player_processor(self, cmd):
        if isinstance(cmd, Playstatus):
            if cmd == Status.EXIT:
                self.stop()
        elif isinstance(cmd, NowPlaying) and cmd.track.coverArt:
            cmd.track = resolveCoverArt(cmd.track)
            Announce.announce(cmd.track)
            self.playing_now = cmd
        elif isinstance(cmd, Search) and len(cmd.items):
            cmd.items = resolveSearch(cmd.items)
        elif isinstance(cmd, LastAdded):
            cmd.albums = resolveAlbums(cmd.albums)
        elif isinstance(cmd, RecentlyPlayed):
            cmd.albums = resolveAlbums(cmd.albums)
        elif isinstance(cmd, MostPlayed):
            cmd.albums = resolveAlbums(cmd.albums)
        elif isinstance(cmd, ArtistAlbums):
            cmd.artistInfo = resolveArtistImage(cmd.artistInfo)
            cmd.albums = resolveAlbums(cmd.albums)
        self.__ui_queue.put_nowait(cmd)

    def __random(self):
        if self.api.isPlaying:
            self.api.playback_queue.put_nowait(Action.STOP)
        self.api.playqueue.skip_to = None
        self.api.command_queue.put_nowait((Command.RANDOM, None))

    def __random_album(self):
        if self.api.isPlaying:
            self.api.playback_queue.put_nowait(Action.STOP)
        self.api.playqueue.skip_to = None
        self.api.command_queue.put_nowait((Command.RANDOM_ALBUM, None))

    def __toggle(self):
        if self.api.isPlaying:
            self.api.search_queue.put_nowait((Command.TOGGLE, None))
        else:
            self.api.command_queue.put_nowait((Command.PLAYLIST, None))

    def __rescan(self):
        self.api.search_queue.put_nowait((Command.RESCAN, None))

    def __newest(self):
        self.api.search_queue.put_nowait((Command.LAST_ADDED, None))

    def __recently_played(self):
        self.api.search_queue.put_nowait((Command.RECENTLY_PLAYED, None))

    def __most_played(self):
        self.api.search_queue.put_nowait((Command.MOST_PLAYED, None))

    def __search(self, query):
        self.api.search_queue.put_nowait((Command.SEARCH, query))

    def __artist_albums(self, query):
        if query:
            self.api.search_queue.put_nowait((Command.ARTIST_ALBUMS, query))

    def __album(self, albumId):
        self.api.playqueue.skip_to = None
        if self.api.isPlaying:
            self.api.playback_queue.put_nowait(Action.STOP)
        self.api.command_queue.put_nowait((Command.ALBUM, albumId))

    def __current_album(self):
        if self.playing_now:
            return self.__album(self.playing_now.track.albumId)

    def __play_last_added(self):
        self.api.playqueue.skip_to = None
        if self.api.isPlaying:
            self.api.playback_queue.put_nowait(Action.STOP)
        self.api.command_queue.put_nowait((Command.PLAY_LAST_ADDED, None))

    def __play_most_played(self):
        self.api.playqueue.skip_to = None
        if self.api.isPlaying:
            self.api.playback_queue.put_nowait(Action.STOP)
        self.api.command_queue.put_nowait((Command.PLAY_MOST_PLAYED, None))

    def __artist(self, artistId):
        self.api.playqueue.skip_to = None
        if self.api.isPlaying:
            self.api.playback_queue.put_nowait(Action.STOP)
        self.api.command_queue.put_nowait((Command.ARTIST, artistId))

    def __current_artist(self):
        if self.playing_now:
            return self.__artist(self.playing_now.track.artistId)

    def __albumsong(self, albumId, songId):
        self.api.playqueue.skip_to = songId
        if self.api.isPlaying:
            self.api.playback_queue.put_nowait(Action.STOP)
        self.api.command_queue.put_nowait((Command.ALBUM, albumId))

    def __song(self, songId):
        self.api.playqueue.skip_to = songId
        if self.api.isPlaying:
            self.api.playback_queue.put_nowait(Action.NEXT)
        else:
            self.api.command_queue.put_nowait((Command.PLAYLIST, None))

    def __quit(self):
        if self.api.isPlaying:
            self.api.playback_queue.put_nowait(Action.EXIT)
        self.commander.put_nowait(
            (Command.PLAYER_RESPONSE, Playstatus(status=Status.EXIT))
        )

    def __stop(self):
        self.api.playback_queue.put_nowait(Action.STOP)

    def __volume_up(self):
        if self.api.isPlaying:
            self.api.playback_queue.put_nowait(Action.VOLUME_UP)

    def __volume_down(self):
        if self.api.isPlaying:
            self.api.playback_queue.put_nowait(Action.VOLUME_DOWN)

    def __mute(self):
        if self.api.isPlaying:
            self.api.playback_queue.put_nowait(Action.MUTE)

    def __next(self):
        self.api.playqueue.skip_to = None
        if self.api.isPlaying:
            self.api.playback_queue.put_nowait(Action.NEXT)
        else:
            self.api.command_queue.put_nowait((Command.PLAYLIST, None))

    def __previous(self):
        if self.api.isPlaying:
            self.api.playback_queue.put_nowait(Action.PREVIOUS)
        else:
            self.api.command_queue.put_nowait((Command.PLAYLIST, None))

    def __restart(self):
        self.api.playback_queue.put_nowait(Action.RESTART)

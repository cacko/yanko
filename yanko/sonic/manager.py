import logging
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
    ArtistInfo as ArtistInfoData
)
from yanko.sonic.announce import Announce
from yanko.sonic.api import Client
from yanko.sonic.coverart import CoverArtFile
from yanko.sonic.artist import ArtistInfo
import asyncio
from multiprocessing.pool import ThreadPool


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


def find_idx_by_id(items, item, k='id'):
    for idx, itm in enumerate(items):
        if getattr(itm, k) == getattr(item, k):
            return idx


def resolveSearch(items):
    with ThreadPool(10) as pool:
        jobs = pool.map(resolveIcon, items)
        for res in jobs:
            try:
                items[find_idx_by_id(items, res, 'uid')] = res
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

    commander: Queue = None
    alfred: Queue = None
    eventLoop: asyncio.AbstractEventLoop = None
    api = None
    player_queue: Queue = None
    announce_queue: Queue = None
    playing_now: NowPlaying = None
    __ui_queue: Queue = None

    def __init__(self, ui_queue, time_event) -> None:
        self.__ui_queue = ui_queue
        self.eventLoop = asyncio.new_event_loop()
        self.commander = Queue()
        self.player_queue = Queue()
        self.api = Client(self.player_queue, time_event)
        self.announce_queue = Queue()
        super().__init__()

    def run(self):
        tasks = asyncio.wait(
            [self.command_processor(), self.player_processor(), self.announce_processor()])
        self.eventLoop.run_until_complete(tasks)

    async def command_processor(self):
        while not self.stopped():
            if self.commander.empty():
                await asyncio.sleep(0.1)
                continue
            await self.commander_runner()

    async def announce_processor(self):
        while not self.stopped():
            if self.announce_queue.empty():
                await asyncio.sleep(0.1)
                continue
            await self.announce_runner()

    async def player_processor(self):
        while not self.stopped():
            if self.player_queue.empty():
                await asyncio.sleep(0.1)
                continue
            await self.player_runner()

    async def commander_runner(self):
        try:
            cmd, payload = self.commander.get_nowait()
            self.commander.task_done()
            match(cmd):
                case Command.TOGGLE:
                    await self.__toggle()
                case Command.STOP:
                    await self.__stop()
                case Command.RANDOM:
                    await self.__random()
                case Command.RANDOM_ALBUM:
                    await self.__random_album()
                case Command.QUIT:
                    await self.__quit()
                case Command.NEXT:
                    await self.__next()
                case Command.PREVIOUS:
                    await self.__previous()
                case Command.VOLUME_UP:
                    await self.__volume_up()
                case Command.VOLUME_DOWN:
                    await self.__volume_down()
                case Command.MUTE:
                    await self.__mute()
                case Command.RESTART:
                    await self.__restart()
                case Command.LAST_ADDED:
                    await self.__newest()
                case Command.RECENTLY_PLAYED:
                    await self.__recently_played()
                case Command.MOST_PLAYED:
                    await self.__most_played()
                case Command.ALBUM:
                    await self.__album(payload)
                case Command.ARTIST:
                    await self.__artist(payload)
                case Command.SONG:
                    await self.__song(payload)
                case Command.SEARCH:
                    await self.__search(payload)
                case Command.ALBUMSONG:
                    await self.__albumsong(*payload.split('/'))
                case Command.ARTIST_ALBUMS:
                    await self.__artist_albums(payload)
                case Command.RESCAN:
                    await self.__rescan()
                case Command.CURRENT_ALBUM:
                    await self.__current_album()
                case Command.CURRENT_ARTIST:
                    await self.__current_artist()
                case Command.PLAY_LAST_ADDED:
                    await self.__play_last_added()
                case Command.PLAY_MOST_PLAYED:
                    await self.__play_most_played()
        except Exception as e:
            logging.exception(e)

    async def player_runner(self):
        try:
            cmd = self.player_queue.get_nowait()
            if isinstance(cmd, Playstatus):
                if cmd == Status.EXIT:
                    self.stop()
            elif isinstance(cmd, NowPlaying) and cmd.track.coverArt:
                cmd.track = resolveCoverArt(cmd.track)
                self.announce_queue.put_nowait(cmd.track)
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
            self.player_queue.task_done()
        except Exception as e:
            logging.exception(e)

    async def announce_runner(self):
        payload = self.announce_queue.get_nowait()
        Announce.announce(payload)
        self.announce_queue.task_done()

    async def __random(self):
        if self.api.isPlaying:
            self.api.playback_queue.put_nowait(Action.STOP)
        self.api.command_queue.put_nowait((Command.RANDOM, None))

    async def __random_album(self):
        if self.api.isPlaying:
            self.api.playback_queue.put_nowait(Action.STOP)
        self.api.command_queue.put_nowait((Command.RANDOM_ALBUM, None))

    async def __toggle(self):
        if self.api.isPlaying:
            self.api.search_queue.put_nowait((Command.TOGGLE, None))
        else:
            self.api.command_queue.put_nowait((Command.PLAYLIST, None))

    async def __rescan(self):
        self.api.search_queue.put_nowait((Command.RESCAN, None))

    async def __newest(self):
        self.api.search_queue.put_nowait((Command.LAST_ADDED, None))

    async def __recently_played(self):
        self.api.search_queue.put_nowait((Command.RECENTLY_PLAYED, None))

    async def __most_played(self):
        self.api.search_queue.put_nowait((Command.MOST_PLAYED, None))

    async def __search(self, query):
        self.api.search_queue.put_nowait((Command.SEARCH, query))

    async def __artist_albums(self, query):
        if query:
            self.api.search_queue.put_nowait((Command.ARTIST_ALBUMS, query))

    async def __album(self, albumId):
        if self.api.isPlaying:
            self.api.playback_queue.put_nowait(Action.STOP)
        self.api.command_queue.put_nowait((Command.ALBUM, albumId))

    async def __current_album(self):
        if self.playing_now:
            return await self.__album(self.playing_now.track.albumId)

    async def __play_last_added(self):
        if self.api.isPlaying:
            self.api.playback_queue.put_nowait(Action.STOP)
        self.api.command_queue.put_nowait((Command.PLAY_LAST_ADDED, None))

    async def __play_most_played(self):
        if self.api.isPlaying:
            self.api.playback_queue.put_nowait(Action.STOP)
        self.api.command_queue.put_nowait((Command.PLAY_MOST_PLAYED, None))

    async def __artist(self, artistId):
        if self.api.isPlaying:
            self.api.playback_queue.put_nowait(Action.STOP)
        self.api.command_queue.put_nowait((Command.ARTIST, artistId))

    async def __current_artist(self):
        if self.playing_now:
            return await self.__artist(self.playing_now.track.artistId)

    async def __albumsong(self, albumId, songId):
        self.api.playqueue.skip_to = songId
        if self.api.isPlaying:
            self.api.playback_queue.put_nowait(Action.STOP)
        self.api.command_queue.put_nowait((Command.ALBUM, albumId))

    async def __song(self, songId):
        self.api.playqueue.skip_to = songId
        if self.api.isPlaying:
            self.api.playback_queue.put_nowait(Action.NEXT)
        else:
            self.api.command_queue.put_nowait((Command.PLAYLIST, None))

    async def __quit(self):
        if self.api.isPlaying:
            self.api.playback_queue.put_nowait(Action.EXIT)
        self.player_queue.put_nowait(Playstatus(status=Status.EXIT))

    async def __stop(self):
        self.api.playback_queue.put_nowait(Action.STOP)

    async def __volume_up(self):
        if self.api.isPlaying:
            self.api.playback_queue.put_nowait(Action.VOLUME_UP)

    async def __volume_down(self):
        if self.api.isPlaying:
            self.api.playback_queue.put_nowait(Action.VOLUME_DOWN)

    async def __mute(self):
        if self.api.isPlaying:
            self.api.playback_queue.put_nowait(Action.MUTE)

    async def __next(self):
        self.api.playqueue.skip_to = None
        if self.api.isPlaying:
            self.api.playback_queue.put_nowait(Action.NEXT)
        else:
            self.api.command_queue.put_nowait((Command.PLAYLIST, None))

    async def __previous(self):
        if self.api.isPlaying:
            self.api.playback_queue.put_nowait(Action.PREVIOUS)
        else:
            self.api.command_queue.put_nowait((Command.PLAYLIST, None))

    async def __restart(self):
        self.api.playback_queue.put_nowait(Action.RESTART)

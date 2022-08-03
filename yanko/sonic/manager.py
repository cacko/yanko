import logging
from pathlib import Path
from queue import LifoQueue
from yanko.core import perftime
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
from yanko.sonic.api import Client
from yanko.sonic.coverart import CoverArtFile
from yanko.sonic.artist import ArtistInfo
import asyncio
from multiprocessing.pool import ThreadPool
from itertools import repeat


def run_async(args):
    fn, obj = args
    loop = asyncio.new_event_loop()
    task = fn(obj)
    res = loop.run_until_complete(task)
    return res


async def resolveCoverArt(obj):
    ca = CoverArtFile(obj.coverArt)
    res: Path = await ca.path
    obj.coverArt = res.as_posix() if res.exists() else None
    icon: Path = await ca.icon_path
    if icon:
        obj.coverArtIcon = icon.as_posix()
    else:
        obj.coverArtIcob = None
    return obj


async def resolveArtistImage(obj: ArtistInfoData):
    ca = CoverArtFile(obj.largeImageUrl)
    res: Path = await ca.path
    obj.image = res.as_posix() if res.exists() else None
    return obj


async def resolveIcon(obj):
    if isinstance(obj, ArtistSearchItem):
        url = obj.icon.path
        ai = ArtistInfo(url)
        info: ArtistInfoData = await ai.info
        if info:
            obj.icon.path = info.largeImageUrl
    ca = CoverArtFile(obj.icon.path)
    res: Path = await ca.path
    obj.icon.path = res.as_posix() if res.exists() else None
    return obj


def find_idx_by_id(items, item, k='id'):
    for idx, itm in enumerate(items):
        if getattr(itm, k) == getattr(item, k):
            return idx


async def resolveSearch(items):
    with ThreadPool(10) as pool:
        jobs = pool.map(run_async, zip(repeat(resolveIcon, len(items)), items))
        for res in jobs:
            try:
                items[find_idx_by_id(items, res, 'uid')] = res
            except Exception as e:
                logging.error(e, exc_info=True)
        pool.close()
        pool.join()
    return items


async def resolveAlbums(albums):
    with perftime("resolve albums"):
        with ThreadPool(10) as pool:
            jobs = pool.map(run_async, zip(
                repeat(resolveCoverArt, len(albums)), albums))
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


class Manager(object, metaclass=ManagerMeta):

    commander: LifoQueue = None
    alfred: LifoQueue = None
    eventLoop: asyncio.AbstractEventLoop = None
    manager_callback = None
    player_callback = None
    api = None
    __running = False
    player_queue: LifoQueue = None

    def __init__(self) -> None:
        self.eventLoop = asyncio.new_event_loop()
        self.commander = LifoQueue()
        self.api = Client()
        self.player_queue = LifoQueue()
        self.api.manager_queue = self.player_queue

    def start(self, manager_callback, player_callback):
        self.manager_callback = manager_callback
        self.player_callback = player_callback
        self.__running = True
        tasks = asyncio.wait(
            [self.command_processor(), self.player_processor()])
        self.eventLoop.run_until_complete(tasks)

    async def command_processor(self):
        while self.__running:
            if self.commander.empty():
                await asyncio.sleep(0.1)
                continue
            await self.commander_runner()

    async def player_processor(self):
        while self.__running:
            if self.player_queue.empty():
                await asyncio.sleep(0.1)
                continue
            await self.player_runner()

    async def commander_runner(self):
        try:
            cmd, payload = self.commander.get_nowait()
            match(cmd):
                case Command.TOGGLE:
                    await self.__toggle()
                case Command.RANDOM:
                    await self.__random()
                case Command.RANDOM_ALBUM:
                    await self.__random_album()
                case Command.QUIT:
                    await self.__quit()
                case Command.NEXT:
                    await self.__next()
                case Command.RESTART:
                    await self.__restart()
                case Command.NEWEST:
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
            self.commander.task_done()
        except Exception as e:
            logging.exception(e)

    async def player_runner(self):
        try:
            cmd = self.player_queue.get_nowait()
            if isinstance(cmd, Playstatus):
                if cmd == Status.EXIT:
                    self.__running = False
            elif isinstance(cmd, NowPlaying) and cmd.track.coverArt:
                cmd.track = await resolveCoverArt(cmd.track)
            elif isinstance(cmd, Search) and len(cmd.items):
                cmd.items = await resolveSearch(cmd.items)
            elif isinstance(cmd, LastAdded):
                cmd.albums = await resolveAlbums(cmd.albums)
            elif isinstance(cmd, RecentlyPlayed):
                cmd.albums = await resolveAlbums(cmd.albums)
            elif isinstance(cmd, MostPlayed):
                cmd.albums = await resolveAlbums(cmd.albums)
            elif isinstance(cmd, ArtistAlbums):
                cmd.artistInfo = await resolveArtistImage(cmd.artistInfo)
                cmd.albums = await resolveAlbums(cmd.albums)
            self.player_callback(cmd)
            self.player_queue.task_done()
        except Exception as e:
            logging.exception(e)

    async def __random(self):
        if self.api.status != Status.STOPPED:
            self.api.playback_queue.put_nowait(Action.STOP)
        self.api.command_queue.put_nowait((Command.RANDOM, None))

    async def __random_album(self):
        if self.api.status != Status.STOPPED:
            self.api.playback_queue.put_nowait(Action.STOP)
        self.api.command_queue.put_nowait((Command.RANDOM_ALBUM, None))

    async def __toggle(self):
        self.api.search_queue.put_nowait((Command.TOGGLE, None))     

    async def __rescan(self):
        self.api.search_queue.put_nowait((Command.RESCAN, None))

    async def __newest(self):
        self.api.search_queue.put_nowait((Command.NEWEST, None))

    async def __recently_played(self):
        self.api.search_queue.put_nowait((Command.RECENTLY_PLAYED, None))

    async def __most_played(self):
        self.api.search_queue.put_nowait((Command.MOST_PLAYED, None))

    async def __search(self, query):
        self.api.search_queue.put_nowait((Command.SEARCH, query))

    async def __artist_albums(self, query):
        self.api.search_queue.put_nowait((Command.ARTIST_ALBUMS, query))

    async def __album(self, albumId):
        if self.api.status != Status.STOPPED:
            self.api.playback_queue.put_nowait(Action.STOP)
        self.api.command_queue.put_nowait((Command.ALBUM, albumId))

    async def __artist(self, artistId):
        if self.api.status != Status.STOPPED:
            self.api.playback_queue.put_nowait(Action.STOP)
        self.api.command_queue.put_nowait((Command.ARTIST, artistId))

    async def __albumsong(self, albumId, songId):
        self.api.skip_to = songId
        if self.api.status != Status.STOPPED:
            self.api.playback_queue.put_nowait(Action.STOP)
        self.api.command_queue.put_nowait((Command.ALBUM, albumId))

    async def __song(self, songId):
        self.api.skip_to = songId
        if self.api.status != Status.STOPPED:
            self.api.playback_queue.put_nowait(Action.NEXT)

    async def __quit(self):
        self.api.search_queue.put_nowait((Command.QUIT, None))

    async def __next(self):
        self.api.playback_queue.put_nowait(Action.NEXT)

    async def __restart(self):
        self.api.playback_queue.put_nowait(Action.RESTART)

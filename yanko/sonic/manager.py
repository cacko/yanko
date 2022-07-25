import logging
from pathlib import Path
from queue import LifoQueue
from yanko.sonic import Action, Command, NowPlaying, Playstatus, LastAdded, Search, Status, RecentlyPlayed
from yanko.sonic.api import Client, CoverArtFile
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed



async def resolveCoverArt(obj):
    ca = CoverArtFile(obj.coverArt)
    res: Path = await ca.path
    obj.coverArt = res.as_posix() if res.exists() else None
    return obj

async def resolveIcon(obj):
    ca = CoverArtFile(obj.icon.path)
    res: Path = await ca.path
    obj.icon.path = res.as_posix() if res.exists() else None
    return obj

def find_idx_by_id(items, item, k='id'):
    for idx,itm in enumerate(items):
        if getattr(itm, k) == getattr(item, k):
            return idx

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
    __player_queue: LifoQueue = None

    def __init__(self) -> None:
        self.eventLoop = asyncio.new_event_loop()
        self.commander = LifoQueue()
        self.api = Client()
        self.__player_queue = LifoQueue()
        self.api.manager_queue = self.__player_queue

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
            if self.__player_queue.empty():
                await asyncio.sleep(0.1)
                continue
            await self.player_runner()

    async def commander_runner(self):
        try:
            cmd, payload = self.commander.get_nowait()
            match(cmd):
                case Command.RANDOM:
                    await self.__random()
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
                case Command.ALBUM:
                    await self.__album(payload)
                case Command.SONG:
                    await self.__song(payload)
                case Command.SEARCH:
                    await self.__search(payload)
                case Command.ALBUMSONG:
                    await self.__albumsong(*payload.split('/'))
            self.commander.task_done()
        except Exception as e:
            logging.exception(e)

    async def player_runner(self):
        try:
            cmd = self.__player_queue.get_nowait()
            if isinstance(cmd, Playstatus) and cmd == Status.EXIT:
                self.__running = False
            elif isinstance(cmd, NowPlaying) and cmd.track.coverArt:
                cmd.track = await resolveCoverArt(cmd.track)
            elif isinstance(cmd, Search) and len(cmd.items):
                with ThreadPoolExecutor(max_workers=10) as executor:
                    jobs = [executor.submit(resolveIcon, item) for item in cmd.items]
                    for future in as_completed(jobs):
                        try:
                            res = await future.result()
                            cmd.items[find_idx_by_id(cmd.items, res, 'uid')] = res
                        except Exception as e:
                            logging.error(e, exc_info=True)

            elif isinstance(cmd, LastAdded) or isinstance(cmd, RecentlyPlayed):
                with ThreadPoolExecutor(max_workers=10) as executor:
                    jobs = [executor.submit(resolveCoverArt, album) for album in cmd.albums]
                    for future in as_completed(jobs):
                        try:
                            res = await future.result()
                            cmd.albums[find_idx_by_id(cmd.albums, res)] = res
                        except Exception as e:
                            logging.error(e, exc_info=True)
            self.player_callback(cmd)
            self.__player_queue.task_done()
        except Exception as e:
            logging.exception(e)

    async def __random(self):
        if self.api.playing:
            self.api.playback_queue.put_nowait(Action.STOP)
        self.api.command_queue.put_nowait((Command.RANDOM, None))

    async def __newest(self):
        self.api.command_queue.put_nowait((Command.NEWEST, None))

    async def __recently_played(self):
        self.api.command_queue.put_nowait((Command.RECENTLY_PLAYED, None))

    async def __search(self, query):
        self.api.search_queue.put_nowait((Command.SEARCH, query))

    async def __album(self, albumId):
        if self.api.playing:
            self.api.playback_queue.put_nowait(Action.STOP)
        self.api.command_queue.put_nowait((Command.ALBUM, albumId))

    async def __albumsong(self, albumId, songId):
        self.api.skip_to = songId
        if self.api.playing:
            self.api.playback_queue.put_nowait(Action.STOP)
        self.api.command_queue.put_nowait((Command.ALBUM, albumId))

    async def __song(self, songId):
        self.api.skip_to = songId
        if self.api.playing:
            self.api.playback_queue.put_nowait(Action.NEXT)

    async def __quit(self):
        self.api.playback_queue.put_nowait(Action.EXIT)

    async def __next(self):
        self.api.playback_queue.put_nowait(Action.NEXT)

    async def __restart(self):
        self.api.playback_queue.put_nowait(Action.RESTART)

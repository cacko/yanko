from queue import LifoQueue
from yanko.sonic import Action, Command, Playstatus, Status
from yanko.sonic.psub import pSub
import time
import asyncio


class ManagerMeta(type):

    _instance = None

    def __call__(self, *args, **kwds):
        if not self._instance:
            self._instance = super().__call__(*args, **kwds)
        return self._instance


class Manager(object, metaclass=ManagerMeta):

    commander: LifoQueue = None
    eventLoop: asyncio.AbstractEventLoop = None
    manager_callback = None
    player_callback = None
    psub = None
    __running = False
    __player_queue: LifoQueue = None

    def __init__(self) -> None:
        self.eventLoop = asyncio.new_event_loop()
        self.commander = LifoQueue()
        self.psub = pSub()
        self.__player_queue = LifoQueue()
        self.psub.manager_queue = self.__player_queue

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
                case Command.ALBUM:
                    await self.__album(payload)
            self.commander.task_done()
        except Exception as e:
            print(e)

    async def player_runner(self):
        try:
            cmd = self.__player_queue.get_nowait()
            self.player_callback(cmd)
            self.__player_queue.task_done()
            if isinstance(cmd, Playstatus) and cmd == Status.EXIT:
                self.__running = False
        except Exception as e:
            print(e)

    async def __random(self):
        self.psub.command_queue.put_nowait((Command.RANDOM, None))

    async def __newest(self):
        self.psub.command_queue.put_nowait((Command.NEWEST, None))

    async def __album(self, albumId):
        if self.psub.playing:
            self.psub.playback_queue.put_nowait(Action.STOP)
        self.psub.command_queue.put_nowait((Command.ALBUM, albumId))

    async def __quit(self):
        self.psub.playback_queue.put_nowait(Action.EXIT)


    async def __next(self):
        self.psub.playback_queue.put_nowait(Action.NEXT)

    async def __restart(self):
        self.psub.playback_queue.put_nowait(Action.RESTART)


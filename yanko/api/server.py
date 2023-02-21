from queue import Queue
from typing import Optional
import uvicorn
from corethread import StoppableThread
from fastapi import FastAPI, Request, Depends
from pydantic import BaseModel, Extra
from yanko.core import log_level
from yanko.core.config import app_config
from corestring import string_hash
import time
import logging
from yanko.sonic import Command
from yanko.sonic.beats import Beats
from .auth import check_auth


class ApiConfig(BaseModel, extra=Extra.ignore):
    host: str
    port: int


class ServerMeta(type):

    _instance: Optional["Server"] = None
    _manager: Queue
    _queue: dict[str, Queue] = {}

    def __call__(cls, *args, **kwds):
        if not cls._instance:
            cls._instance = type.__call__(cls, *args, **kwds)
        return cls._instance

    def queue(cls, queue_id):
        if queue_id not in cls._queue:
            cls._queue[queue_id] = Queue()
        return cls._queue[queue_id]

    @property
    def app(cls) -> FastAPI:
        return cls().app


class Server(StoppableThread, metaclass=ServerMeta):

    api: Optional[Queue] = None
    server: Optional[uvicorn.Server]
    config_vars = ["host", "port", "threadpool_workers"]

    def __init__(self, *args, **kwargs):
        self.app = FastAPI()
        super().__init__(*args, **kwargs)

    def start(
        self,
        api: Queue,
        state_callback,
    ) -> None:
        self.api = api
        self.state_callback = state_callback
        return super().start()

    def run(self) -> None:
        config = ApiConfig(**app_config.get("api"))
        server_config = uvicorn.Config(
            app=self.app,
            host=config.host,
            port=config.port,
            use_colors=True,
            workers=4,
            # factory=True,
            log_level=log_level.lower()
        )
        self.server = uvicorn.Server(server_config)
        self.server.run()

    def stop(self):
        super().stop()
        if self.server:
            self.server.should_exit = True

    def search(self, query):
        queue_id = string_hash(query)
        queue = __class__.queue(queue_id)
        assert self.api
        self.api.put_nowait((Command.SEARCH, query))
        while True:
            if queue.empty():
                time.sleep(0.1)
            else:
                res = queue.get_nowait()
                return {"items": res.get("items", [])}

    def state(self):
        return self.state_callback()

    def command(self, query):
        queue_item = query.split("=", 2)
        payload = None
        try:
            cmd = Command(queue_item.pop(0))
            if len(queue_item) > 0:
                payload = queue_item.pop(0)
            assert self.api
            self.api.put_nowait((cmd, payload))
        except (ValueError, AssertionError) as e:
            logging.debug(e)


@Server.app.get("/state")
async def state(auth=Depends(check_auth)):
    return Server().state()


@Server.app.post("/beats")
async def beats(request: Request, auth=Depends(check_auth)):
    data = await request.json()
    return Beats.store_beats(data)


@Server.app.get("/search/{query}")
async def search(query: str, auth=Depends(check_auth)):
    return Server().search(query)


@Server.app.get("/command/{query}")
async def command(query: str, auth=Depends(check_auth)):
    return Server().command(query)

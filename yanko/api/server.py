import logging
import time
from queue import Queue
from typing import Optional
import uvicorn
from corethread import StoppableThread
from fastapi import FastAPI, Request
from pydantic import BaseModel, Extra
from corestring import string_hash
from yanko.core import log_level
# from yanko.api.auth import auth_required
from yanko.core.config import app_config
from yanko.sonic import Command
from yanko.sonic.beats import Beats


class ApiConfig(BaseModel, extra=Extra.ignore):
    host: str
    port: int


app = FastAPI()


class ServerMeta(type):

    _instance: Optional["Server"] = None
    _manager: Queue
    _queue: dict[str, Queue] = {}

    def __call__(cls, *args, **kwds):
        if not cls._instance:
            cls._instance = type.__call__(cls, *args, **kwds)
        return cls._instance

    def search(cls, query):
        return cls().do_search(query)

    def state(cls):
        return cls().do_state()

    def command(cls, query):
        return cls().do_command(query)

    def beats(cls, data):
        obj = Beats.store_beats(data)
        return obj

    def queue(cls, queue_id):
        if queue_id not in cls._queue:
            cls._queue[queue_id] = Queue()
        return cls._queue[queue_id]


class Server(StoppableThread, metaclass=ServerMeta):

    api: Optional[Queue] = None
    server: Optional[uvicorn.Server]
    config_vars = ["host", "port", "threadpool_workers"]

    def __init__(self, *args, **kwargs):
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
            app=app,
            host=config.host,
            port=config.port,
            use_colors=True,
            # factory=True,
            log_level=log_level.lower()
        )
        self.server = uvicorn.Server(server_config)
        self.server.run()

    def stop(self):
        super().stop()
        if self.server:
            self.server.should_exit = True

    def do_search(self, query):
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

    def do_state(self):
        return self.state_callback()

    def do_command(self, query):
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


@app.get("/state")
def state():
    return Server.state()


@app.post("/beats")
def beats(request: Request):
    data = request.json()
    return Server.beats(data)


@app.get("/search/{query}")
def search(query: str):
    return Server.search(query)


@app.get("/command/{query}")
def command(query: str):
    return Server.command(query)

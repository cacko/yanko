from sys import api_version

import yaml
from yanko.core.config import app_config
from queue import LifoQueue
from bottle import Bottle, run
import time
from yanko.sonic import Command
from yanko.api.auth import auth_required
from yanko.lametric import LaMetric

app = Bottle()

class ServerMeta(type):

    _instance: 'Server' = None
    _manager: LifoQueue = None
    _queue: LifoQueue = None

    def __call__(self, *args, **kwds):
        if not self._instance:
            self._instance = super().__call__(*args, **kwds)
        return self._instance

    def start(cls, queue: LifoQueue, state_callback):
        cls().start_server(queue, state_callback)

    def search(cls, query):
        return  cls().do_search(query)

    def state(cls):
        return  cls().do_state()

    def command(cls, query):
        return cls().do_command(query)

    @property
    def queue(cls):
        if not cls._queue:
            cls._queue = LifoQueue()
        return cls._queue

class Server(object, metaclass=ServerMeta):

    api: LifoQueue = None
    state_callback = None
    
    def start_server(self, queue, state_callback):
        self.api = queue
        self.state_callback = state_callback
        conf = app_config.get("api")
        run(app, **conf)

    def do_search(self, query):
        self.api.put_nowait((Command.SEARCH, query))
        while True:
            if __class__.queue.empty():
                time.sleep(0.1)
            else:
                res = __class__.queue.get_nowait()
                return res

    def do_state(self):
        self.state_callback()
            
    def do_command(self, query):
        c, i = query.split("=", 2)
        try:
            cmd = Command(c)
            self.api.put_nowait((cmd, i))
        except ValueError as e:
            print(e)

@app.route('/state')
@auth_required
def state():
    return Server.state()

@app.route('/search/<query:path>')
@auth_required
def search(query):
    return Server.search(query)

@app.route('/command/<query:path>')
@auth_required
def command(query):
    return Server.command(query)

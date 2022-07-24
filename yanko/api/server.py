from sys import api_version
from yanko.core.config import app_config
from queue import LifoQueue
from bottle import Bottle, run
import time
from yanko.sonic import Command

app = Bottle()


class ServerMeta(type):

    _instance: 'Server' = None
    _manager: LifoQueue = None
    _queue: LifoQueue = None

    def __call__(self, *args, **kwds):
        if not self._instance:
            self._instance = super().__call__(*args, **kwds)
        return self._instance

    def start(cls, queue: LifoQueue):
        cls().start_server(queue)

    def search(cls, query):
        return  cls().do_search(query)

    def command(cls, query):
        return cls().do_command(query)

    @property
    def queue(cls):
        if not cls._queue:
            cls._queue = LifoQueue()
        return cls._queue

class Server(object, metaclass=ServerMeta):

    api: LifoQueue = None
    
    def start_server(self, queue):
        self.api = queue
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
            
    def do_command(self, query):
        c, i = query.split("=", 2)
        try:
            cmd = Command(c)
            self.api.put_nowait((cmd, i))
        except ValueError as e:
            print(e)

@app.route('/search/<query:path>')
def search(query):
    return Server.search(query)

@app.route('/command/<query:path>')
def command(query):
    return Server.command(query)
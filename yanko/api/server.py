from yanko.core.config import app_config
from queue import Queue
from bottle import Bottle, run
import time
from yanko.core.thread import StoppableThread
from yanko.sonic import Command
from yanko.api.auth import auth_required
from yanko.core.string import string_hash

app = Bottle()

class ServerMeta(type):

    _instance: 'Server' = None
    _manager: Queue = None
    _queue: dict[str, Queue] = {}

    def __call__(self, *args, **kwds):
        if not self._instance:
            self._instance = super().__call__(*args, **kwds)
        return self._instance

    def listen(cls, queue: Queue, state_callback):
        cls().start(queue, state_callback)
        return cls()

    def search(cls, query):
        return  cls().do_search(query)

    def state(cls):
        return  cls().do_state()

    def command(cls, query):
        return cls().do_command(query)

    def queue(cls, queue_id):
        if queue_id not in cls._queue:
            cls._queue[queue_id] = Queue()
        return cls._queue[queue_id]

class Server(StoppableThread, metaclass=ServerMeta):

    api: Queue = None
    state_callback = None

    def start(self, queue, state_callback):
        self.api = queue
        self.state_callback = state_callback
        return super().start()
    
    def run(self):
        conf = app_config.get("api")
        run(app, **conf)

    def do_search(self, query):
        queue_id = string_hash(query)
        queue = __class__.queue(queue_id)
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
            self.api.put_nowait((cmd, payload))
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

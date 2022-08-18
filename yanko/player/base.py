from queue import Queue
from yanko.sonic import Status
from pathlib import Path
from yanko.core.config import app_config
from urllib.parse import urlparse, parse_qs, urlencode


class BasePlayer(object):

    _queue: Queue = None
    _url = None

    def __init__(self, queue):
        self.lock_file.unlink(missing_ok=True)
        self._queue = queue

    @property
    def lock_file(self) -> Path:
        return app_config.app_dir / "play.lock"



    def get_stream_url(self, stream_url, track_data, format="raw"):
        song_id = track_data.get("id")
        url = urlparse(stream_url)
        query = parse_qs(url.query)
        query = {"id": song_id, "format": format, **query}
        return f"{url.scheme}://{url.netloc}{url.path}?{urlencode(query, doseq=True)}"

    @property
    def hasFinished(self):
        raise NotImplementedError

    def play(self, stream_url, track_data):
        raise NotImplementedError

    def _stop(self):
        raise NotImplementedError

    def _restart(self, stream_url, track_data):
        raise NotImplementedError

    def _next(self):
        raise NotImplementedError

    def _previous(self):
        raise NotImplementedError

    def pause(self):
        raise NotImplementedError

    def resume(self):
        raise NotImplementedError

    def exit(self):
        self._terminate()
        return Status.EXIT

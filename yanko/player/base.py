from pathlib import Path
from queue import Queue
from threading import Event
from typing import Optional
from urllib.parse import parse_qs, urlencode, urlparse
from yanko.core.config import app_config
from yanko.sonic import Status, StreamFormat


class BasePlayer(object):

    _queue: Queue
    _manager_queue: Queue
    _time_event: Event
    _format = "raw"
    volume: float
    muted: bool

    def __init__(
        self,
        queue,
        manager_queue,
        stream_url,
        track_data,
        time_event,
        volume = 1,
        muted = False,
        format: Optional[StreamFormat] = None,
    ):
        self.volume = volume
        self.muted = muted
        self.lock_file.unlink(missing_ok=True)
        self._queue = queue
        self._manager_queue = manager_queue
        self._time_event = time_event
        self._url = stream_url
        self._data = track_data
        self._format = format.value if format else StreamFormat.RAW.value

    @property
    def lock_file(self) -> Path:
        return app_config.app_dir / "play.lock"

    @property
    def stream_url(self):
        song_id = self._data.get("id")
        url = urlparse(self._url)
        query = parse_qs(url.query)
        query = {"id": song_id, "format": self._format, **query}
        return f"{url.scheme}://{url.netloc}{url.path}?{urlencode(query, doseq=True)}"

    @property
    def hasFinished(self):
        raise NotImplementedError

    def play(self):
        raise NotImplementedError

    def _stop(self):
        raise NotImplementedError

    def _restart(self):
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
        return Status.EXIT

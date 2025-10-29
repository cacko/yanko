from pathlib import Path
from queue import Queue
from threading import Event
from typing import Optional
from urllib.parse import parse_qs, urlencode, urlparse
from yanko.core.config import app_config
from yanko.sonic import Status, StreamFormat


class BasePlayer(object):

    _control: Optional[Queue] = None

    def __init__(
        self,
        queue,
        manager_queue,
        stream_url,
        track_data,
        time_event,
        format: StreamFormat,
        volume: float = 1,
        muted: bool = False,

    ):
        self.volume = volume
        self.muted = muted
        self.lock_file.unlink(missing_ok=True)
        self._queue = queue
        self._manager_queue = manager_queue
        self._time_event = time_event
        self._end_event = Event()
        self._url = stream_url
        self._data = track_data
        self._format = format

    @property
    def lock_file(self) -> Path:
        return app_config.app_dir / "play.lock"

    @property
    def stream_url(self):
        song_id = self._data.get("id")
        url = urlparse(self._url)
        query = parse_qs(url.query)
        query = dict(id=song_id, format=self._format.value, **query)
        if self._format == StreamFormat.NONE:
            del query["format"]
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

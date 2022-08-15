from queue import Queue
import queue
from yanko.core.config import app_config
from pathlib import Path
import json
from yanko.sonic import Playlist, Track
from datetime import datetime, timezone


class PlayQueue:

    __queue: Queue = None
    __songs: list = []
    __idx: int = 0
    skip_to = None

    def __init__(self, manager_queue: Queue) -> None:
        self.__queue = manager_queue
        self.__load()

    @property
    def playlist_file(self) -> Path:
        return app_config.app_dir / "playlist.dat"

    def __load(self):
        if not self.playlist_file.exists():
            return
        with self.playlist_file.open("r") as fp:
            try:
                last_playlist = json.load(fp)
                self.load(last_playlist)
            except json.decoder.JSONDecodeError:
                pass

    def load(self, songs):
        self.__idx = 0
        self.__songs = songs[:]
        with self.playlist_file.open("w") as fp:
            json.dump(songs, fp)
        self.__queue.put_nowait(
            Playlist(
                start=datetime.now(tz=timezone.utc),
                tracks=[Track(**data) for data in self.__songs]
            )
        )

    def __iter__(self):
        for idx, song in enumerate(self.__songs):
            self.__idx = idx
            if self.skip_to:
                if song.get("id") == self.skip_to:
                    self.skip_to = None
                else:
                    continue
            yield song

    def previous(self):
        res = self.__songs[max(0, self.__idx - 1)]
        self.skip_to = res.get("id")
        return res

    def next(self):
        if self.skip_to:
            return next(filter(lambda x: x.get("id") == self.skip_to, self.__songs), None)
        res = self.__songs[min(len(self.__songs), self.__idx + 1)]
        self.skip_to = res.get("id")
        return res

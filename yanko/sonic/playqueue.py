from queue import Queue
from yanko.core.config import app_config
from pathlib import Path
import json
import pickle
from yanko.sonic import Command, Playlist, Track
from datetime import datetime, timezone
from yanko.sonic.beats import Fetcher
import logging
from typing import Optional


class PlayQueue:

    __songs: list = []
    __idx: int = 0
    __last_id: Optional[str] = None
    __skip_error: int = 0
    skip_to = None

    def __init__(self, manager_queue: Queue) -> None:
        self.__queue = manager_queue
        self.__load()

    @property
    def playlist_file(self) -> Path:
        return app_config.app_dir / "playlist.dat"

    @property
    def last_id_file(self) -> Path:
        return app_config.app_dir / "last_id.dat"

    @property
    def last_id(self):
        try:
            if not self.__last_id:
                assert self.last_id_file.exists()
                data = self.last_id_file.read_bytes()
                if not data:
                    return None
                last_id = pickle.loads(data)
                self.__last_id = last_id
            return self.__last_id
        except AssertionError:
            return None


    @last_id.setter
    def last_id(self, val):
        self.__last_id = val
        self.last_id_file.write_bytes(pickle.dumps(val))

    def __load(self):
        if not self.playlist_file.exists():
            return
        with self.playlist_file.open("r") as fp:
            try:
                last_playlist = json.load(fp)
                self.load(last_playlist)
                if last_id := self.last_id:
                    ids = [s.get("id") for s in self.__songs]
                    if last_id in ids:
                        self.skip_to = last_id
            except json.decoder.JSONDecodeError:
                pass

    def load(self, songs):
        self.__idx = 0
        self.__songs = songs[:]
        with self.playlist_file.open("w") as fp:
            json.dump(songs, fp)
        Fetcher.add(paths=[x.get("path") for x in songs])
        self.__queue.put_nowait(
            (
                Command.PLAYER_RESPONSE,
                Playlist(
                    start=datetime.now(tz=timezone.utc),
                    tracks=[Track(**data) for data in self.__songs],
                ),
            )
        )

    def __iter__(self):
        if not len(self.__songs):
            return
        for idx, song in enumerate(self.__songs):
            self.__idx = idx
            if self.skip_to:
                logging.debug(f"skip to {self.skip_to}, song id={song.get('id')}")
                if song.get("id") == self.skip_to:
                    logging.debug(f"skipped to {self.skip_to}")
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
            match = next(
                filter(lambda x: x.get("id") == self.skip_to, self.__songs), None
            )
            try:
                assert match
                self.__skip_error = 0
            except AssertionError:
                self.__skip_error += 1
                if self.__skip_error > len(self.__songs):
                    self.skip_to = None
                    self.__skip_error = 0
            return match
        res = self.__songs[min(len(self.__songs) - 1, self.__idx + 1)]
        self.skip_to = res.get("id")
        return res

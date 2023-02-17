from enum import Enum
from pathlib import Path
from cachable import Cachable
from humanfriendly.tables import format_smart_table
from progressor import Progress
from yanko.db.base import YankoDb
from yanko.db.models import Album, Artist, ArtistInfo, Beats
from pydantic import BaseModel, Extra, Field, PrivateAttr


def format_size(*args, **kwds):
    print(args, kwds)


class CacheType(BaseModel, extra=Extra.ignore):
    name: str
    count: int
    size: int = Field(default=0)
    _files: list[Path] = PrivateAttr()

    def __init__(self, **data):
        super().__init__(**data)
        self._files = []

    def add(self, fp: Path):
        if fp.exists():
            self._files.append(fp)
            self.count += 1
            self.size += fp.stat().st_size

    def clear(self):
        with Progress(title="Deleting...") as progress:
            for fp in progress.track(self._files):
                fp.unlink(missing_ok=True)


class Cache(BaseModel, extra=Extra.ignore):
    cover_art: CacheType
    cover_icon: CacheType
    beats_json: CacheType

    def to_table(self):
        data = [map(str, v.values()) for v in self.dict().values()]

        return format_smart_table(data, ["Name", "Count", "Size"])


class Method(Enum):
    GET = "get"
    POST = "post"
    PUT = "put"
    DELETE = "delete"


class CachableDb(Cachable):
    def __init__(
        self,
        model: Beats | Artist | Album | ArtistInfo,
        id_key: str,
        id_value: str
    ) -> None:
        self.__model = model
        self.__id_key = id_key
        self.__id_value = id_value
        super().__init__()

    def fromcache(self):
        if model := self.__model.fetch(
            getattr(self.__model, self.__id_key) == self.__id_value
        ):
            return model
        return None

    def tocache(self, res: dict):
        with YankoDb.db.atomic():
            model = self.__model(**res)  # type: ignore
            model.save()
            return model

    @property
    def isCached(self) -> bool:
        q = self.__model.select().where(
            getattr(self.__model, self.__id_key) == self.__id_value
        )
        exists = q.exists()
        return exists

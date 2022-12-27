from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import humanfriendly
from cachable import Cachable
from dataclasses_json import Undefined, config, dataclass_json
from humanfriendly.tables import format_smart_table
from progressor import Progress
import logging
from yanko.db.base import YankoDb
from yanko.db.models import BaseModel


def format_size(*args, **kwds):
    print(args, kwds)


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class CacheType:
    name: str
    count: int
    size: int = field(
        metadata=config(
            encoder=humanfriendly.format_size,
        )
    )

    def __post_init__(self):
        self.__files = []

    def add(self, fp: Path):
        if fp.exists():
            self.__files.append(fp)
            self.count += 1
            self.size += fp.stat().st_size

    def clear(self):
        with Progress(title="Deleting...") as progress:
            for fp in progress.track(self.__files):
                fp.unlink(missing_ok=True)


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class Cache:
    cover_art: CacheType
    cover_icon: CacheType
    beats_json: CacheType

    def to_table(self):
        data = [map(str, v.values()) for v in self.to_dict().values()]  # type: ignore

        return format_smart_table(data, ["Name", "Count", "Size"])


class Method(Enum):
    GET = "get"
    POST = "post"
    PUT = "put"
    DELETE = "delete"


class CachableDb(Cachable):
    def __init__(self, model: BaseModel, id_key: str, id_value: str) -> None:
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
        if exists:
            logging.warning(
                f"RECORD exists {self.__model} {self.__id_key}=={self.__id_value}"
            )
        return exists

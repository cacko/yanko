from enum import Enum
from yanko import logger
from pathlib import Path
from cachable import Cachable
from yanko.db.base import YankoDb
from yanko.db.models import BaseModel
from dataclasses_json import dataclass_json, Undefined, config
from dataclasses import dataclass, field
import humanfriendly
from humanfriendly.tables import format_smart_table
from progressor import Progress

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
        ))

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
        data = [map(str, v.values()) for v in self.to_dict().values()]

        return format_smart_table(
            data,
            ["Name", "Count", "Size"]
        )

class Method(Enum):
    GET = "get"
    POST = "post"
    PUT = "put"
    DELETE = "delete"


class CachableDb(Cachable):

    __model: BaseModel = None
    __id_key: str = None
    __id_value: str = None

    def __init__(self, model: BaseModel, id_key: str, id_value: str) -> None:
        self.__model = model
        self.__id_key = id_key
        self.__id_value = id_value
        super().__init__()


    def fromcache(self):
        if model := self.__model.fetch(getattr(self.__model, self.__id_key) == self.__id_value):
            return model
        return None

    def tocache(self, res: dict):
        with YankoDb.db.atomic():
            model = self.__model(**res)
            model.save()
            return model

    @property
    def isCached(self) -> bool:
        q = self.__model.select().where(getattr(self.__model, self.__id_key) == self.__id_value)
        exists = q.exists()
        if exists:
            logger.warning(f"RECORD exists {self.__model} {self.__id_key}=={self.__id_value}")
        return exists

# @dataclass_json(undefined=Undefined.EXCLUDE)
# @dataclass
# class TimeCache:
#     timestamp: datetime
#     struct: any


# @dataclass
# class BinaryStruct:
#     binary: any
#     type: str


# class StorageMeta(type):

#     __instance = None
#     __storage_path = None

#     def __call__(cls, *args, **kwargs):
#         if not cls.__instance:
#             cls.__instance = type.__call__(cls, *args, **kwargs)
#         return cls.__instance

#     def register(cls, storage_path: Path):
#         cls.__storage_path = storage_path

#     @property
#     def root(cls) -> Path:
#         return cls.__storage_path

#     def get(cls, key):
#         return cls().do_get(cls.root / key)

#     def set(cls, key, data):
#         return cls().do_set(cls.root / key, data)

#     def persist(cls, key):
#         pass

#     def exists(cls, key):
#         return cls().do_exists(cls.root / key)


# class Storage(object, metaclass=StorageMeta):

#     def do_get(self, p: Path):
#         return p.read_bytes()

#     def do_set(self, p: Path, data):
#         return p.write_bytes(data)

#     def do_exists(self, p: Path):
#         return p.exists()


# class CacheableMeta(type):

#     _storage: Path = None

#     def register(cls, storage_dir: str):
#         cls.storage = storage_dir
#         Storage.register(cls.storage)

#     @property
#     def storage(self) -> Path:
#         if not self._storage:
#             raise FileNotFoundError
#         return self._storage

#     @storage.setter
#     def storage(self, value: str):
#         p = Path(value)
#         if not p.exists():
#             p.mkdir(parents=True)
#         if not p.is_dir():
#             raise FileNotFoundError
#         self._storage = p

#     @property
#     def hash_key(cls):
#         return f"{cls.__name__}"


# class Cachable(object, metaclass=CacheableMeta):

#     _struct = None

#     def fromcache(self):
#         if data := Storage.get(self.store_key):
#             return pickle.loads(data)
#         return None

#     def tocache(self, res):
#         logger.debug(self.store_key)

#         Storage.set(self.store_key, pickle.dumps(res))
#         Storage.persist(self.store_key)
#         return res

#     def load(self) -> bool:
#         if self._struct is not None:
#             return True
#         if not self.isCached:
#             return False
#         self._struct = self.fromcache()
#         return True if self._struct else False

#     @property
#     def id(self):
#         raise NotImplementedError

#     @property
#     def isCached(self) -> bool:
#         return Storage.exists(self.store_key) == 1

#     @property
#     def store_key(self):
#         return f"{self.__class__.__name__}.{self.id}"


# class TimeCacheable(Cachable):

#     cachetime: timedelta = timedelta(minutes=1)
#     _struct: TimeCache = None

#     def fromcache(self):
#         if data := Storage.get(self.store_key):
#             struct: TimeCache = pickle.loads(data)
#             return struct if not self.isExpired(struct.timestamp) else None
#         return None

#     def tocache(self, res) -> TimeCache:
#         timecache = TimeCache(timestamp=datetime.now(
#             tz=timezone.utc), struct=res)
#         Storage.set(self.store_key, pickle.dumps(timecache))
#         Storage.persist(self.store_key)
#         return timecache

#     def isExpired(self, t: datetime) -> bool:
#         return datetime.now(tz=timezone.utc) - t > self.cachetime

#     def load(self) -> bool:
#         if self._struct and self.isExpired:
#             return False
#         if not self.isCached:
#             return False
#         self._struct = self.fromcache()
#         return True if self._struct else False

#     @property
#     def isCached(self) -> bool:
#         if not Storage.exists(self.store_key) == 1:
#             return False
#         if data := Storage.get(self.store_key):
#             struct: TimeCache = TimeCache.from_dict(pickle.loads(data))
#             return not self.isExpired(struct.timestamp)
#         return False


# class CachableFile(Cachable):

#     DEFAULT: Path = None
#     SIZE = (250, 250)
#     _path: Path = None
#     __contentType: str = None
#     __filehash: str = None

#     def tocache(self, res: BinaryStruct):
#         im = Image.open(io.BytesIO(res.binary))
#         im.thumbnail(self.SIZE, Image.BICUBIC)
#         im.save(self.storage_path.as_posix())

#     def fromcache(self):
#         if self.isCached:
#             return self.path
#         return None

#     @property
#     def storage_path(self):
#         if not self._path:
#             self._path = type(self).storage / f"{self.store_key}"
#         return self._path

#     @property
#     def path(self):
#         self._init()
#         return self.storage_path

#     @property
#     def filehash(self):
#         if not self.__filehash:
#             self.__filehash = file_hash(self.storage_path)
#         return self.__filehash

#     @property
#     def contentType(self) -> str:
#         if not self.__contentType and self.storage_path.exists():
#             self.__contentType, _ = mimetypes.guess_type(self.storage_path)
#         return self.__contentType

#     @property
#     def isCached(self) -> bool:
#         return self.storage_path.exists()

#     @property
#     def filename(self):
#         raise NotImplementedError

#     @property
#     def url(self):
#         raise NotImplementedError

#     @property
#     def store_key(self):
#         return f"{self.__class__.__name__}.{self.filename}"

#     def _init(self):
#         if self.isCached:
#             return
#         try:
#             resp = requests.get(self.url)
#             self._struct = BinaryStruct(
#                 binary=resp.content,
#                 type=resp.headers.get("content-type")
#             )
#             self.tocache(self._struct)
#         except Exception:
#             self._path = self.DEFAULT

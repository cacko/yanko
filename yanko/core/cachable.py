from datetime import datetime, timedelta, timezone
import mimetypes
from pathlib import Path
import pickle
from PIL import Image
import io
import requests
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from dataclasses_json import dataclass_json, Undefined


class Method(Enum):
    GET = "get"
    POST = "post"
    PUT = "put"
    DELETE = "delete"


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class TimeCache:
    timestamp: datetime
    struct: any


@dataclass
class BinaryStruct:
    binary: any
    type: str


class StorageMeta(type):

    __instance = None
    __storage_path = None

    def __call__(cls, *args, **kwargs):
        if not cls.__instance:
            cls.__instance = type.__call__(cls, *args, **kwargs)
        return cls.__instance

    def register(cls, storage_path: Path):
        cls.__storage_path = storage_path

    @property
    def root(cls) -> Path:
        return cls.__storage_path

    def get(cls, key):
        return cls().do_get(cls.root / key)

    def set(cls, key, data):
        return cls().do_set(cls.root / key, data)

    def persist(cls, key):
        pass

    def exists(cls, key):
        return cls().do_exists(cls.root / key)


class Storage(object, metaclass=StorageMeta):

    def do_get(self, p: Path):
        return p.read_bytes()

    def do_set(self, p: Path, data):
        return p.write_bytes(data)

    def do_exists(self, p: Path):
        return p.exists()


class CacheableMeta(type):

    _storage: Path = None

    def register(cls, storage_dir: str):
        cls.storage = storage_dir
        Storage.register(cls.storage)

    @property
    def storage(self) -> Path:
        if not self._storage:
            raise FileNotFoundError
        return self._storage

    @storage.setter
    def storage(self, value: str):
        p = Path(value)
        if not p.exists():
            p.mkdir(parents=True)
        if not p.is_dir():
            raise FileNotFoundError
        self._storage = p

    @property
    def hash_key(cls):
        return f"{cls.__name__}"


class Cachable(object, metaclass=CacheableMeta):

    _struct = None

    def fromcache(self):
        if data := Storage.get(self.store_key):
            return pickle.loads(data)
        return None

    def tocache(self, res):
        Storage.set(self.store_key, pickle.dumps(res))
        Storage.persist(self.store_key)
        return res

    def load(self) -> bool:
        if self._struct is not None:
            return True
        if not self.isCached:
            return False
        self._struct = self.fromcache()
        return True if self._struct else False

    @property
    def id(self):
        raise NotImplementedError

    @property
    def isCached(self) -> bool:
        return Storage.exists(self.store_key) == 1

    @property
    def store_key(self):
        return f"{self.__class__.__name__}.{self.id}"


class TimeCacheable(Cachable):

    cachetime: timedelta = timedelta(minutes=1)
    _struct: TimeCache = None

    def fromcache(self):
        if data := Storage.get(self.store_key):
            struct: TimeCache = pickle.loads(data)
            return struct if not self.isExpired(struct.timestamp) else None
        return None

    def tocache(self, res) -> TimeCache:
        timecache = TimeCache(timestamp=datetime.now(
            tz=timezone.utc), struct=res)
        Storage.set(self.store_key, pickle.dumps(timecache))
        Storage.persist(self.store_key)
        return timecache

    def isExpired(self, t: datetime) -> bool:
        return datetime.now(tz=timezone.utc) - t > self.cachetime

    def load(self) -> bool:
        if self._struct and self.isExpired:
            return False
        if not self.isCached:
            return False
        self._struct = self.fromcache()
        return True if self._struct else False

    @property
    def isCached(self) -> bool:
        if not Storage.exists(self.store_key) == 1:
            return False
        if data := Storage.get(self.store_key):
            struct: TimeCache = TimeCache.from_dict(pickle.loads(data))
            return not self.isExpired(struct.timestamp)
        return False


class CachableFile(Cachable):

    DEFAULT: Path = None
    SIZE = (250, 250)
    _path: Path = None
    __contentType: str = None

    def tocache(self, res: BinaryStruct):
        im = Image.open(io.BytesIO(res.binary))
        im.thumbnail(self.SIZE, Image.BICUBIC)
        im.save(self.storage_path.as_posix())

    def fromcache(self):
        if self.isCached:
            return self.path
        return None

    @property
    def storage_path(self):
        if not self._path:
            self._path = type(self).storage / f"{self.store_key}"
        return self._path

    @property
    def path(self):
        self._init()
        return self.storage_path

    @property
    def contentType(self) -> str:
        if not self.__contentType and self.storage_path.exists():
            self.__contentType, _ = mimetypes.guess_type(self.storage_path)
        return self.__contentType

    @property
    def isCached(self) -> bool:
        return self.storage_path.exists()

    @property
    def filename(self):
        raise NotImplementedError

    @property
    def url(self):
        raise NotImplementedError

    @property
    def store_key(self):
        return f"{self.__class__.__name__}.{self.filename}"

    def _init(self):
        if self.isCached:
            return
        try:
            resp = requests.get(self.url)
            self._struct = BinaryStruct(
                binary=resp.content,
                type=resp.headers.get("content-type")
            )
            self.tocache(self._struct)
        except Exception:
            self._path = self.DEFAULT

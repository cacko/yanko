from cachable.cacheable import Cachable
from cachable.storage import Storage as ReStorage
from yanko.core.string import string_hash


class ApiCache(Cachable):

    __url: str = None
    __id: str = None

    def __init__(self, url) -> None:
        self.__url = url

    @property
    def id(self):
        if not self.__id:
            self.__id = string_hash(self.__url)
        return self.__id

    @classmethod
    def flush(cls):
        ReStorage._redis.flushdb(asynchronous=True)

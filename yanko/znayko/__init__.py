from yanko.core.config import app_config
from yanko.core.cachable import Method
from enum import Enum
from requests import request
import logging

class Endpoints(Enum):
    BEATS = 'beats'


class ZnaykoMeta(type):

    _instance = None

    def __call__(self, *args, **kwds):
        if not self._instance:
            self._instance = type.__call__(self, *args, **kwds)
        return self._instance

    def beats(cls, path: str):
        return cls().make_request(Method.GET, Endpoints.BEATS.value, params={"path": path})


class Znayko(object, metaclass=ZnaykoMeta):

    __host = None

    def __init__(self) -> None:
        conf = app_config.get("znayko")
        self.__host = conf.get("api")

    def make_request(self, method: Method, endpoint: Endpoints, **kwags):
        try:
            resp = request(
                method=method.value,
                url=f"{self.__host}/{endpoint}",
                **kwags
            )
            return resp.json()
        except Exception as e:
            logging.debug(e)
            return None

import logging
from os import environ
from pathlib import Path
from typing import Optional
from pydantic import BaseModel
import requests
from pixelme import Pixelate
from requests.exceptions import ConnectionError, JSONDecodeError

from yanko.core.cachable import Method
from yanko.core.config import app_config
from yanko.lametric.auth import OTP
from yanko.sonic import Status


class NowPlayingFrame(BaseModel):
    text: str
    icon: Optional[str] = None


class StatusFrame(BaseModel):
    status: str


class LaMetricMeta(type):

    _instance = None

    def __call__(self, *args, **kwds):
        if not self._instance:
            self._instance = super().__call__(*args, **kwds)
        return self._instance

    def nowplaying(cls, text, icon: Optional[str] = None):
        cls().send_nowplaying(text, icon)

    def status(cls, status: Status = Status.STOPPED):
        cls().send_status(status)


class LaMetric(object, metaclass=LaMetricMeta):
    def __make_request(self, method: Method, endpoint: str, **args):
        conf = app_config.get("lametric")
        if not conf:
            return
        host = environ.get("LAMETRIC_CONTROLLER", conf.get("host"))
        try:
            response = requests.request(
                method=method.value,
                headers=OTP.headers,
                url=f"{host}/{endpoint}",
                **args,
            )
            return response.json()
        except ConnectionError:
            logging.debug("lametric is off")
        except JSONDecodeError:
            pass

    def send_nowplaying(self, text, icon: Optional[str] = None):
        model = NowPlayingFrame(text=text)
        try:
            assert icon
            icon_path = Path(icon)
            assert icon_path.exists()
            pix = Pixelate(icon_path, padding=200, block_size=25)
            pix.resize((8, 8))
            model = NowPlayingFrame(text=text, icon=pix.base64)
        except AssertionError:
            pass

        return self.__make_request(Method.POST, "api/nowplaying", json=model.dict())

    def send_status(self, status: Status = Status.STOPPED):
        return self.__make_request(
            Method.POST, "api/status", json=StatusFrame(status=status.value).dict()
        )

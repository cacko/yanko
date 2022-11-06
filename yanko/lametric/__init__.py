import logging
from dataclasses import asdict, dataclass
from os import environ
from pathlib import Path
from typing import Optional

import requests
from dataclasses_json import Undefined, dataclass_json
from pixelme import Pixelate
from requests.exceptions import ConnectionError, JSONDecodeError

from yanko.core.cachable import Method
from yanko.core.config import app_config
from yanko.lametric.auth import OTP
from yanko.sonic import Status


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class NowPlayingFrame:
    text: str
    icon: Optional[str] = None


@dataclass
class StatusFrame:
    status: str


class LaMetricMeta(type):

    _instance = None

    def __call__(self, *args, **kwds):
        if not self._instance:
            self._instance = super().__call__(*args, **kwds)
        return self._instance

    def nowplaying(cls, text, icon: Path):
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
            logging.debug(f"lametric is off")
        except JSONDecodeError as e:
            pass

    def send_nowplaying(self, text, icon: Path):
        pix = Pixelate(icon, padding=200, block_size=25)
        pix.resize((8, 8))
        model = NowPlayingFrame(text=text, icon=pix.base64)
        return self.__make_request(Method.POST, "api/nowplaying", json=asdict(model))

    def send_status(self, status: Status = Status.STOPPED):
        return self.__make_request(
            Method.POST, "api/status", json=asdict(StatusFrame(status=status.value))
        )

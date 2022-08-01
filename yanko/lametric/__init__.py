import logging
from os import environ
from pathlib import Path
from yanko.core.config import app_config
import requests
from cachable.request import Method
from dataclasses import dataclass
from dataclasses_json import dataclass_json, Undefined
from yanko.lametric.pixel import pixelate
from yanko.lametric.auth import OTP
from yanko.sonic import Status
from requests.exceptions import ConnectionError, JSONDecodeError

@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class NotificationFrame:
    text: str
    icon: int = 17668


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class NotificationModel:
    frames: list[NotificationFrame]


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class Notification:
    model: NotificationModel
    priority: str = "info"
    icon_type: str = "none"


class LaMetricMeta(type):

    _instance = None

    def __call__(self, *args, **kwds):
        if not self._instance:
            self._instance = super().__call__(*args, **kwds)
        return self._instance

    def nowplaying(cls, text, icon: Path):
        cls().send_nowplaying(text, icon)

    def status(cls, status: Status):
        cls().send_status(status)


class LaMetric(object, metaclass=LaMetricMeta):

    def __make_request(self, method: Method, endpoint: str, **args):
        conf = app_config.get("lametric")
        host = environ.get("LAMETRIC_CONTROLLER", conf.get("host"))
        try:
            response = requests.request(
                method=method.value,
                headers=OTP.headers,
                url=f"{host}/{endpoint}",
                **args
            )
            return response.json()
        except ConnectionError:
            logging.debug(f"lametric is off")
        except JSONDecodeError:
            pass

    def send_nowplaying(self, text, icon: Path):
        model = NotificationModel(
            frames=[
                NotificationFrame(
                    text=text,
                    icon=pixelate(icon)
                )
            ]
        )
        return self.__make_request(
            Method.POST,
            "yanko/nowplaying",
            json=model.to_dict()
        )

    def send_status(self, status: Status):
        return self.__make_request(
            Method.POST,
            "yanko/status",
            json={"status": status.value}
        )

from yanko.core.config import app_config
import requests
from cachable.request import Method
from dataclasses import dataclass
from dataclasses_json import dataclass_json, Undefined


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

    def nowplaying(cls, text, icon=17668, priority="info"):
        return cls().do_notification(Notification(
            priority=priority,
            model=NotificationModel(
                frames=[NotificationFrame(
                    text=text,
                    icon=icon
                )]
            )
        ))


class LaMetric(object, metaclass=LaMetricMeta):

    def __make_request(self, method: Method, endpoint: str, **args):
        conf = app_config.get("lametric")
        host = conf.get("host")
        user = conf.get("user")
        apikey = conf.get("apikey")
        response = requests.request(
            method=method.value,
            auth=(user, apikey),
            url=f"{host}/api/v2/{endpoint}",
            **args
        )
        return response.json()

    def do_notification(self, notification: Notification):
        return self.__make_request(
            Method.POST,
            "device/notifications",
            json=notification.to_dict()
        )

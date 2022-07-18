import logging
import toml
from pathlib import Path
from os import environ
from yanko.core.config import Config

logging.basicConfig(
    level=getattr(logging, environ.get("YANKO_LOG_LEVEL", "INFO")),
    format="%(filename)s %(message)s",
    datefmt="YANKO %H:%M:%S",
)
log = logging.getLogger("YANKO")

class app_config_meta(type):
    _instance = None

    def __call__(self, *args, **kwds):
        if not self._instance:
            self._instance = super().__call__(*args, **kwds)
        return self._instance

    def get(cls, var,*args, **kwargs):
        return cls().getvar(var, *args, **kwargs)



class app_config(object, metaclass=app_config_meta):

    _config = None

    def __init__(self) -> None:
        self._config = Config()
        self._config.from_toml("config.toml")

    def getvar(self, var, *args, **kwargs):
        return self._config.get(var, *args, *kwargs)


from pathlib import Path
from yanko import __name__
from appdirs import user_config_dir, user_cache_dir, user_data_dir
from yaml import Loader, load
import logging


class app_config_meta(type):
    _instance = None

    def __call__(self, *args, **kwds):
        if not self._instance:
            self._instance = super().__call__(*args, **kwds)
        return self._instance

    def get(cls, var, *args, **kwargs):
        return cls().getvar(var, *args, **kwargs)

    @property
    def app_dir(cls) -> Path:
        res = Path(user_config_dir(__name__))
        if not res.exists():
            res.mkdir(parents=True)
        return res

    @property
    def cache_dir(cls) -> Path:
        res = Path(user_cache_dir(__name__))
        if not res.exists():
            res.mkdir(parents=True)
        return res

    @property
    def data_dir(cls) -> Path:
        res = Path(user_data_dir(__name__))
        if not res.exists():
            res.mkdir(parents=True)
        return res


class app_config(object, metaclass=app_config_meta):

    _config: dict

    def __init__(self) -> None:
        pth = app_config.app_dir / "config.yaml"
        self._config = load(pth.read_text(), Loader=Loader)

    def getvar(self, var, *args, **kwargs):
        return self._config.get(var, *args, *kwargs)

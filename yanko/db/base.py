from pathlib import Path
from peewee import *
from yanko.core.config import app_config
from playhouse.sqlite_ext import SqliteExtDatabase


class YankoDbMeta(type):
    _instance = None

    def __call__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = type.__call__(cls, *args, **kwargs)
        return cls._instance

    @property
    def db(cls) -> SqliteExtDatabase:
        return cls().get_db()

    def close(cls):
        cls.db.close()

    @property
    def db_file(cls) -> Path:
        return app_config.app_dir / "yanko.db"


class YankoDb(object, metaclass=YankoDbMeta):
    __db: SqliteExtDatabase = None

    def __init__(self):
        self.__db = SqliteExtDatabase(
            __class__.db_file.as_posix(),
            pragmas=(
                ("cache_size", -1024 * 64),
                ("journal_mode", "wal"),
                ("foreign_keys", 1),
            ),
        )

    def get_db(self) -> SqliteExtDatabase:
        return self.__db

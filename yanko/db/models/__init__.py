__all__ = ["BaseModel"]

from peewee import *

from yanko.db.base import YankoDb

class BaseModel(Model):
    @classmethod
    def fetch(cls, *query, **filters):
        try:
            return cls.get(*query, **filters)
        except cls.DoesNotExist:
            return None

    class Meta:
        database = YankoDb.db

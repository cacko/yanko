__all__ = ["BaseModel"]

from peewee import Model
from playhouse.shortcuts import model_to_dict

from yanko.db.base import YankoDb


class BaseModel(Model):
    @classmethod
    def fetch(cls, *query, **filters):
        try:
            return cls.get(*query, **filters)
        except cls.DoesNotExist:  # type: ignore
            return None

    def to_dict(self):
        return model_to_dict(self)

    class Meta:
        database = YankoDb.db

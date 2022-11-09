from peewee import CharField, FloatField
from playhouse.sqlite_ext import JSONField

from . import BaseModel


class Beats(BaseModel):
    path = CharField(index=True)
    beats = JSONField()
    tempo = FloatField()

from peewee import *
from . import BaseModel
from playhouse.sqlite_ext import JSONField


class Beats(BaseModel):
    path = CharField(index=True)
    beats = JSONField()
    tempo = FloatField()

from peewee import CharField, FloatField
from playhouse.sqlite_ext import JSONField

from . import ModelBase


class Beats(ModelBase):
    path = CharField(index=True)
    beats = JSONField()
    tempo = FloatField()

from peewee import CharField, IntegerField

from . import ModelBase


class Artist(ModelBase):
    id = CharField(index=True)
    name = CharField()
    albumCount = IntegerField(default=0)
    artistImageUrl = CharField(null=True)

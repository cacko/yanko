from peewee import CharField, IntegerField

from . import BaseModel


class Artist(BaseModel):
    id = CharField(index=True)
    name = CharField()
    albumCount = IntegerField(default=0)
    artistImageUrl =  CharField(null=True)
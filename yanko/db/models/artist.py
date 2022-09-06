from re import M
from peewee import *
from . import BaseModel


class Artist(BaseModel):
    id = CharField(index=True)
    name = CharField()
    albumCount = IntegerField(default=0)
    artistImageUrl =  CharField(null=True)
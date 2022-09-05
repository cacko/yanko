from re import M
from peewee import *
from . import BaseModel
from playhouse.sqlite_ext import JSONField


class Artist(BaseModel):
    id = CharField(index=True)
    name = CharField()
    albumCount = IntegerField(default=0)
    artistImageUrl: CharField(null=True)
    biography: TextField(null=True)
    musicBrainzId: CharField(null=True)
    lastFmUrl: CharField(null=True)
    smallImageUrl: CharField(null=True)
    mediumImageUrl: CharField(null=True)
    largeImageUrl: CharField(null=True)
    image: CharField(null=True)

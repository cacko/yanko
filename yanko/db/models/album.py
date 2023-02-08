from peewee import (BooleanField, CharField, ForeignKeyField, IntegerField,
                    TimestampField)

from . import ModelBase
from .artist import Artist


class Album(ModelBase):
    artistInfo = ForeignKeyField(Artist, related_name='artist_info')
    id = CharField()
    parent = CharField()
    isDir = BooleanField(default=False)
    title = CharField()
    album = CharField()
    artist = CharField()
    duration = IntegerField()
    created = TimestampField()
    artistId = CharField()
    year = IntegerField(default=0)
    genre = CharField(null=True)
    coverArt = CharField(null=True)
    coverArtIcon = CharField(null=True)
    songCount = IntegerField(default=0)

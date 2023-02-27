import logging
from playhouse.sqlite_ext import JSONField
from peewee import (
    BooleanField,
    CharField,
    ForeignKeyField,
    FloatField,
    IntegerField,
    TimestampField,
    TextField
)
from peewee import Model, IntegrityError
from playhouse.shortcuts import model_to_dict
from yanko.db.base import YankoDb


class ModelBase(Model):
    @classmethod
    def fetch(cls, *query, **filters):
        try:
            return cls.get(*query, **filters)
        except cls.DoesNotExist:  # type: ignore
            return None

    def to_dict(self):
        return model_to_dict(self)

    def save(self, *args, **kwds):
        try:
            return super().save(*args, **kwds)
        except IntegrityError as e:
            logging.exception(e)
            return self.__class__.upsert(self.to_dict())

    @classmethod
    def upsert(cls, data: dict):
        raise NotImplementedError

    class Meta:
        database = YankoDb.db


class Artist(ModelBase):
    id = CharField(index=True)
    name = CharField()
    albumCount = IntegerField(default=0)
    artistImageUrl = CharField(null=True)


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


class ArtistInfo(ModelBase):
    artist_id = CharField(index=True, unique=True)
    biography = TextField(null=True)
    musicBrainzId = CharField(null=True)
    lastFmUrl = CharField(null=True)
    smallImageUrl = CharField(null=True)
    mediumImageUrl = CharField(null=True)
    largeImageUrl = CharField(null=True)
    image = CharField(null=True)

    @classmethod
    def upsert(cls, data: dict):
        artist_id = data.get("artist_id", "")
        del data["artist_id"]
        del data["id"]
        return cls.update(**data).where(cls.artist_id == artist_id).execute()


class Beats(ModelBase):
    path = CharField(index=True, unique=True)
    beats = JSONField()
    tempo = FloatField()

    @classmethod
    def upsert(cls, data: dict):
        path = data.get("path", "")
        del data["path"]
        del data["id"]
        return cls.update(**data).where(cls.path == path).execute()

from peewee import CharField, TextField

from . import ModelBase


class ArtistInfo(ModelBase):
    artist_id = CharField(index=True)
    biography = TextField(null=True)
    musicBrainzId = CharField(null=True)
    lastFmUrl = CharField(null=True)
    smallImageUrl = CharField(null=True)
    mediumImageUrl = CharField(null=True)
    largeImageUrl = CharField(null=True)
    image = CharField(null=True)

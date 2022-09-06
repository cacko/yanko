from peewee import *
from . import BaseModel


class ArtistInfo(BaseModel):
    artist_id = CharField(index=True)
    biography = TextField(null=True)
    musicBrainzId = CharField(null=True)
    lastFmUrl = CharField(null=True)
    smallImageUrl = CharField(null=True)
    mediumImageUrl = CharField(null=True)
    largeImageUrl = CharField(null=True)
    image = CharField(null=True)

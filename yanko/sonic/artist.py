from urllib.parse import urlparse, parse_qs
from hashlib import blake2b
from yanko.sonic import ArtistInfo as ArtistInfoData, ArtistInfo as ArtistInfoResponse
from yanko.core.cachable import CachableDb
from yanko.db.models.artist_info import ArtistInfo as ArtistInfoModel
import requests
from typing import Optional
import logging


class ArtistInfo(CachableDb):

    _url = None
    _id = None
    _artist_id = None
    _struct: Optional[ArtistInfoModel] = None

    def __init__(self, url) -> None:
        self._url = url
        super().__init__(
            model=ArtistInfoModel,
            id_key="artist_id",
            id_value=self.artist_id
        )

    @property
    def id(self):
        if not self._id:
            pu = urlparse(self._url)
            pa = parse_qs(pu.query)
            id = "".join(pa.get("id", []))
            h = blake2b(digest_size=20)
            h.update(id.encode())
            self._id = h.hexdigest
        return self._id

    @property
    def artist_id(self):
        if not self._artist_id:
            pu = urlparse(self._url)
            pa = parse_qs(pu.query)
            self._artist_id = "".join(pa.get("id", []))
        return self._artist_id

    def _fetch(self):
        try:
            rq = requests.get(self._url)
            json = rq.json()
            assert json
            info = json.get("subsonic-response", {}).get("artistInfo", None)
            print(info)
            assert info
            mbz = info.get("musicBrainzId", None)
            assert mbz
            info["musicBrainzId"] = mbz.get("value")
            resp = ArtistInfoResponse(**info)
            info = resp.dict()
            self._struct = self.tocache({"artist_id": self.artist_id, **info})
        except AssertionError as e:
            logging.exception(e)

    @property
    def info(self) -> Optional[ArtistInfoData]:
        isLoaded = self.load()
        if not isLoaded:
            self._fetch()
        if self._struct:
            return ArtistInfoData(**self._struct.to_dict())
        return None

    @property
    def headers(self) -> dict:
        return {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,\
                image/avif,application/json,image/webp,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "no-cache",
        }

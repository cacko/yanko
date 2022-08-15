from urllib.parse import urlparse, parse_qs
from hashlib import blake2b
from yanko.sonic import ArtistInfo, ArtistInfoResponse
from yanko.core.cachable import Cachable
import requests
class ArtistInfo(Cachable):

    _url = None
    _id = None

    def __init__(self, url) -> None:
        self._url = url
        super().__init__()

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
    def info(self)-> ArtistInfo:
        isLoaded = self.load()
        if not isLoaded:
            rq = requests.get(self._url)
            json = rq.json()
            if json:
                resp = ArtistInfoResponse.from_dict(json.get("subsonic-response"))
                self._struct = resp.artistInfo
                self.tocache(self._struct)
        return self._struct

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
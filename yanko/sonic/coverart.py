from cachable import CachableFile
from urllib.parse import parse_qs, urlparse
from hashlib import blake2b
from PIL import Image


class CoverArtFile(CachableFile):

    _url: str = None
    __filename: str = None
    ICON_SIZE = (22,22)

    def __init__(self, url: str) -> None:
        self._url = url

    @property
    def filename(self):
        if not self.__filename:
            pu = urlparse(self._url)
            pa = parse_qs(pu.query)
            id = "".join(pa.get("id", []))
            if not id:
                id = self._url
            h = blake2b(digest_size=20)
            h.update(id.encode())
            self.__filename = f"{h.hexdigest()}.webp"
        return self.__filename

    @property
    def url(self):
        return self._url

    @property
    async def icon_path(self):
        await self._init()
        stem = self.storage_path.stem
        icon_path = self.storage_path.with_stem(f"{stem}_icon")
        if not icon_path.exists():
            im = Image.open(self.storage_path.as_posix())
            im.thumbnail(self.ICON_SIZE, Image.BICUBIC)
            im.save(icon_path.as_posix())
        return icon_path


    

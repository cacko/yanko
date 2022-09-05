from cachable import CachableFile
from urllib.parse import parse_qs, urlparse
from hashlib import blake2b
from PIL import Image

from yanko.core.string import file_hash


class CoverArtFile(CachableFile):

    _url: str = None
    __filename: str = None
    __filehash: str = None
    ICON_SIZE = (22, 22)
    NOT_CACHED_HASH = [
        "b9013a23400aeab42ea7dbcd89832ed41a94ab909c1a6d91f866ccd38123515e",
        "decfd6156ee93368160d76849f377ad65d540c80061a24b673b98ffbf805f026"
    ]

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
    def isCached(self) -> bool:
        return self.storage_path.exists() and self.filehash not in self.NOT_CACHED_HASH

    @property
    def filehash(self):
        if not self.__filehash:
            self.__filehash = file_hash(self.storage_path)
        return self.__filehash

    @property
    def url(self):
        return self._url

    @property
    def icon_path(self):
        self._init()
        stem = self.storage_path.stem
        icon_path = self.storage_path.with_stem(f"{stem}_icon")
        if not icon_path.exists() or file_hash(icon_path) in self.NOT_CACHED_HASH:
            im = Image.open(self.storage_path.as_posix())
            im.thumbnail(self.ICON_SIZE, Image.BICUBIC)
            im.save(icon_path.as_posix())
        return icon_path

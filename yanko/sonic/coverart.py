from cachable.storage.file import CachableFileImage
from urllib.parse import parse_qs, urlparse
from PIL import Image
from yanko.core.string import file_hash, string_hash


class CoverArtFile(CachableFileImage):

    _url: str = None
    _filename: str = None
    _filehash: str = None
    ICON_SIZE = (22, 22)
    NOT_CACHED_HASH = [
        "b9013a23400aeab42ea7dbcd89832ed41a94ab909c1a6d91f866ccd38123515e",
        "decfd6156ee93368160d76849f377ad65d540c80061a24b673b98ffbf805f026"
    ]

    def __init__(self, url: str) -> None:
        self._url = url
        super().__init__()

    @property
    def filename(self):
        if not self._filename:
            pu = urlparse(self._url)
            pa = parse_qs(pu.query)
            id = "".join(pa.get("id", []))
            if not id:
                id = self._url
            self._filename = f"{string_hash(id)}.webp"
        return self._filename

    @property
    def isCached(self) -> bool:
        return self._path.exists() and self.filehash not in self.NOT_CACHED_HASH

    @property
    def filehash(self):
        if not self._filehash:
            self._filehash = file_hash(self._path)
        return self._filehash

    @property
    def url(self):
        return self._url

    @property
    def icon_path(self):
        self._init()
        stem = self._path.stem
        icon_path = self._path.with_stem(f"{stem}_icon")
        if not icon_path.exists() or file_hash(icon_path) in self.NOT_CACHED_HASH:
            im = Image.open(self._path.as_posix())
            im.thumbnail(self.ICON_SIZE, Image.BICUBIC)
            im.save(icon_path.as_posix())
        return icon_path

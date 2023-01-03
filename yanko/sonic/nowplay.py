class NowPlayMeta(type):

    _instance = None

    def __call__(self, *args, **kwds):
        if not self._instance:
            self._instance = super().__call__(*args, **kwds)
        return self._instance


class NowPlay(object, metaclass=NowPlayMeta):
    pass

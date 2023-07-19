from .baseitem import MenuItem
from yanko.ui.icons import Label, Symbol


class ActionItemMeta(type):

    _instances: dict[str, 'ActionItem'] = {}

    def __call__(cls, title, *args, **kwds):
        if title not in cls._instances:
            cls._instances[title] = super().__call__(title, *args, **kwds)
        return cls._instances[title]

    @property
    def next(cls) -> "ActionItem":
        return cls(Label.NEXT.value, icon=Symbol.NEXT.value)

    @property
    def restart(cls) -> "ActionItem":
        return cls(Label.RESTART.value, icon=Symbol.RESTART.value)

    @property
    def previous(cls) -> "ActionItem":
        return cls(Label.PREVIOUS.value, icon=Symbol.PREVIOUS.value)

    @property
    def quit(cls) -> "ActionItem":
        return cls(Label.QUIT.value, icon=Symbol.QUIT.value)

    @property
    def random(cls) -> "ActionItem":
        return cls(Label.RANDOM.value, icon=Symbol.RANDOM.value)

    @property
    def random_album(cls) -> "ActionItem":
        return cls(
            Label.RANDOM_ALBUM.value, icon=Symbol.RANDOM_ALBUM.value
        )

    @property
    def last_added(cls) -> "ActionItem":
        return cls(Label.LAST_ADDED.value, icon=Symbol.LAST_ADDED.value)

    @property
    def artist(cls) -> "ActionItem":
        return cls(Label.ARTIST.value, icon=Symbol.ARTIST.value)

    @property
    def recent(cls) -> "ActionItem":
        return cls(Label.RECENT.value, icon=Symbol.RECENT.value)

    @property
    def most_played(cls) -> "ActionItem":
        return cls(
            Label.MOST_PLAYED.value, icon=Symbol.MOST_PLAYED.value
        )

    @property
    def share(cls) -> "ActionItem":
        return cls(Label.SHARE.value, icon=Symbol.SHARE.value)


class ActionItem(MenuItem, metaclass=ActionItemMeta):
    def __init__(
        self, title, callback=None, key=None, icon=None, dimensions=None, template=None
    ):
        template = True
        super().__init__(title, callback, key, icon, dimensions, template)

    def setAvailability(self, enabled: bool):
        self._menuitem.setEnabled_(enabled)


class MusicItem(MenuItem):

    __id = None

    def __init__(
        self,
        title,
        id,
        callback=None,
        key=None,
        icon=None,
        dimensions=None,
        template=None,
    ):
        self.__id = id
        super().__init__(
            title,
            callback=callback,
            key=key,
            icon=icon,
            dimensions=dimensions,
            template=True if template else False,
        )

    @property
    def id(self):
        return self.__id

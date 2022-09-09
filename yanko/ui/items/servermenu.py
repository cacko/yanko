from rumps import MenuItem
from yanko.ui.icons import Label, Symbol
from yanko.ui.items.actions import ActionItem


class ServerMenuMeta(type):

    __instance: "ServerMenu" = None


    def __call__(cls, *args, **kwds):
        if not cls.__instance:
            cls.__instance = type.__call__(cls, *args, **kwds)
        return cls.__instance

    def register(cls, items, callback=None) -> "ServerMenu":
        return cls(items, callback=callback)

    def action(cls, label: Label):
        return cls.__instance.get(label.value)


class ServerMenu(MenuItem, metaclass=ServerMenuMeta):
    callback = None

    def __init__(self, items=[], callback=None):
        super().__init__(
            title=Label.ADVANCED.value,
            callback=callback,
            icon=Symbol.ADVANCED.value,
            template=True,
        )

        for title, icon  in items :
            self.add(ActionItem(
                title=title,
                icon=icon,
                callback=callback
            ))

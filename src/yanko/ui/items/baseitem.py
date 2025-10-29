from rumps import MenuItem as BaseMenuItem
from AppKit import (
    NSAttributedString,  # type: ignore
    NSFont,  # type: ignore
    NSFontAttributeName,  # type: ignore
    NSBackgroundColorAttributeName,  # type: ignore
    NSColor  # type: ignore
)
from PyObjCTools.Conversion import propertyListFromPythonCollection
from enum import Enum
from typing import Optional


class Font(Enum):
    REGULAR = NSFont.fontWithName_size_("MesloLGS NF", 13)
    BOLD = NSFont.fontWithName_size_("MesloLGS NF Bold", 13)


class MenuItem(BaseMenuItem):
    def __init__(
        self, title, callback=None, key=None, icon=None, dimensions=None, template=True
    ):
        super().__init__(title, callback, key, icon, dimensions, template)
        self.setAttrTitle()

    def setAvailability(self, enabled: bool):
        self._menuitem.setEnabled_(enabled)

    def string_attributes(self, font: Font, backgroundColor: Optional[NSColor] = None):
        if backgroundColor:
            return propertyListFromPythonCollection(
                {
                    NSFontAttributeName: font.value,
                    NSBackgroundColorAttributeName: backgroundColor
                },
                conversionHelper=lambda x: x,
            )
        return propertyListFromPythonCollection(
            {
                NSFontAttributeName: font.value,
            },
            conversionHelper=lambda x: x,
        )

    def setAttrTitle(
        self,
        title=None,
        font: Optional[Font] = None,
        backgroundColor: Optional[NSColor] = None
    ):
        if not title:
            title = self.title
        if not font:
            font = Font.REGULAR
        tt = NSAttributedString.alloc().initWithString_attributes_(
            title, self.string_attributes(font, backgroundColor=backgroundColor)
        )
        self._menuitem.setAttributedTitle_(tt)

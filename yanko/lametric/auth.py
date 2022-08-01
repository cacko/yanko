import pyotp
from yanko.core.config import app_config


class OTPMeta(type):

    _instance = None

    def __call__(self, *args, **kwds):
        if not self._instance:
            self._instance = super().__call__(*args, **kwds)
        return self._instance

    @property
    def code(cls):
        return cls().getCode()

    @property
    def headers(cls):
        return cls().getHeaders()


class OTP(object, metaclass=OTPMeta):

    __totp = None

    def __init__(self) -> None:
        conf = app_config.get("lametric")
        self.__totp = pyotp.TOTP(conf.get("secret"))

    def getCode(self):
        return self.__totp.now()

    def getHeaders(self):
        return {
            "Cache-Control": "no-cache",
            'X-TOTP': self.getCode()
        }

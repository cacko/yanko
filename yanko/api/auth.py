from fastapi.exceptions import HTTPException
from starlette.requests import Request
from starlette.status import HTTP_403_FORBIDDEN
from yanko.core.config import app_config
import pyotp


ALLOWED_IPS = ["127.0.0.1"]


class Authorization:

    async def __call__(self, request: Request):
        client = request.client
        assert client
        if client.host in ALLOWED_IPS:
            return
        conf = app_config.get("api")
        otp = request.headers.get("x-totp", "")
        totp = pyotp.TOTP(conf.get("secret"))
        if not totp.verify(otp):
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN, detail="Not authenticated"
            )


check_auth = Authorization()

from bottle import request, HTTPError
import pyotp
from yanko.core.config import app_config
from functools import wraps

ALLOWED_IPS = ['127.0.0.1']

def auth_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.remote_addr in ALLOWED_IPS:
            return f(*args, **kwargs)
        conf = app_config.get("api")
        otp = request.get_header("x-totp", "")
        totp = pyotp.TOTP(conf.get("secret"))
        if not totp.verify(otp):
            err = HTTPError(403, "no")
            return err
        return f(*args, **kwargs)
    return decorated_function
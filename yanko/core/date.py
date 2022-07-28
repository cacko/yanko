from datetime import datetime, timedelta, timezone
import arrow

def seconds_to_duration(s):
    delta = timedelta(seconds=s)
    res = str(delta)
    return res[2:7]


def elapsed_duration(start):
    delta = datetime.now(tz=timezone.utc) - start
    res = str(delta)
    return res[2:7]

def isodate_encoder(d):
    pass

def isodate_decoder(d):
    ar = arrow.get(d)
    return ar.datetime
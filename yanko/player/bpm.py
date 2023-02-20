import logging
from aubio import source, tempo  # type: ignore
from numpy import median, diff
from yanko.core.shell import Shell
from pathlib import Path
from corefile import TempPath
from uuid import uuid4


class Decoder(Shell):
    executable: str = "ffmpeg"

    def __init__(self, input_path: Path, output_path: Path):
        self.args = [
            "-y",
            "-v",
            "fatal",
            "-i",
            input_path.as_posix(),
            "-acodec",
            "pcm_s16le",
            "-ar",
            "22050",
            "-ac",
            "1",
            "-af",
            "loudnorm=I=-5:LRA=15:TP=0",
            output_path.as_posix(),
        ]


def get_file_bpm(input_path: Path):
    tmp_path = TempPath(f"{uuid4().hex}.wav")
    worker = Decoder(input_path=input_path, output_path=tmp_path)
    worker.execute()
    samplerate, win_s, hop_s = 4000, 128, 64
    s = source(tmp_path.as_posix(), samplerate, hop_s)  # type: ignore
    samplerate = s.samplerate
    o = tempo("specdiff", win_s, hop_s, samplerate)
    beats = []
    total_frames = 0

    while True:
        samples, read = s()
        is_beat = o(samples)
        if is_beat:
            this_beat = o.get_last_s()
            beats.append(this_beat)
            # if o.get_confidence() > .2 and len(beats) > 2.:
            #    break
        total_frames += read
        if read < hop_s:
            break

    def beats_to_bpm(beats, input_path):
        # if enough beats are found, convert to periods then to bpm
        if len(beats) > 1:
            if len(beats) < 4:
                logging.error("few beats found in {:s}".format(input_path))
            bpms = 60./diff(beats)
            return median(bpms)
        else:
            logging.error("not enough beats found in {:s}".format(input_path))
            return 0

    return beats_to_bpm(beats, input_path)

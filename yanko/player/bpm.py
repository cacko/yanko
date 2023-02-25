import logging
from aubio import source, tempo  # type: ignore
from numpy import median, diff
from yanko.core.shell import Shell
from pathlib import Path
from corefile import TempPath
from uuid import uuid4
from librosa import (
    stft,
    istft,
    magphase,
    load,
    frames_to_time,
    time_to_frames,
    onset,
    beat,
    decompose,
)
from librosa.util import peak_pick, softmask
import numpy as np
from typing import Optional, Any
from pydantic import BaseModel
from yanko.core.bytes import nearest_bytes
from threading import Lock
from yanko.core import perftime

music_lock = Lock()


class BeatsStruct(BaseModel):
    path: Path | str
    beats: Optional[list[float]] = None
    tempo: Optional[float] = None


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


class BeatsMeta(type):

    __store_root: Optional[Path]

    def __call__(self, *args: Any, **kwds: Any) -> Any:
        return super().__call__(*args, **kwds)

    def register(cls, store_root: str):
        cls.__store_root = Path(store_root)

    @property
    def store_root(cls) -> Path:
        assert cls.__store_root
        return cls.__store_root


class Beats(object, metaclass=BeatsMeta):

    _struct: Optional[BeatsStruct] = None

    def __init__(
        self,
        path: str,
        hop_length=512,
        margin=0,
        with_vocals=False,
        force=False
    ):
        self.__requested_path = path
        self.__path = Beats.store_root / path.lstrip("/")
        self.__tmppath = TempPath(f"{uuid4().hex}.wav")
        self.__hop_length = hop_length
        self.__margin = nearest_bytes(margin)
        self.__with_vocals = with_vocals
        assert self.__path.exists()

    def __decode(self):
        worker = Decoder(input_path=self.__path, output_path=self.__tmppath)
        return worker.execute()

    @property
    def fast_bpm(self):
        self.__decode()
        samplerate, win_s, hop_s = 4000, 128, 64
        s = source(self.__tmppath.as_posix(), samplerate, hop_s)  # type: ignore
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
            total_frames += read
            if read < hop_s:
                break

        def beats_to_bpm(beats) -> int:
            if len(beats) > 1:
                if len(beats) < 4:
                    logging.error("few beats found in {:s}".format(self.__path))
                bpms = 60./diff(beats)
                return int(median(bpms))
            else:
                logging.error("not enough beats found in {:s}".format(self.__path))
                return 0

        return beats_to_bpm(beats)

    def extract(self) -> BeatsStruct:
        with music_lock:
            with perftime(f"decoding {self.__path}"):
                self.__decode()
                assert self.__tmppath.exists()
            with perftime(f"extracting beats {self.__path}"):
                y, sr = load(self.__tmppath.as_posix())
                D = stft(y)
                y_percussive = None
                if self.__with_vocals:
                    logging.info(f"Percussive margin: {self.__margin}")
                    _, D_percussive = decompose.hpss(D, margin=self.__margin)
                    y_percussive = istft(D_percussive, length=len(y))
                else:
                    logging.info(f"No vocals mode: {self.__path}")
                    S_full, phase = magphase(stft(y))
                    S_filter = decompose.nn_filter(
                        S_full,
                        aggregate=np.median,
                        metric="cosine",
                        width=int(time_to_frames(2, sr=sr)),
                    )
                    S_filter = np.minimum(S_full, S_filter)
                    margin_i, _ = 2, 10
                    power = 2

                    mask_i = softmask(
                        S_filter,
                        margin_i * (S_full - S_filter),
                        power=power
                    )
                    S_background = mask_i * S_full
                    D_background = S_background * phase
                    y_percussive = istft(D_background)

                spectral_novelty = onset.onset_strength(
                    y=y_percussive, sr=sr, hop_length=self.__hop_length
                )

                onset_frames = peak_pick(
                    spectral_novelty,
                    pre_max=3,
                    post_max=3,
                    pre_avg=3,
                    post_avg=5,
                    delta=0.5,
                    wait=10,
                )

                beat_times = frames_to_time(
                    onset_frames, hop_length=self.__hop_length
                )
                tempo = beat.tempo(y=y_percussive, sr=sr)

                return BeatsStruct(
                    beats=list(map(float, list(beat_times))),
                    tempo=float(tempo[0]),  # type: ignore
                    path=self.__requested_path,
                )

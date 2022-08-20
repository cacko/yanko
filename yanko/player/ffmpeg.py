import queue
import sys
import ffmpeg
import sounddevice
import logging
import numpy as np
import time
from yanko.player.base import BasePlayer
from yanko.sonic import Status, Action, VolumeStatus
from yanko.player.base import BasePlayer

def int_or_str(text):
    """Helper function for argument parsing."""
    try:
        return int(text)
    except ValueError:
        return text


class FFMPeg(BasePlayer):

    BUFFISIZE = 20
    BLOCKSIZE = 1024
    VOLUME_STEP = 0.05
    q: queue.Queue = None
    status: Status = None
    __volume = 1
    __muted = False

    @property
    def volume(self):
        return self.__volume

    @volume.setter
    def volume(self, val):
        self.__volume = val
        self._manager_queue.put_nowait(
            VolumeStatus(volume=self.__volume, muted=self.__muted,
                         timestamp=time.time())
        )

    @property
    def muted(self):
        return self.__muted

    @muted.setter
    def muted(self, val):
        self.__muted = val
        self._manager_queue.put_nowait(
            VolumeStatus(volume=self.__volume, muted=self.__muted,
                         timestamp=time.time())
        )

    @property
    def device(self):
        _, device = sounddevice.default.device
        return device

    def probe(self):
        try:
            info = ffmpeg.probe(self.stream_url)
        except ffmpeg.Error as e:
            sys.stderr.buffer.write(e.stderr)
        streams = info.get('streams', [])
        stream = streams[0]
        if stream.get('codec_type') != 'audio':
            logging.warning('The stream must be an audio stream')
            return Status.STOPPED

        return stream

    def play(self):

        self.q = queue.Queue(maxsize=self.BUFFISIZE)
        self.status = Status.PLAYING
        device = self.device
        device_spec = sounddevice.query_devices(device, 'output')
        channels = device_spec.get("max_output_channels")
        samplerate = float(
            device_spec.get("default_samplerate"))
        logging.debug(device_spec)
        try:
            logging.debug('Opening stream ...')
            self.last_frame = 0
            process = ffmpeg.input(self.stream_url).output(
                'pipe:',
                format='f32le',
                acodec='pcm_f32le',
                ac=channels,
                ar=samplerate,
                loglevel='quiet',
            ).run_async(pipe_stdout=True)
            stream = sounddevice.RawOutputStream(
                samplerate=samplerate, blocksize=self.BLOCKSIZE,
                device=device, channels=channels, dtype='float32',
                callback=self.callback)
            read_size = self.BLOCKSIZE * channels * stream.samplesize
            logging.debug('Buffering ...')
            for _ in range(self.BUFFISIZE):
                self.q.put_nowait(process.stdout.read(read_size))
            logging.debug('Starting Playback ...')
            with stream:
                timeout = self.BLOCKSIZE * self.BUFFISIZE / samplerate
                while True:
                    if self.status == Status.PAUSED:
                        sounddevice.sleep(50)
                    else:
                        self.q.put(process.stdout.read(
                            read_size), timeout=timeout)
                    if queue_action := self.process_queue():
                        self.status = Status.STOPPED
                        process.terminate()
                        stream.close()
                        return queue_action
            process.wait()
        except queue.Full:
            pass
        except Exception as e:
            logging.error(e)
        return Status.PLAYING

    def callback(self, outdata, frames, time, status):
        while self.status == Status.PAUSED:
            sounddevice.sleep(50)
        assert frames == self.BLOCKSIZE
        if status.output_underflow:
            logging.debug(
                'Output underflow: increase blocksize?', file=sys.stderr)
            raise sounddevice.CallbackAbort
        assert not status
        try:
            data = self.q.get_nowait()
            data_array = np.frombuffer(data, dtype='float32')
            volume_norm = data_array * (0 if self.muted else self.volume)
            outdata[:] = volume_norm.tobytes()
        except queue.Empty as e:
            logging.debug(
                'Buffer is empty: increase buffersize?', file=sys.stderr)
            raise sounddevice.CallbackAbort from e

    def process_queue(self):
        if self._queue.empty():
            return None
        command = self._queue.get_nowait()
        self._queue.task_done()
        match (command):
            case Action.RESTART:
                return self._restart()
            case Action.NEXT:
                return self._next()
            case Action.PREVIOUS:
                return self._previous()
            case Action.STOP:
                return self._stop()
            case Action.EXIT:
                return self.exit()
            case Action.PAUSE:
                self.status = Status.PAUSED
            case Action.RESUME:
                self.status = Status.RESUMED
            case Action.VOLUME_DOWN:
                self.volume = max(0, self.volume - self.VOLUME_STEP)
            case Action.VOLUME_UP:
                self.volume = min(2, self.volume + self.VOLUME_STEP)
            case Action.MUTE:
                self.muted = not self.muted
        return None

    def _stop(self):
        return Status.STOPPED

    def _restart(self):
        return self.play()

    def _next(self):
        return Status.NEXT

    def _previous(self):
        return Status.PREVIOUS

    def pause(self):
        self._queue.put_nowait(Action.PAUSE)

    def resume(self):
        self._queue.put_nowait(Action.RESUME)

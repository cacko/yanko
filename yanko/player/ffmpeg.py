import queue
import sys
import ffmpeg
import sounddevice
from yanko.player.base import BasePlayer
from yanko.sonic import Status, Action
from yanko.player.base import BasePlayer
from time import sleep
import logging


def int_or_str(text):
    """Helper function for argument parsing."""
    try:
        return int(text)
    except ValueError:
        return text

        # '-af',
        # 'loudnorm=I=-16:LRA=11:TP=-1.5',
        # '-af',
        # 'virtualbass',


class FFMPeg(BasePlayer):

    BUFFISIZE = 20
    BLOCKSIZE = 1024
    q: queue.Queue = None
    status: Status = None

    @property
    def device(self):
        _, device = sounddevice.default.device
        return device

    def probe(self):
        pass

    def play(self):

        self.q = queue.Queue(maxsize=self.BUFFISIZE)

        # try:
        #     info = ffmpeg.probe(url)
        # except ffmpeg.Error as e:
        #     sys.stderr.buffer.write(e.stderr)

        # streams = info.get('streams', [])

        # stream = streams[0]

        # if stream.get('codec_type') != 'audio':
        #     logging.warning('The stream must be an audio stream')
        #     return Status.STOPPED

        self.status = Status.PLAYING
        # channels = stream['channels']
        # samplerate = float(stream['sample_rate'])
        device = self.device
        device_spec = sounddevice.query_devices(device, 'output')
        channels = device_spec.get("max_output_channels")
        samplerate = float(device_spec.get("default_samplerate"))
        logging.debug(device_spec)

        try:
            logging.debug('Opening stream ...')
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
                        sleep(0.05)
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
            sleep(0.1)
        assert frames == self.BLOCKSIZE
        if status.output_underflow:
            logging.debug(
                'Output underflow: increase blocksize?', file=sys.stderr)
            raise sounddevice.CallbackAbort
        assert not status
        try:
            data = self.q.get_nowait()
        except queue.Empty as e:
            logging.debug(
                'Buffer is empty: increase buffersize?', file=sys.stderr)
            raise sounddevice.CallbackAbort from e
        assert len(data) == len(outdata)
        outdata[:] = data

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
        return None

    def _stop(self):
        return Status.STOPPED

    def _restart(self):
        return Status.PLAYING

    def _next(self):
        return Status.NEXT

    def _previous(self):
        return Status.PREVIOUS

    def pause(self):
        self._queue.put_nowait(Action.PAUSE)

    def resume(self):
        self._queue.put_nowait(Action.RESUME)

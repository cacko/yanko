from corethread import StoppableThread
from queue import Queue
import ffmpeg
import logging
from time import sleep


class Input(StoppableThread):

    url: str
    queue: Queue
    blocksize: int
    output_channels: int
    samplesize: int
    samplerate: int

    def __init__(
        self,
        url: str,
        outputQueue: Queue,
        blocksize: int,
        output_channels: int,
        samplesize: int,
        samplerate: int,
        *args,
        **kwargs,
    ):
        self.url = url
        self.blocksize = blocksize
        self.output_channels = output_channels
        self.samplesize = samplesize
        self.samplerate = samplerate
        self.queue = outputQueue
        super().__init__(*args, **kwargs)

    def run(self):
        logging.debug(f"Reader started for {self.url}")
        read_size = self.blocksize * self.output_channels * self.samplesize
        process = (
            ffmpeg.input(
                self.url,
                tcp_nodelay=1,
                reconnect_on_network_error=1,
                reconnect_streamed=1,
                multiple_requests=1,
                reconnect_delay_max=5,
            ).audio.filter(
                'loudnorm',  I=-16, TP=-1.5, LRA=11
            )
            .output(
                "pipe:",
                format="f32le",
                acodec="pcm_f32le",
                ac=self.output_channels,
                ar=self.samplerate,
                loglevel="quiet",
            )
            .run_async(pipe_stdout=True)
        )
        while not self.stopped():
            if self.queue.full():
                sleep(0.1)
            else:
                data = process.stdout.read(read_size)
                self.queue.put_nowait(data)
        process.terminate()

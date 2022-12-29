from corethread import StoppableThread
from queue import Queue
import ffmpeg
import logging
from time import sleep
from yanko.player.device import Device


class Input(StoppableThread):

    url: str
    queue: Queue
    samplesize: int

    def __init__(
        self,
        url: str,
        outputQueue: Queue,
        samplesize: int,
        *args,
        **kwargs,
    ):
        self.url = url
        self.samplesize = samplesize
        self.queue = outputQueue
        super().__init__(*args, **kwargs)

    def run(self):
        logging.debug(f"Reader started for {self.url}")
        read_size = Device.blocksize * Device.output_channels * self.samplesize
        timeout = Device.blocksize * Device.buffsize / Device.samplerate
        process = (
            ffmpeg.input(
                self.url,
                tcp_nodelay=1,
                reconnect_on_network_error=1,
                reconnect_streamed=1,
                multiple_requests=1,
                reconnect_delay_max=5,
            )
            .audio.filter("loudnorm", I=-16, TP=-1.5, LRA=11)
            .output(
                "pipe:",
                format="f32le",
                acodec="pcm_f32le",
                ac=Device.output_channels,
                ar=Device.samplerate,
                loglevel="quiet",
            )
            .run_async(pipe_stdout=True)
        )
        while not self.stopped():
            if self.queue.full():
                sleep(0.1)
            else:
                data = process.stdout.read(read_size)
                if data:
                    self.queue.put(data, timeout=timeout)
                else:
                    break
        process.wait()

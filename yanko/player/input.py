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
        process = (
            ffmpeg.input(
                self.url,
            )
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
                    self.queue.put_nowait(data)
                else:
                    break
        logging.debug("Reading finished.")
        process.terminate()

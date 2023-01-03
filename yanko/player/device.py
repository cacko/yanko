from typing import Optional, Any
from yanko.core.bytes import nearest_bytes
from pydantic import BaseModel, Extra, Field
import sounddevice as sd
import logging


class DeviceParams(BaseModel, extra=Extra.ignore):
    name: Optional[str] = None
    index: Optional[int] = None
    hostapi: Optional[int] = None
    max_input_channels: Optional[int] = None
    max_output_channels: Optional[int] = None
    default_low_input_latency: Optional[float] = None
    default_low_output_latency: Optional[float] = None
    default_high_input_latency: Optional[float] = None
    default_high_output_latency: Optional[float] = None
    default_samplerate: float = 44100.0
    prime_output_buffers_using_stream_callback: bool = Field(default=True)

    @property
    def blocksize(self) -> int:
        return nearest_bytes(int(self.samplerate * self.latency))

    @property
    def latency(self) -> float:
        if not self.default_high_output_latency:
            self.default_high_output_latency = 1
        if not self.default_low_output_latency:
            self.default_low_output_latency = 1
        return max(
            filter(
                lambda x: x,
                [self.default_high_output_latency, self.default_low_output_latency],
            )
        )

    @property
    def output_channels(self) -> int:
        if not self.max_output_channels:
            return 2
        return int(self.max_output_channels)

    @property
    def input_channels(self) -> int:
        if not self.max_input_channels:
            return 2
        return int(self.max_input_channels)

    @property
    def samplerate(self) -> float:
        if not self.default_samplerate:
            return 0
        return float(self.default_samplerate)

    @property
    def buffsize(self) -> int:
        return 20


class DeviceMeta(type):

    __output: Optional["Device"] = None

    def __call__(cls, *args: Any, **kwds: Any) -> Any:
        if not cls.__output:
            cls.__output = type.__call__(cls, *args, **kwds)
        return cls.__output

    def register(cls):
        cls()

    @property
    def samplesize(cls) -> int:
        return cls().get_property("samplesize")

    @property
    def blocksize(cls) -> int:
        return cls().get_property("blocksize")

    @property
    def latency(cls) -> float:
        return cls().get_property("latency")

    @property
    def output_channels(cls) -> int:
        return cls().get_property("output_channels")

    @property
    def input_channels(cls) -> int:
        return cls().get_property("input_channels")

    @property
    def samplerate(cls) -> float:
        return cls().get_property("samplerate")

    @property
    def buffsize(cls) -> int:
        return cls().get_property("buffsize")

    @property
    def index(cls) -> int:
        return cls().get_property("index")

    @property
    def name(cls) -> str:
        return cls().get_property("name")


class Device(object, metaclass=DeviceMeta):

    __device: DeviceParams

    def __init__(self, *args, **kwargs) -> None:
        _, device = sd.default.device
        device_spec = sd.query_devices(device, "output")
        self.__device = DeviceParams(**device_spec)  # type: ignore

    def get_property(self, prop: str):
        return getattr(self.__device, prop)

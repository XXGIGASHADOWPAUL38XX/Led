import socket
import struct
import threading
import time

import numpy as np

from config import DELAY_UPDATE, FREQ_BINS, SKIP_LED_NUMBERS
from frontend.components.elements.element import Element
from frontend.components.elements.element_value import ElementValue
from frontend.components.elements.dials import LinearDial
from frontend.nodes.controllers.controller_node import ControllerNode


class ESP32Node(ControllerNode):
    """Send an RGBA strip to an ESP32 over UDP using DDP.

    Input `rgba` has shape (FREQ_BINS, 4) in [0, 255]; no graph outputs.
    Configure `esp32_ip`, `ddp_port`, `led_count`, and alpha shaping controls.
    A worker starts at construction, converts RGBA to RGB with skipped-prefix
    LEDs, pads or truncates to led_count, and transmits continuously.
    Alpha processing modifies the input; `close()` stops the worker/socket."""

    nodeName = "ESP32"

    def __init__(
        self,
        rgba: np.ndarray = np.zeros((FREQ_BINS, 4), dtype=np.float32),
        power_log: float = 1.5,
        min_alpha: float = 5. / 255.,
        remove_alpha: float = 5. / 255.,
        esp32_ip: str = "192.168.1.11",
        ddp_port: int = 4048,
        led_count: int = FREQ_BINS + SKIP_LED_NUMBERS,
        render: bool = True,
        alias: str | None = None,
    ) -> None:
        super().__init__(
            rgba,
            power_log=power_log,
            min_alpha=min_alpha,
            remove_alpha=remove_alpha,
            render=render,
            alias=alias,
        )

        self.power_log = LinearDial(
            self,
            "power_log",
            0,
            10,
            ElementValue(power_log),
        )
        self.esp32_ip = Element(self, "esp32_ip", ElementValue(esp32_ip))
        self.ddp_port = Element(self, "ddp_port", ElementValue(ddp_port))
        self.led_count = Element(self, "led_count", ElementValue(led_count))

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Reuse socket, useful when restarting your app often.
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.sequence = 0
        self.running = True

        self.worker = threading.Thread(target=self._write_loop, daemon=True)
        self.worker.start()

    def c_update(self):
        """
        Kept for compatibility with your node system.

        The actual sending is done in the background thread so the ESP32 keeps
        receiving frames even if c_update timing is irregular.
        """
        pass

    def _write_loop(self):
        frame_period = DELAY_UPDATE / 1000.0
        next_time = time.monotonic()

        while self.running:
            try:
                frame = self._get_rgb_frame()
                self._send_ddp_frame(frame)
            except Exception as exc:
                print(f"[ESP32] Failed to send frame: {exc}")

            next_time += frame_period
            delay = next_time - time.monotonic()

            if delay > 0:
                time.sleep(delay)
            else:
                # If the backend is late, do not accumulate latency.
                next_time = time.monotonic()

    def _get_rgb_frame(self) -> bytes:
        """
        Converts the current rgb Element value to exactly led_count * 3 bytes.

        Expected input shape:
            (led_count, 3)

        If the input has fewer LEDs, it pads black.
        If the input has too many LEDs, it truncates.
        """
        self.process_rgba()
        rgb_array = np.clip(self.rgb.value, 0, 255).astype(np.uint8)

        if rgb_array.ndim != 2 or rgb_array.shape[1] != 3:
            raise ValueError(
                f"Expected rgb array shape (N, 3), got {rgb_array.shape}"
            )

        led_count = int(self.led_count.value)

        if rgb_array.shape[0] < led_count:
            padded = np.zeros((led_count, 3), dtype=np.uint8)
            padded[: rgb_array.shape[0]] = rgb_array
            rgb_array = padded
        elif rgb_array.shape[0] > led_count:
            rgb_array = rgb_array[:led_count]

        return rgb_array.tobytes()

    def _send_ddp_frame(self, rgb_bytes: bytes):
        """
        Sends one full RGB frame to the ESP32 using DDP over UDP.

        The firmware listens on UDP port 4048 by default.
        Payload is raw RGB bytes:
            LED 0: R, G, B
            LED 1: R, G, B
            ...
        """
        led_count = int(self.led_count.value)
        expected_len = led_count * 3

        if len(rgb_bytes) != expected_len:
            raise ValueError(
                f"Expected {expected_len} RGB bytes, got {len(rgb_bytes)}"
            )

        flags = 0x41
        sequence = self.sequence & 0x0F
        data_type = 0x01
        destination = 0x01
        data_offset = 0
        data_len = len(rgb_bytes)

        ddp_header = struct.pack(
            ">BBBBIH",
            flags,
            sequence,
            data_type,
            destination,
            data_offset,
            data_len,
        )

        packet = ddp_header + rgb_bytes

        self.socket.sendto(
            packet,
            (self.esp32_ip.value, int(self.ddp_port.value)),
        )

        self.sequence = (self.sequence + 1) & 0x0F

    def close(self):
        self.running = False

        try:
            self.worker.join(timeout=1.0)
        except RuntimeError:
            pass

        try:
            self.socket.close()
        except OSError:
            pass

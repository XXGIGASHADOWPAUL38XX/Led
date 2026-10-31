"""Run a short local song excerpt through an isolated graph without audio output."""
import asyncio
from pathlib import Path
import os
from math import gcd

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

from backend.api.runtime import Runtime
from config import CHUNK_SIZE, SAMPLE_RATE


class Audition:
    def __init__(self):
        path = Path(os.environ.get("JEV_AUDIO_PATH", Path(__file__).resolve().parents[2] / "RYOQUCHA - CAUSTICS.mp3"))
        with sf.SoundFile(path) as song:
            song.seek(max(0, (len(song) - 4 * song.samplerate) // 2))
            audio = song.read(4 * song.samplerate, dtype="float32", always_2d=True)
            rate = song.samplerate
        if not audio.size:
            raise ValueError("Jev audition song is empty; set JEV_AUDIO_PATH to a local audio file")
        divisor = gcd(rate, SAMPLE_RATE)
        audio = resample_poly(audio, SAMPLE_RATE // divisor, rate // divisor, axis=0)
        self.audio = np.repeat(audio, 2, axis=1) if audio.shape[1] == 1 else audio[:, :2]
        self.song = path.name

    async def measure(self, graph, catalog):
        runtime = Runtime(catalog, preview=True)
        try:
            runtime.load(graph)
            streams = [node for node in runtime.nodes.values() if node.nodeName in {"StreamPlayer", "StreamMic"}]
            for node in runtime.players.values():
                node.audio.value = self.audio
                node.sample_rate.value = SAMPLE_RATE
            # Replacing stream callbacks with decoded blocks keeps devices and workers idle.
            hop = min((node.chunk.value.shape[-1] for node in streams), default=CHUNK_SIZE)
            outputs = [(node.name(), name) for node in runtime.nodes.values()
                       for name, port in node.pending_terminals.items() if port["io"] == "out"][-24:]
            records = {f"{node}.{name}": [] for node, name in outputs}
            sample_every = max(1, len(self.audio) // hop // 16)
            audio_levels = []
            for frame, offset in enumerate(range(0, len(self.audio), hop)):
                for node in streams:
                    if node.nodeName == "StreamPlayer" and node.audio_in._value_source is None:
                        continue
                    size = node.chunk.value.shape[-1]
                    audio = self.audio if node.nodeName == "StreamMic" else node.audio_in.value
                    block = audio[offset:offset + size]
                    block = np.pad(block, ((0, size - len(block)), (0, 0)))
                    node.chunk.value[:] = block.T if node.nodeName == "StreamPlayer" else block.mean(axis=1)
                for node in runtime.updates:
                    if node.nodeName not in {"SCPlaylistPlayer", "StreamPlayer", "StreamMic", "ESP32"}:
                        try:
                            node.c_update()
                        except Exception as error:
                            raise ValueError(f"Silent audition failed at {node.name()}: {error}") from error
                if frame % sample_every == 0:
                    audio_levels.append(float(np.sqrt(np.mean(self.audio[offset:offset + hop] ** 2))))
                    for node_id, name in outputs:
                        value = np.asarray(runtime.element(node_id, name).value)
                        if not value.size or value.dtype.kind not in "biuf":
                            continue
                        sampled = np.asarray(value.reshape(-1)[np.linspace(0, value.size - 1, min(512, value.size), dtype=int)], dtype=float)
                        if not np.isfinite(value).all():
                            raise ValueError(f"Non-finite output during audition: {node_id}.{name}")
                        item = {"shape": list(value.shape), "min": float(sampled.min()),
                                "max": float(sampled.max()), "mean": float(sampled.mean()),
                                "std": float(sampled.std())}
                        if value.ndim == 2 and value.shape[-1] in (3, 4):
                            item["channels"] = value.mean(axis=0, dtype=float).tolist()
                        records[f"{node_id}.{name}"].append(item)
                if frame % 8 == 0:
                    await asyncio.sleep(0)
            result = {}
            for name, samples in records.items():
                if samples:
                    result[name] = {**samples[-1], "min": min(item["min"] for item in samples),
                                    "max": max(item["max"] for item in samples),
                                    "mean_over_time": [round(item["mean"], 5) for item in samples]}
                    result[name]["temporal_std"] = float(np.std([item["mean"] for item in samples]))
                    if "channels" in samples[-1]:
                        result[name]["channels_over_time"] = [item["channels"] for item in samples]
            return {"song": self.song, "seconds": len(self.audio) / SAMPLE_RATE,
                    "hop_samples": hop, "outputs_limit": 24, "playback_and_hardware": "disabled",
                    "streams": {node.name(): {"chunk_size": int(node.chunk.value.shape[-1]),
                        "audio_connected": node.nodeName == "StreamMic" or node.audio_in._value_source is not None}
                        for node in streams},
                    "audio_rms_over_time": audio_levels, "outputs": result}
        finally:
            runtime.close()

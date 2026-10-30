from backend.components.elements.parameters import Parameter, DataElement, SequenceElement
import hashlib
import os
import pickle
import tempfile
import threading
import time
from urllib.parse import unquote, urlparse

import numpy as np
import soundfile as sf
import static_ffmpeg
from queue import SimpleQueue, Empty
from yt_dlp import YoutubeDL

from backend.updatable.updatable import AudioUpdatable
from config import SAMPLE_RATE
from backend.components.elements.element_value import ElementValue

from backend.overrides.CNode import CNode, OfflineCNode

class SCPlaylistPlayer(CNode, AudioUpdatable):
    """Download, cache, and control playback of a SoundCloud playlist.

    No input terminals; configure `playlist_url`, browser/profile cookies,
    `prefetch_seconds`, and `cache`. Outputs `audio` shaped (samples, 2),
    `sample_rate` in Hz, and changing `enqueue_token` connect to StreamPlayer
    inputs. Play/seek publishes remaining track audio; pause publishes empty
    audio. Background loading starts for a nonempty URL and supports offline
    playlist analysis nodes. Call `start()` to load the playlist; worker
    results are applied by `c_update()` on the processing thread."""

    nodeName = "SCPlaylistPlayer"
    entries_cache_path = os.path.expanduser("~/.cache/led/sc_playlist_entries.pkl")
    tracks_cache_path = os.path.expanduser("~/.cache/led/sc_playlist_tracks.pkl")

    def __init__(self, playlist_url="https://soundcloud.com/trg-electro/sets/led", browser="chrome", profile="Default", prefetch_seconds=10, cache=True, offline_pipelines=None, alias=None):
        super().__init__(self.nodeName, {"audio": {"io": "out"}, "sample_rate": {"io": "out"}, "enqueue_token": {"io": "out"}}, alias=alias)
        self.playlist_url = Parameter(self, 'playlist_url', playlist_url, kind='text')
        self.browser = Parameter(self, 'browser', browser, kind='text')
        self.profile = Parameter(self, 'profile', profile, kind='text')
        self.prefetch_seconds = Parameter(self, 'prefetch_seconds', float(prefetch_seconds), minimum=0, maximum=300)
        self.cache = Parameter(self, 'cache', bool(cache), kind='boolean')
        self.audio = DataElement(self, 'audio', ElementValue(np.zeros((0, 2), dtype=np.float32)))
        self.sample_rate = DataElement(self, 'sample_rate', ElementValue(0))
        self.enqueue_token = DataElement(self, 'enqueue_token', ElementValue(0))
        self.offline_pipelines = SequenceElement(self, 'offline_pipelines', list(offline_pipelines or []))
        self._events = SimpleQueue()
        self.loading = False
        self._thread = None
        self._stop_event = threading.Event()
        self._data_lock = threading.Lock()
        self._tracks = []
        self._entries = []
        self._seek_ratios = []
        self._current_track_index = -1
        self._is_playing = False
        self._track_started_at = 0.0
        self._track_start_position = 0.0

    def _ydl_opts(self):
        opts = {"quiet": True, "format": "bestaudio[abr<=128]/bestaudio"}
        browser = str(self.browser.value).strip()
        profile = str(self.profile.value).strip()
        if browser:
            opts["cookiesfrombrowser"] = (browser, profile) if profile else (browser,)
        return opts

    @staticmethod
    def _load_cache(path):
        try:
            with open(path, "rb") as f:
                return pickle.load(f)
        except Exception:
            return {}

    @staticmethod
    def _save_cache(path, cache):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(cache, f)

    @classmethod
    def _track_cache_key(cls, track_url, opts):
        return hashlib.sha256(f"{track_url}|{repr(sorted(opts.items()))}".encode()).hexdigest()

    @classmethod
    def _download_track(cls, entry, opts, use_cache=True, cache=None):
        track_url = entry.get("url")
        if not track_url:
            return np.zeros((0, 2), dtype=np.float32), SAMPLE_RATE
        key = cls._track_cache_key(track_url, opts)
        cache = cache if cache is not None else (cls._load_cache(cls.tracks_cache_path) if use_cache else {})
        if key in cache:
            return cache[key]
        with tempfile.TemporaryDirectory() as tmp:
            static_ffmpeg.add_paths()
            download_opts = dict(opts)
            download_opts["outtmpl"] = os.path.join(tmp, "track.%(ext)s")
            download_opts["postprocessors"] = [{"key": "FFmpegExtractAudio", "preferredcodec": "wav", "preferredquality": "0"}]
            YoutubeDL(download_opts).download([track_url])
            audio, sample_rate = sf.read(os.path.join(tmp, "track.wav"))
            audio = np.asarray(audio, dtype=np.float32)
            if audio.ndim == 1:
                audio = np.repeat(audio[:, None], 2, axis=1)
            elif audio.shape[1] == 1:
                audio = np.repeat(audio, 2, axis=1)
            result = audio, int(sample_rate)
        cache[key] = result
        return result

    @staticmethod
    def _entry_metadata(entry):
        url = entry.get("url", "")
        parts = [part for part in urlparse(url).path.split("/") if part]
        return {
            "artist": unquote(parts[0].replace("-", " ")) if parts else entry.get("uploader", ""),
            "title": unquote(parts[1].replace("-", " ")) if len(parts) > 1 else entry.get("title", ""),
            "duration": float(entry.get("duration") or 0),
        }

    @staticmethod
    def _extract_entries(url, opts):
        playlist_opts = dict(opts)
        playlist_opts.update(extract_flat="in_playlist", lazy_playlist=True)
        with YoutubeDL(playlist_opts) as ydl:
            return ydl.extract_info(url, download=False).get("entries", [])

    def _worker(self):
        try:
            opts = self._ydl_opts()
            playlist_url = str(self.playlist_url.value).strip()
            entries_cache = self._load_cache(self.entries_cache_path) if bool(self.cache.value) else {}
            entries_key = hashlib.sha256(f"{playlist_url}|{repr(sorted(opts.items()))}".encode()).hexdigest()
            entries = entries_cache.get(entries_key)
            if entries is None:
                entries = self._extract_entries(playlist_url, opts)
                entries_cache[entries_key] = entries
                if bool(self.cache.value):
                    self._save_cache(self.entries_cache_path, entries_cache)
        except Exception:
            self._events.put(("loading", False))
            return
        entries = list(entries)
        self._events.put(("playlist", entries))
        track_cache = self._load_cache(self.tracks_cache_path) if bool(self.cache.value) else {}
        prefetched_seconds = 0.0
        for index, entry in enumerate(entries):
            if self._stop_event.is_set():
                break
            if prefetched_seconds >= float(self.prefetch_seconds.value):
                break
            try:
                track = self._download_track(entry, opts, bool(self.cache.value), track_cache)
            except Exception:
                continue
            prefetched_seconds += float(entry.get("duration") or 0.0)
            self._events.put(("track", (entry, track)))
        if bool(self.cache.value):
            self._save_cache(self.tracks_cache_path, track_cache)
        self._events.put(("loading", False))

    def add_music(self, entry):
        threading.Thread(target=self._add_worker, args=(entry,), daemon=True).start()

    def _add_worker(self, entry):
        try:
            opts = self._ydl_opts()
            track_cache = self._load_cache(self.tracks_cache_path) if bool(self.cache.value) else {}
            track = self._download_track(entry, opts, bool(self.cache.value), track_cache)
            if bool(self.cache.value):
                self._save_cache(self.tracks_cache_path, track_cache)
        except Exception:
            self._events.put(("loading", False))
            return
        self._events.put(("add", (entry, track)))

    def remove_music(self, index):
        with self._data_lock:
            if not 0 <= index < len(self._entries):
                return
            self._entries.pop(index)
            self._tracks.pop(index)
            self._seek_ratios.pop(index)

    def _drain_events(self):
        while True:
            try:
                kind, value = self._events.get_nowait()
            except Empty:
                return
            if kind == "loading":
                self.loading = value
            elif kind == "playlist":
                self._entries = value
                self._tracks = [None] * len(value)
                self._seek_ratios = [0.0] * len(value)
            elif kind == "add":
                entry, track = value
                self._entries.append(entry)
                self._tracks.append(track)
                self._seek_ratios.append(0.0)
                self.calculate_offline_pipelines()
            elif kind == "track":
                entry, track = value
                index = next((at for at, item in enumerate(self._entries) if item is entry), None)
                if index is not None:
                    self._tracks[index] = track
                self.calculate_offline_pipelines()

    def on_play_requested(self, index):
        with self._data_lock:
            track = self._tracks[index]
            ratio = self._seek_ratios[index]
            if ratio >= 1:
                ratio = self._seek_ratios[index] = 0.0
            self._current_track_index = index
        if track is None:
            return
        audio, sample_rate = track
        start = int(ratio * audio.shape[0])
        self._track_start_position = start / float(sample_rate or SAMPLE_RATE)
        self._track_started_at = time.monotonic()
        self.audio.value = audio[start:]
        self.sample_rate.value = int(sample_rate)
        self.enqueue_token.value = int(self.enqueue_token.value) + 1
        self._is_playing = True
        self.update_offline_pipeline_position(index, self._track_start_position)

    def on_pause_requested(self, index):
        if index != self._current_track_index:
            return
        self.audio.value = np.zeros((0, 2), dtype=np.float32)
        self.enqueue_token.value = int(self.enqueue_token.value) + 1
        self._seek_ratios[index] = self._current_position_ratio()
        self._track_start_position = self._current_position()
        self._is_playing = False

    def on_seek_requested(self, index, ratio):
        with self._data_lock:
            self._seek_ratios[index] = float(ratio)
            track = self._tracks[index]
        if index != self._current_track_index or track is None:
            return
        audio, sample_rate = track
        start = int(float(ratio) * audio.shape[0])
        self._track_start_position = start / float(sample_rate or SAMPLE_RATE)
        self._track_started_at = time.monotonic()
        self.update_offline_pipeline_position(index, self._track_start_position)
        if not self._is_playing:
            return
        self.audio.value = audio[start:]
        self.sample_rate.value = int(sample_rate)
        self.enqueue_token.value = int(self.enqueue_token.value) + 1

    def track_duration(self, index):
        track = self._tracks[index]
        if track is None:
            return float(self._entries[index].get("duration") or 0)
        audio, sample_rate = track
        return audio.shape[0] / float(sample_rate or SAMPLE_RATE)

    def _current_position_ratio(self):
        if self._current_track_index < 0:
            return 0.0
        duration = self.track_duration(self._current_track_index)
        return min(1.0, self._current_position() / duration) if duration else 0.0

    def _current_position(self):
        if self._current_track_index < 0:
            return 0.0
        position = self._track_start_position + (time.monotonic() - self._track_started_at if self._is_playing else 0)
        return min(self.track_duration(self._current_track_index), position)

    def _update_playback_position(self):
        if self._current_track_index < 0 or not self._is_playing:
            return
        position = self._current_position()
        ratio = self._current_position_ratio()
        with self._data_lock:
            self._seek_ratios[self._current_track_index] = ratio
        self.update_offline_pipeline_position(self._current_track_index, position)
        if ratio >= 1:
            self.on_pause_requested(self._current_track_index)

    def get_offline_pipeline_nodes(self):
        return [node for node in self.get_nodes() if isinstance(node, OfflineCNode)]

    def calculate_offline_pipelines(self, *_args):
        with self._data_lock:
            tracks = list(self._tracks)
        if not tracks or any(track is None for track in tracks):
            return
        for node in self.offline_pipelines:
            node.calculate_playlist(tracks)

    def update_offline_pipeline_index(self, track_index, audio_index):
        for node in self.offline_pipelines:
            node.update_audio_index(track_index, audio_index)

    def update_offline_pipeline_position(self, track_index, position):
        for node in self.offline_pipelines:
            node.update_audio_position(track_index, position)

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            return
        self.loading = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        self.audio.value = np.zeros((0, 2), dtype=np.float32)
        self.enqueue_token.value = int(self.enqueue_token.value) + 1
        self._is_playing = False

    def c_update(self):
        self._drain_events()
        self._update_playback_position()
        return self.audio

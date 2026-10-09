from frontend.components.elements.dials import LinearDial
from frontend.components.elements.switch.switch import Switch
from frontend.components.elements.parameters import DataElement
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
from PyQt5 import QtCore
from yt_dlp import YoutubeDL

from backend.updatable.updatable import AudioUpdatable
from config import SAMPLE_RATE
from frontend.components.elements.element_value import ElementValue
from frontend.components.elements.player.playlist_player import PlaylistPlayer
from frontend.components.elements.textedit.textedit import TextEdit
from frontend.nodes.playlist_player.soundcloud.api import search_tracks
from frontend.overrides.CNode import CNode, OfflineCNode


class SCPlaylistPlayer(CNode, AudioUpdatable):
    """Download, cache, and control playback of a SoundCloud playlist.

    No input terminals; configure `playlist_url`, browser/profile cookies,
    `prefetch_seconds`, and `cache`. Outputs `audio` shaped (samples, 2),
    `sample_rate` in Hz, and changing `enqueue_token` connect to StreamPlayer
    inputs. Play/seek publishes remaining track audio; pause publishes empty
    audio. Background loading starts for a nonempty URL and supports offline
    playlist analysis nodes."""

    nodeName = "SCPlaylistPlayer"
    entries_cache_path = os.path.expanduser("~/.cache/led/sc_playlist_entries.pkl")
    tracks_cache_path = os.path.expanduser("~/.cache/led/sc_playlist_tracks.pkl")
    metadataReady = QtCore.pyqtSignal(object)
    trackLoaded = QtCore.pyqtSignal(int)

    def __init__(self, playlist_url="https://soundcloud.com/trg-electro/sets/led4", browser="chrome", profile="Default", prefetch_seconds=10, cache=True, render=True, alias=None):
        super().__init__(self.nodeName, {"audio": {"io": "out"}, "sample_rate": {"io": "out"}, "enqueue_token": {"io": "out"}}, render=render, alias=alias)
        AudioUpdatable.__init__(self)
        self.playlist_url = TextEdit(self, "playlist_url", ElementValue(playlist_url))
        self.browser = TextEdit(self, "browser", ElementValue(browser))
        self.profile = TextEdit(self, "profile", ElementValue(profile))
        self.prefetch_seconds = LinearDial(self, 'prefetch_seconds', 0, 300, ElementValue(float(prefetch_seconds)))
        self.cache = Switch(self, 'cache', ElementValue(bool(cache)))
        self.audio = DataElement(self, 'audio', ElementValue(np.zeros((0, 2), dtype=np.float32)))
        self.sample_rate = DataElement(self, 'sample_rate', ElementValue(0))
        self.enqueue_token = DataElement(self, 'enqueue_token', ElementValue(0))
        self.playlist_player = PlaylistPlayer([], self, self.get_offline_pipeline_nodes)
        self.elements.append(self.playlist_player)
        self.playlist_player.playRequested.connect(self.on_play_requested)
        self.playlist_player.pauseRequested.connect(self.on_pause_requested)
        self.playlist_player.seekRequested.connect(self.on_seek_requested)
        self.playlist_player.searchRequested.connect(self.search_music)
        self.playlist_player.searchResults.connect(self.playlist_player.set_search_results)
        self.playlist_player.addRequested.connect(self.add_music)
        self.playlist_player.removeRequested.connect(self.remove_music)
        self.playlist_player.offlinePipelineAdded.connect(self.calculate_offline_pipelines)
        self.metadataReady.connect(self.on_metadata_ready)
        self.trackLoaded.connect(self.on_track_loaded)
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
        if playlist_url:
            self.playlist_player.set_loading(True)
            self.start()

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
            self.playlist_player.loadingChanged.emit(False)
            return
        with self._data_lock:
            self._entries = list(entries)
            self._tracks = [None] * len(entries)
            self._seek_ratios = [0.0] * len(entries)
        self.metadataReady.emit([self._entry_metadata(entry) for entry in entries])
        track_cache = self._load_cache(self.tracks_cache_path) if bool(self.cache.value) else {}
        prefetched_seconds = 0.0
        for index, entry in enumerate(entries):
            if self._stop_event.is_set():
                break
            if prefetched_seconds >= float(self.prefetch_seconds.value):
                break
            with self._data_lock:
                self._tracks[index] = self._download_track(entry, opts, bool(self.cache.value), track_cache)
            prefetched_seconds += float(entry.get("duration") or 0.0)
            self.trackLoaded.emit(index)
        if bool(self.cache.value):
            self._save_cache(self.tracks_cache_path, track_cache)
        self.playlist_player.loadingChanged.emit(False)

    def search_music(self, query):
        self.playlist_player.set_loading(True)
        threading.Thread(target=self._search_worker, args=(query,), daemon=True).start()

    def _search_worker(self, query):
        try:
            results = search_tracks(query, limit=5)
        except Exception:
            results = []
        self.playlist_player.searchResults.emit(results)

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
            self.playlist_player.loadingChanged.emit(False)
            return
        with self._data_lock:
            self._entries.append(entry)
            self._tracks.append(track)
            self._seek_ratios.append(0.0)
            index = len(self._entries) - 1
            metadata = [self._entry_metadata(item) for item in self._entries]
        self.metadataReady.emit(metadata)
        self.trackLoaded.emit(index)

    def remove_music(self, index):
        with self._data_lock:
            if not 0 <= index < len(self._entries):
                return
            self._entries.pop(index)
            self._tracks.pop(index)
            self._seek_ratios.pop(index)
            metadata = [self._entry_metadata(item) for item in self._entries]
        self.metadataReady.emit(metadata)

    def on_metadata_ready(self, metadata):
        self.playlist_player.set_playlist_metadata(metadata)
        if not metadata:
            self.playlist_player.set_loading(False)
        self._refresh_node_ui_geometry()

    def on_track_loaded(self, index):
        with self._data_lock:
            track = self._tracks[index]
        if track is not None and index < len(self.playlist_player.music_players):
            audio, sample_rate = track
            player = self.playlist_player.music_players[index]
            player.music_length = audio.shape[0] / float(sample_rate or SAMPLE_RATE)
            player.music_length_label.setText(player.format_time(player.music_length))
        self.playlist_player.set_loaded(index, True)
        with self._data_lock:
            finished = index == len(self._tracks) - 1
        if finished:
            self.playlist_player.set_loading(False)
            self.calculate_offline_pipelines()
        self._refresh_node_ui_geometry()

    def _refresh_node_ui_geometry(self):
        self.playlist_player.adjustSize()
        if self._elements_proxy is not None and "audio" in self.terminals:
            self.refresh_terminal_positions()

    def on_play_requested(self, index):
        with self._data_lock:
            track = self._tracks[index]
            ratio = self._seek_ratios[index]
            self._current_track_index = index
        if track is None:
            return
        audio, sample_rate = track
        start = int(ratio * audio.shape[0])
        self._track_start_position = start / float(sample_rate or SAMPLE_RATE)
        self._track_started_at = time.monotonic()
        self.playlist_player.set_position(index, self._track_start_position)
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
        self._is_playing = False

    def on_seek_requested(self, index, ratio):
        with self._data_lock:
            self._seek_ratios[index] = float(ratio)
            track = self._tracks[index]
        if index != self._current_track_index or not self._is_playing or track is None:
            return
        audio, sample_rate = track
        start = int(float(ratio) * audio.shape[0])
        self._track_start_position = start / float(sample_rate or SAMPLE_RATE)
        self._track_started_at = time.monotonic()
        self.playlist_player.set_position(index, self._track_start_position)
        self.audio.value = audio[start:]
        self.sample_rate.value = int(sample_rate)
        self.enqueue_token.value = int(self.enqueue_token.value) + 1
        self.update_offline_pipeline_position(index, self._track_start_position)

    def _current_position_ratio(self):
        if self._current_track_index < 0:
            return 0.0
        with self._data_lock:
            track = self._tracks[self._current_track_index]
        if track is None:
            return 0.0
        audio, sample_rate = track
        duration = audio.shape[0] / float(sample_rate or SAMPLE_RATE)
        return min(1.0, self._current_position() / duration) if duration else 0.0

    def _current_position(self):
        return self._track_start_position if not self._is_playing else self._track_start_position + time.monotonic() - self._track_started_at

    def _update_playback_position(self):
        if self._current_track_index < 0 or not self._is_playing:
            return
        position = self._current_position()
        self.playlist_player.set_position(self._current_track_index, position)
        ratio = self._current_position_ratio()
        with self._data_lock:
            self._seek_ratios[self._current_track_index] = ratio
        self.update_offline_pipeline_position(self._current_track_index, position)

    def get_offline_pipeline_nodes(self):
        return [node for node in self.get_flowchart_visible_nodes() if isinstance(node, OfflineCNode)]

    def calculate_offline_pipelines(self, *_args):
        with self._data_lock:
            tracks = list(self._tracks)
        if not tracks or any(track is None for track in tracks):
            return
        for node in self.playlist_player.offline_pipelines():
            node.calculate_playlist(tracks)

    def update_offline_pipeline_index(self, track_index, audio_index):
        for node in self.playlist_player.offline_pipelines():
            node.update_audio_index(track_index, audio_index)

    def update_offline_pipeline_position(self, track_index, position):
        for node in self.playlist_player.offline_pipelines():
            node.update_audio_position(track_index, position)

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        self.audio.value = np.zeros((0, 2), dtype=np.float32)
        self.enqueue_token.value = int(self.enqueue_token.value) + 1
        self._is_playing = False

    def c_update(self):
        self._update_playback_position()
        return self.audio

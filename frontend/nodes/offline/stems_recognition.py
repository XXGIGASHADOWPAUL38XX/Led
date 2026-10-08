import numpy as np
from scipy.spatial.distance import cdist

from frontend.components.elements.dials import LinearDial
from frontend.components.elements.element import Element
from frontend.components.elements.element_value import ElementValue
from frontend.components.elements.trigger.trigger import TriggerElement
from frontend.overrides.CNode import OfflineCNode


def fourier_transform(audio, sample_rate, frame_ms=25, hop_ms=10, n_bands=200):
    """Window audio and return amplitudes in logarithmic frequency bands."""
    n = round(sample_rate * frame_ms / 1000)
    hop = round(sample_rate * hop_ms / 1000)
    count = max(0, 1 + (len(audio) - n) // hop)
    frames = np.stack(
        [audio[i * hop:i * hop + n] for i in range(count)]
    ) if count else np.empty((0, n), dtype=np.float32)
    frames *= np.hanning(n)

    fft_frequencies = np.fft.rfftfreq(n, 1 / sample_rate)
    fft_amplitudes = 2 * np.abs(np.fft.rfft(frames, axis=-1)) / n
    fft_amplitudes[:, 0] = 0  # ignore DC

    frequencies = np.geomspace(20, sample_rate / 2, n_bands)
    edges = np.r_[0, np.sqrt(frequencies[:-1] * frequencies[1:]), np.inf]
    bands = np.digitize(fft_frequencies, edges) - 1
    amplitudes = np.stack([
        np.bincount(bands, weights=frame, minlength=n_bands)[:n_bands]
        for frame in fft_amplitudes
    ]) if count else np.empty((0, n_bands))
    return frequencies, amplitudes


def group_amplitudes_frames(amplitudes, nb_frames=2):
    if nb_frames <= 0:
        raise ValueError("nb_frames must be positive")

    length, n_bands = amplitudes.shape
    margin = (-length) % nb_frames
    if margin:
        amplitudes = np.vstack((amplitudes, np.zeros((margin, n_bands))))

    # Keep adjacent FFT frames in the same group.  Reshaping to
    # (nb_frames, n_groups, ...) would interleave the frames instead.
    return amplitudes.reshape(-1, nb_frames, n_bands).mean(axis=1)


def get_abs_difference(amplitudes):
    return np.clip(amplitudes[1:] - amplitudes[:-1], 0, 1)


def filter_abs_difference(abs_difference, threshold=2):
    mask = abs_difference.sum(axis=0) < threshold
    abs_difference[:, mask] = 0
    return abs_difference


def roll_to_normalize_freq(amplitudes):
    x, n = amplitudes.shape

    nonzero = amplitudes >= 0.0002
    first = np.argmax(nonzero, axis=1)
    first = np.where(nonzero.any(axis=1), first, 0)

    indices = (np.arange(n)[None, :] + first[:, None]) % n
    return np.take_along_axis(amplitudes, indices, axis=1)


def get_similarity(abs_difference, threshold=0.5):
    # indices = np.array([1691, 1711, 1733, 1753]) - 1
    # x = abs_difference[[1691, 1711, 1733, 1753]]
    x = np.power(abs_difference, 3)
    row_sums = x.sum(axis=1)
    pair_sums = row_sums[:, None] + row_sums[None, :]
    l1 = cdist(x, x, metric="cityblock")

    intersection = ((pair_sums - l1) * 0.5) + 1e-8
    union = ((pair_sums + l1) * 0.5) + 1e-6

    similarity = np.divide(
        intersection,
        union,
        out=np.ones_like(union, dtype=float),
        where=union != 0,
    )
    np.fill_diagonal(similarity, 0)
    mask = similarity > threshold
    return np.where(np.triu(mask, k=1))


def get_stems(amplitudes, frequencies, rows, cols):
    if rows.size == 0:
        return np.empty((0, amplitudes.shape[1]), dtype=float)

    ## Vstack them to be same length n.max() with -1
    s = np.r_[0, np.flatnonzero(rows[1:] != rows[:-1]) + 1]
    n = np.diff(np.r_[s, cols.size])
    m = n.max()

    c = np.zeros((s.size, m), dtype=cols.dtype) - 1
    c[np.arange(m) < n[:, None]] = cols + 1

    out = np.full((c.shape[0], amplitudes.shape[1]), np.inf)
    for idx in c.T:
        valid = idx != -1
        out[valid] = np.minimum(out[valid], amplitudes[idx[valid]])
    return out


def filter_stems(stems, rows, cols, max_distance=100, level_threshold=0.25):
    # get_stems produces one stem per consecutive group in sorted rows.
    _, group = np.unique(rows, return_inverse=True)
    distant = np.abs(cols - rows) > max_distance
    counts = np.bincount(group[distant], minlength=stems.shape[0])
    mask = (np.sum(stems, axis=1) > level_threshold) & (counts > 10)
    return stems[mask], mask


def _find_stem_indexes(normalized_freq_pitches, stems):
    normalized_freq_pitches = np.power(normalized_freq_pitches, 1.55)
    present = np.all(
        normalized_freq_pitches[:, None, :] >= stems[None, :, :], axis=2
    )
    return [np.flatnonzero(present[:, i]) for i in range(stems.shape[0])]


def find_stems(audio, sample_rate, analysis_nb_frames=2, similarity_threshold=0.5, level_threshold=0.5, min_presence_count=11, hop_ms=10):
    return [indexes for indexes, _ in find_stem_data(
        audio, sample_rate, analysis_nb_frames, similarity_threshold,
        level_threshold, min_presence_count, hop_ms,
    )]


def find_stem_data(audio, sample_rate, analysis_nb_frames=2, similarity_threshold=0.5, level_threshold=0.5, min_presence_count=11, hop_ms=10):
    frequencies, amplitudes = fourier_transform(audio, sample_rate, hop_ms=hop_ms)
    average_grouped_amplitudes = group_amplitudes_frames(amplitudes, analysis_nb_frames)
    normalized_freq_pitches = roll_to_normalize_freq(average_grouped_amplitudes)
    f_abs_difference = filter_abs_difference(normalized_freq_pitches)
    rows, cols = get_similarity(f_abs_difference, similarity_threshold)
    stems = get_stems(average_grouped_amplitudes, frequencies, rows, cols)
    f_stems, stem_mask = filter_stems(stems, rows, cols, level_threshold=level_threshold)
    stems_recognition = _find_stem_indexes(average_grouped_amplitudes, f_stems)
    keep = np.array([len(indices) >= min_presence_count for indices in stems_recognition], dtype=bool)
    f_stems = f_stems[keep]
    stems_recognition = [indices for indices, valid in zip(stems_recognition, keep) if valid]
    return [
        (indices, float(np.mean(stem)))
        for indices, stem in zip(stems_recognition, f_stems)
    ]



class StemsRecognitionNode(OfflineCNode):
    """Analyze complete tracks for recurring spectral groups and presence.

    Receives (audio, sample_rate) tracks through `calculate_playlist`, not
    input terminals. Playback position updates dynamic `stem_N` outputs,
    each a one-element 0/1 presence array, plus internal average amplitudes.
    Configure `analysis_nb_frames`, `hop_ms`, similarity/level thresholds,
    and `min_presence_count`; this detects spectral groups rather than
    producing separated audio tracks."""

    nodeName = "StemsRecognition"

    def __init__(self, analysis_nb_frames=5, similarity_threshold=0.5, level_threshold=0.25, min_presence_count=11, hop_ms=10, render=True, alias=None):
        super().__init__(self.nodeName, {}, render=render, alias=alias)
        self.analysis_nb_frames = LinearDial(self, "analysis_nb_frames", 1, 10, ElementValue(analysis_nb_frames))
        self.similarity_threshold = LinearDial(self, "similarity_threshold", 0, 1, ElementValue(similarity_threshold))
        self.level_threshold = LinearDial(self, "level_threshold", 0.4, 1, ElementValue(level_threshold))
        self.min_presence_count = LinearDial(self, "min_presence_count", 1, 100, ElementValue(min_presence_count))
        self.hop_ms = LinearDial(self, "hop_ms", 1, 20, ElementValue(hop_ms))
        self.triggers = []
        self.avg_amplitudes = []
        self.stem_outputs = self.triggers
        self._track_stems = []
        self._tracks = []
        self._add_stem_output()

    def calculate_playlist(self, tracks):
        self._tracks = tracks
        self._track_stems = [find_stem_data(
            audio.mean(axis=1), sample_rate, round(self.analysis_nb_frames.value),
            self.similarity_threshold.value, self.level_threshold.value,
            round(self.min_presence_count.value),
            self.hop_ms.value,
        ) for audio, sample_rate in tracks]

    def update_audio_index(self, track_index, audio_index):
        stems = self._track_stems[track_index] if track_index < len(self._track_stems) else []
        indexes = [item[0] for item in stems]
        averages = [item[1] for item in stems]
        while len(self.triggers) < len(indexes):
            trigger, average = self._add_stem_output()
            if self._elements_container is not None:
                self._elements_container.layout().addWidget(average)
                self._elements_container.layout().addWidget(trigger)
        for index, (average, trigger) in enumerate(zip(self.avg_amplitudes, self.triggers)):
            if index < len(indexes):
                average.value = averages[index]
                trigger.value = np.array([int(audio_index in indexes[index])])
                average.show()
                trigger.show()
            else:
                average.value = 0.0
                trigger.value = np.zeros(1)
                average.hide()
                trigger.hide()

    def _add_stem_output(self):
        index = len(self.triggers)
        terminal_name = f"stem_{index}"
        self.pending_terminals[terminal_name] = {"io": "out"}
        if terminal_name not in self.terminals:
            self.addTerminal(terminal_name, io="out")
        average = Element(self, f"{terminal_name}_avg_amplitude", ElementValue(0.0))
        trigger = TriggerElement(self, terminal_name, ElementValue(np.zeros(1)))
        setattr(self, terminal_name, trigger)
        self.avg_amplitudes.append(average)
        self.triggers.append(trigger)
        return trigger, average

    def update_audio_position(self, track_index, position):
        group_duration = round(self.analysis_nb_frames.value) * self.hop_ms.value / 1000
        self.update_audio_index(track_index, int(float(position) / group_duration))

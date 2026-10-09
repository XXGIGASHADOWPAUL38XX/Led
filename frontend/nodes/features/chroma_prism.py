from frontend.components.elements.parameters import DataElement
import numpy as np

from backend.pipelines.pipeline import VisualPipeline
from config import FREQ_BINS, MAX_FREQUENCY, MIN_FREQUENCY
from frontend.components.elements import AnalysableElement
from frontend.components.elements.element_value import ElementValue
from frontend.overrides.CNode import CNode


class ChromaPrismNode(VisualPipeline, CNode):
    """Convert spectrum and audio features into animated bars and RGBA colors.

    Inputs: `amplitudes`, 12-bin `chroma`, scalar-array `spectral_centroid`
    (Hz), `spectral_flux`, `onset_strength`, `entropy`, `zero_crossing_rate`,
    `crest_factor`, and `mid_side_energy` shaped (2,). Outputs `data` shaped
    (FREQ_BINS,) in [0, 1] and `brushes` shaped (FREQ_BINS, 4) in [0, 255]
    update with spectrum memory and animation phase each visual frame."""

    nodeName = "ChromaPrism"

    def __init__(
        self,
        amplitudes=np.zeros(FREQ_BINS),
        chroma=np.zeros(12),
        spectral_centroid=np.zeros(1),
        spectral_flux=np.zeros(1),
        onset_strength=np.zeros(1),
        entropy=np.zeros(1),
        zero_crossing_rate=np.zeros(1),
        crest_factor=np.zeros(1),
        mid_side_energy=np.zeros(2),
        render: bool = True,
        alias: str | None = None,
    ) -> None:
        terminals = {
            "amplitudes": {"io": "in"},
            "chroma": {"io": "in"},
            "spectral_centroid": {"io": "in"},
            "spectral_flux": {"io": "in"},
            "onset_strength": {"io": "in"},
            "entropy": {"io": "in"},
            "zero_crossing_rate": {"io": "in"},
            "crest_factor": {"io": "in"},
            "mid_side_energy": {"io": "in"},
            "data": {"io": "out"},
            "brushes": {"io": "out"},
        }
        VisualPipeline.__init__(self)
        CNode.__init__(self, node_name=self.nodeName, terminals=terminals, render=render, alias=alias)

        self.amplitudes = DataElement(self, 'amplitudes', ElementValue(amplitudes))
        self.chroma = DataElement(self, 'chroma', ElementValue(chroma))
        self.spectral_centroid = DataElement(self, 'spectral_centroid', ElementValue(spectral_centroid))
        self.spectral_flux = DataElement(self, 'spectral_flux', ElementValue(spectral_flux))
        self.onset_strength = DataElement(self, 'onset_strength', ElementValue(onset_strength))
        self.entropy = DataElement(self, 'entropy', ElementValue(entropy))
        self.zero_crossing_rate = DataElement(self, 'zero_crossing_rate', ElementValue(zero_crossing_rate))
        self.crest_factor = DataElement(self, 'crest_factor', ElementValue(crest_factor))
        self.mid_side_energy = DataElement(self, 'mid_side_energy', ElementValue(mid_side_energy))
        self.data = AnalysableElement(self, "data", ElementValue(np.zeros(FREQ_BINS)))
        self.brushes = DataElement(self, 'brushes', ElementValue(np.zeros((FREQ_BINS, 4))))

        self.memory = np.zeros(FREQ_BINS)
        self.phase = 0.0
        self.positions = np.linspace(0.0, 1.0, FREQ_BINS)
        self.pitch_classes = np.floor(self.positions * 12).astype(int) % 12
        self.palette = np.array(
            [
                [255, 65, 72],
                [255, 122, 48],
                [255, 190, 64],
                [196, 224, 70],
                [94, 220, 105],
                [45, 214, 170],
                [38, 202, 228],
                [53, 142, 255],
                [92, 94, 255],
                [160, 76, 240],
                [222, 74, 194],
                [255, 72, 128],
            ],
            dtype=float,
        )

    @staticmethod
    def _scalar(value) -> float:
        value = np.asarray(value, dtype=float).reshape(-1)
        return float(value[0]) if value.size else 0.0

    def _spectrum(self):
        spectrum = np.asarray(self.amplitudes.value, dtype=float).reshape(-1)
        if spectrum.size == 0:
            return np.zeros(FREQ_BINS)
        if spectrum.size != FREQ_BINS:
            spectrum = np.interp(
                self.positions,
                np.linspace(0.0, 1.0, spectrum.size),
                spectrum,
            )
        spectrum = np.nan_to_num(spectrum, nan=0.0, posinf=0.0, neginf=0.0)
        return np.clip(spectrum / (np.max(spectrum) + 1e-12), 0.0, 1.0)

    def _chroma_strengths(self):
        chroma = np.asarray(self.chroma.value, dtype=float).reshape(-1)
        if chroma.size == 0:
            return np.zeros(12)
        if chroma.size != 12:
            chroma = np.interp(np.linspace(0.0, 1.0, 12), np.linspace(0.0, 1.0, max(chroma.size, 1)), chroma)
        chroma = np.nan_to_num(np.maximum(chroma, 0.0))
        return chroma / (np.max(chroma) + 1e-12)

    def c_update(self):
        spectrum = self._spectrum()
        chroma = self._chroma_strengths()
        flux = np.clip(self._scalar(self.spectral_flux.value) * 5.0, 0.0, 1.0)
        onset = np.clip(self._scalar(self.onset_strength.value) * 8.0, 0.0, 1.0)
        entropy = np.clip(self._scalar(self.entropy.value), 0.0, 1.0)
        zcr = np.clip(self._scalar(self.zero_crossing_rate.value) * 4.0, 0.0, 1.0)
        crest = np.clip((self._scalar(self.crest_factor.value) - 1.0) / 5.0, 0.0, 1.0)

        mid_side = np.asarray(self.mid_side_energy.value, dtype=float).reshape(-1)
        mid = float(mid_side[0]) if mid_side.size > 0 else 0.0
        side = float(mid_side[1]) if mid_side.size > 1 else 0.0
        stereo_width = np.clip(side / (mid + side + 1e-12), 0.0, 1.0)

        centroid = self._scalar(self.spectral_centroid.value)
        centroid_position = np.clip((centroid - MIN_FREQUENCY) / (MAX_FREQUENCY - MIN_FREQUENCY), 0.0, 1.0)
        focus_width = 0.015 + entropy * 0.14 + stereo_width * 0.05
        focus = np.exp(-((self.positions - centroid_position) ** 2) / focus_width)

        self.memory[:] = (self.memory * (0.78 + entropy * 0.12)) + (spectrum * (0.22 - entropy * 0.12))
        self.phase = (self.phase + 0.012 + onset * 0.05 + stereo_width * 0.025) % 1.0

        wave = 0.5 + 0.5 * np.sin((self.positions * (2.0 + stereo_width * 4.0 + zcr * 5.0) + self.phase) * 2.0 * np.pi)
        arch = 0.12 + 0.88 * np.sin(np.pi * self.positions) ** (0.9 - stereo_width * 0.35)
        pitch_lift = chroma[self.pitch_classes]
        heights = (
            self.memory ** (0.72 - crest * 0.28)
            + focus * (0.18 + flux * 0.24)
            + pitch_lift * (0.10 + onset * 0.22)
            + wave * (0.05 + entropy * 0.10 + zcr * 0.08)
        )
        self.data.value[:] = np.clip(heights * arch * (0.82 + onset * 0.55), 0.01, 1.0)

        colors = self.palette[self.pitch_classes] * (0.48 + pitch_lift[:, None] * 0.42 + focus[:, None] * 0.35)
        colors += np.array([255.0, 245.0, 210.0]) * onset * focus[:, None] * 0.7
        colors *= (0.82 + wave[:, None] * (0.24 + zcr * 0.18) + stereo_width * 0.18)
        self.brushes.value[:, :3] = np.clip(colors, 0.0, 255.0)
        self.brushes.value[:, 3] = np.clip(38.0 + self.data.value * 190.0 + flux * 45.0 + onset * 70.0, 0.0, 255.0)

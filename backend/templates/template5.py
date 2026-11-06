import numpy as np
from backend.pipelines.pipeline import VisualPipeline
from backend.updatable.updatable import audio_updatable_objects, visual_updatable_objects
from config import DELAY_UPDATE, FREQ_BINS, SAMPLE_RATE
from backend.components.elements import AnalysableElement
from backend.components.elements.element import Element
from backend.components.elements.element_value import ElementValue
from backend.nodes.buffer import BufferNode
from backend.nodes.controllers import ESP32Node
from backend.nodes.pipelines import AmplitudesNode
from backend.nodes.pipelines.auditory.filter.low_filter import LowFilterPipelineNode
from backend.nodes.pipelines.auditory.rms import RMSPipelineNode
from backend.nodes.pipelines.transforms.value_transformer import ValueTransformerPipelineNode
from backend.nodes.playlist_player import SCPlaylistPlayer
from backend.nodes.simple import ConstantArrayNode
from backend.nodes.stream.stream_player_node import StreamPlayerNode
from backend.nodes.visual import BarGraphChartNode
from backend.overrides.CNode import CNode

class HarmonicTideNode(VisualPipeline, CNode):
    """Animate spectrum bars and RGB colors with bass-driven waves.

    Inputs `amplitudes` (spectrum vector) and `bass_drive` (one-element array
    in [0, 1]) produce `data` shaped (FREQ_BINS,) in [0, 1] and `brushes`
    shaped (FREQ_BINS, 4) in [0, 255]. Each visual update smooths spectrum,
    tracks bass attacks, and advances an animated color/intensity wave."""
    nodeName = 'HarmonicTide'

    def __init__(self, amplitudes=np.zeros(FREQ_BINS), bass_drive=np.zeros(1), alias: str | None=None) -> None:
        terminals = {'amplitudes': {'io': 'in'}, 'bass_drive': {'io': 'in'}, 'data': {'io': 'out'}, 'brushes': {'io': 'out'}}
        VisualPipeline.__init__(self)
        CNode.__init__(self, node_name=self.nodeName, terminals=terminals, alias=alias)
        self.amplitudes = Element(self, 'amplitudes', ElementValue(amplitudes))
        self.bass_drive = Element(self, 'bass_drive', ElementValue(bass_drive))
        self.data = AnalysableElement(self, 'data', ElementValue(np.zeros(FREQ_BINS)))
        self.brushes = Element(self, 'brushes', ElementValue(np.zeros((FREQ_BINS, 4))))
        self.phase = 0.0
        self.previous_bass = 0.0
        self.kick_pulse = 0.0
        self.memory = np.zeros(FREQ_BINS)
        self.positions = np.linspace(0.0, 1.0, FREQ_BINS)
        self.arch = 0.18 + 0.82 * np.sin(np.pi * self.positions)
        low_color = np.array([18.0, 235.0, 198.0])
        high_color = np.array([238.0, 74.0, 146.0])
        mix = self.positions[:, None]
        self.base_colors = low_color * (1.0 - mix) + high_color * mix

    @staticmethod
    def _scalar(value) -> float:
        value = np.asarray(value, dtype=float).reshape(-1)
        return float(value[0]) if value.size else 0.0

    def _spectrum(self) -> np.ndarray:
        spectrum = np.asarray(self.amplitudes.value, dtype=float).reshape(-1)
        if spectrum.size == 0:
            return np.zeros(FREQ_BINS)
        if spectrum.size != FREQ_BINS:
            source_x = np.linspace(0.0, 1.0, spectrum.size)
            target_x = np.linspace(0.0, 1.0, FREQ_BINS)
            spectrum = np.interp(target_x, source_x, spectrum)
        spectrum = np.nan_to_num(spectrum, nan=0.0, posinf=0.0, neginf=0.0)
        ceiling = max(float(np.max(spectrum)), 1e-06)
        return np.clip(spectrum / ceiling, 0.0, 1.0)

    def c_update(self):
        spectrum = self._spectrum()
        bass = np.clip(self._scalar(self.bass_drive.value), 0.0, 1.0)
        bass_attack = max(0.0, bass - self.previous_bass)
        self.previous_bass = bass
        self.kick_pulse = max(self.kick_pulse * 0.72, bass_attack * 3.8)
        self.memory[:] = self.memory * 0.84 + spectrum * 0.16
        self.phase = (self.phase + 0.025 + bass * 0.1 + self.kick_pulse * 0.18) % 1.0
        tide = 0.5 + 0.5 * np.sin((self.positions + self.phase) * 3.0 * np.pi)
        heights = np.clip(self.memory ** 0.6 * (0.75 + bass * 0.7) + tide * (0.12 + self.kick_pulse * 0.34), 0.02, 1.0)
        self.data.value[:] = heights * self.arch
        brightness = (0.58 + 0.42 * tide + 0.22 * bass + 0.35 * self.kick_pulse)[:, None]
        self.brushes.value[:, :3] = np.clip(self.base_colors * brightness, 0.0, 255.0)
        intensity = self.data.value
        intensity_min = float(np.min(intensity))
        intensity_max = float(np.max(intensity))
        if intensity_max > intensity_min:
            intensity = (intensity - intensity_min) / (intensity_max - intensity_min)
        alpha = np.clip(20.0 + intensity * (190.0 + self.kick_pulse * 95.0), 0.0, 255.0)
        self.brushes.value[:, 3] = alpha

def build_nodes():
    sc_playlist_player_node = SCPlaylistPlayer(cache=True, prefetch_seconds=18, alias='soundcloud_playlist')
    analysis_chunk_size = int(SAMPLE_RATE * DELAY_UPDATE / 1000)
    stream_player_node = StreamPlayerNode(audio_in=sc_playlist_player_node.audio, sample_rate_in=sc_playlist_player_node.sample_rate, enqueue_token=sc_playlist_player_node.enqueue_token, chunk_size=analysis_chunk_size, alias='stream_player')
    buffer_node = BufferNode(indata=stream_player_node.chunk, chunk_size=stream_player_node.chunk.value.shape[1], length=analysis_chunk_size, alias='analysis_buffer')
    amplitudes_node = AmplitudesNode(buffer=buffer_node.data, fft_size=analysis_chunk_size, powering=0.35, alias='amplitudes')
    low_filter_node = LowFilterPipelineNode(buffer_data=buffer_node.data, lowpass_freq=220, alias='bass_filter')
    bass_rms_node = RMSPipelineNode(buffer_data=low_filter_node.data, alias='bass_rms')
    bass_drive_node = ValueTransformerPipelineNode(input_value=bass_rms_node.data, input_value_interval=[0.02, 0.5], output_value_interval=[0, 1], alias='bass_drive')
    harmonic_tide_node = HarmonicTideNode(amplitudes=amplitudes_node.data, bass_drive=bass_drive_node.output_value, alias='harmonic_tide')
    constant_array_one_node = ConstantArrayNode(input_value=1, length=FREQ_BINS, alias='constant_array_one')
    esp32_node = ESP32Node(rgba=harmonic_tide_node.brushes, alias='esp32_node')
    tide_chart_node = BarGraphChartNode(data=constant_array_one_node.data, number_points=FREQ_BINS, brushes=harmonic_tide_node.brushes, alias='tide_chart')
    return [node for node in locals().values() if isinstance(node, CNode)]

"""Aurora Pulse: a restrained, music-reactive spectrum scene."""
import numpy as np
from backend.updatable.updatable import audio_updatable_objects, visual_updatable_objects
from config import DELAY_UPDATE, FREQ_BINS, SAMPLE_RATE
from backend.nodes.buffer import BufferNode
from backend.nodes.features.entropy import EntropyNode
from backend.nodes.features.spectral_centroid import SpectralCentroidNode
from backend.nodes.pipelines import AmplitudesNode
from backend.nodes.pipelines.transforms.operator_node import OperatorPipelineNode
from backend.nodes.pipelines.visual.rgba_pipeline import RGBAPipelineNode
from backend.nodes.playlist_player import SCPlaylistPlayer
from backend.nodes.rainbow import GradiantNode, RainbowNode
from backend.nodes.stream.stream_player_node import StreamPlayerNode
from backend.nodes.visual import BarGraphChartNode, SingleLineChartNode
from backend.overrides.CNode import CNode

def build_nodes():
    playlist = SCPlaylistPlayer(cache=True, prefetch_seconds=12, alias='aurora_playlist')
    analysis_size = int(SAMPLE_RATE * DELAY_UPDATE / 1000)
    stream = StreamPlayerNode(audio_in=playlist.audio, sample_rate_in=playlist.sample_rate, enqueue_token=playlist.enqueue_token, chunk_size=analysis_size, alias='aurora_stream')
    buffer = BufferNode(indata=stream.chunk, chunk_size=stream.chunk.value.shape[1], length=analysis_size, alias='aurora_buffer')
    amplitudes = AmplitudesNode(buffer=buffer.data, fft_size=analysis_size, normalisation=True, powering=0.25, alias='aurora_spectrum')
    entropy = EntropyNode(amplitudes=amplitudes.data, alias='aurora_entropy')
    centroid = SpectralCentroidNode(amplitudes=amplitudes.data, frequencies=amplitudes.frequencies, alias='aurora_centroid')
    glow = OperatorPipelineNode(arguments=[amplitudes.data, '*', entropy.data], length=FREQ_BINS, alias='aurora_glow')
    gradient = GradiantNode(color_in=(22, 235, 214), color_out=(245, 52, 167), cycle=1.4, alias='aurora_gradient')
    rainbow = RainbowNode(gradiant=gradient.data, inv_fraction=0.22, alias='aurora_rainbow')
    rgba = RGBAPipelineNode(rgb=rainbow.data, alpha=glow.data, alias='aurora_rgba')
    spectrum = BarGraphChartNode(data=np.ones(amplitudes.data.value.shape[-1]), brushes=rgba.rgba, number_points=FREQ_BINS, alias='aurora_spectrum_view')
    entropy_chart = SingleLineChartNode(input_data=entropy.data, alias='aurora_entropy_chart')
    centroid_chart = SingleLineChartNode(input_data=centroid.data, alias='aurora_centroid_chart')
    glow_chart = SingleLineChartNode(input_data=glow.data, alias='aurora_glow_chart')
    return [node for node in locals().values() if isinstance(node, CNode)]

import numpy as np
from backend.updatable.updatable import audio_updatable_objects, visual_updatable_objects
from config import DELAY_UPDATE, SAMPLE_RATE
from backend.nodes.buffer import BufferNode
from backend.nodes.pipelines import AmplitudesNode
from backend.nodes.pipelines.transforms.peakfilter_node import PeakFilterNode
from backend.nodes.pipelines.visual import SingleColorNode, RGBAPipelineNode, RollingNode
from backend.nodes.playlist_player import SCPlaylistPlayer
from backend.nodes.stream.stream_player_node import StreamPlayerNode
from backend.nodes.visual import BarGraphChartNode
from backend.overrides.CNode import CNode

def build_nodes():
    sc_playlist_player_node = SCPlaylistPlayer(cache=True, alias='sc_playlist_player_node')
    analysis_chunk_size = int(SAMPLE_RATE * DELAY_UPDATE / 1000)
    stream_player_node = StreamPlayerNode(audio_in=sc_playlist_player_node.audio, sample_rate_in=sc_playlist_player_node.sample_rate, enqueue_token=sc_playlist_player_node.enqueue_token, chunk_size=analysis_chunk_size, alias='stream_player_node')
    buffer_node = BufferNode(indata=stream_player_node.chunk, chunk_size=stream_player_node.chunk.value.shape[1], length=analysis_chunk_size, alias='buffer_node')
    amplitudes_node = AmplitudesNode(buffer=buffer_node.data, fft_size=analysis_chunk_size, alias='amplitudes_node')
    peak_filter_node = PeakFilterNode(input_value=amplitudes_node.data, peaks_to_keep=3, alias='peak_filter_node')
    single_color_node = SingleColorNode()
    rgba_pipeline_node = RGBAPipelineNode(rgb=single_color_node.data, alpha=np.ones(amplitudes_node.data.value.shape[-1]))
    spectogram_chart_node = BarGraphChartNode(data=peak_filter_node.data.value, number_points=amplitudes_node.data.value.shape[0], brushes=rgba_pipeline_node.rgba)
    return [node for node in locals().values() if isinstance(node, CNode)]

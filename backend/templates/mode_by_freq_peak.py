import numpy as np
from backend.updatable.updatable import audio_updatable_objects, visual_updatable_objects
from config import DELAY_UPDATE, SAMPLE_RATE
from backend.nodes.buffer import BufferNode
from backend.group_nodes import CenterToEdgeNode, EdgeToCenterTriggerNode, SinglePeakTriggerNode
from backend.nodes.pipelines.amplitudes.avg_frequencies import AvgFrequenciesNode
from backend.nodes.pipelines.transforms.operator_node import OperatorPipelineNode
from backend.nodes.pipelines.visual import SingleColorNode, RGBAPipelineNode
from backend.nodes.playlist_player import SCPlaylistPlayer
from backend.nodes.offline.stems_recognition import StemsRecognitionNode
from backend.nodes.routing_node import GatheringNode, RoutingNode
from backend.nodes.stream.stream_player_node import StreamPlayerNode
from backend.nodes.visual import BarGraphChartNode
from backend.overrides.CNode import CNode

def build_nodes():
    sc_playlist_player_node = SCPlaylistPlayer(cache=True, alias='sc_playlist_player_node')
    stems_recognition_node = StemsRecognitionNode(analysis_nb_frames=3, similarity_threshold=1, level_threshold=0.8, min_presence_count=20, hop_ms=10, alias='stems_recognition_node')
    analysis_chunk_size = int(SAMPLE_RATE * DELAY_UPDATE / 1000)
    stream_player_node = StreamPlayerNode(audio_in=sc_playlist_player_node.audio, sample_rate_in=sc_playlist_player_node.sample_rate, enqueue_token=sc_playlist_player_node.enqueue_token, chunk_size=analysis_chunk_size, alias='stream_player_node')
    buffer_node = BufferNode(indata=stream_player_node.chunk, chunk_size=stream_player_node.chunk.value.shape[1], length=analysis_chunk_size, alias='buffer_node')
    single_peak_trigger_node = SinglePeakTriggerNode(buffer_data=buffer_node.data, alias='single_peak_trigger_node')
    average_frequency_node = AvgFrequenciesNode(input_amplitudes=single_peak_trigger_node.data, input_frequencies=single_peak_trigger_node.amplitudes_node.frequencies, alias='average_peak_frequency_node')
    low_trigger_node = OperatorPipelineNode(arguments=['(', average_frequency_node.data, '<', 600, ')', '&', '(', average_frequency_node.data, '>', 0, ')'], length=1, alias='low_trigger_node')
    mid_trigger_node = OperatorPipelineNode(arguments=['(', average_frequency_node.data, '>', 600, ')', '&', '(', average_frequency_node.data, '<', 2000, ')'], length=1, alias='mid_trigger_node')
    high_trigger_node = OperatorPipelineNode(arguments=[average_frequency_node.data, '>', 2000], length=1, alias='high_trigger_node')
    bass_edge_trigger_node = EdgeToCenterTriggerNode(input_trigger=stems_recognition_node.stem_outputs[0], length=single_peak_trigger_node.data.value.shape[-1], decay_length=5, alias='bass_edge_to_center_node')
    medium_center_trigger_node = CenterToEdgeNode(input_trigger=mid_trigger_node.data, length=single_peak_trigger_node.data.value.shape[-1], decay_length=5, alias='medium_center_to_edge_node')
    trigger_alpha_node = OperatorPipelineNode(arguments=['(', bass_edge_trigger_node.data, '+', medium_center_trigger_node.data, ')', '/', 2], length=single_peak_trigger_node.data.value.shape[-1], alias='bass_medium_trigger_alpha_node')
    low_color_node = SingleColorNode(color=(0, 100, 255), number_points=single_peak_trigger_node.data.value.shape[-1], alias='low_frequency_color_node')
    mid_color_node = SingleColorNode(color=(0, 255, 100), number_points=single_peak_trigger_node.data.value.shape[-1], alias='mid_frequency_color_node')
    high_color_node = SingleColorNode(color=(255, 60, 0), number_points=single_peak_trigger_node.data.value.shape[-1], alias='high_frequency_color_node')
    routing_node = RoutingNode(operator_nodes=[low_trigger_node, mid_trigger_node, high_trigger_node], alias='frequency_routing_node')
    gathering_node = GatheringNode(input_datas=[low_color_node.data, mid_color_node.data, high_color_node.data], input_booleans=[low_trigger_node.data, mid_trigger_node.data, high_trigger_node.data], alias='frequency_color_gathering_node')
    rgba_pipeline_node = RGBAPipelineNode(rgb=gathering_node.data, alpha=trigger_alpha_node.data)
    spectogram_chart_node = BarGraphChartNode(data=np.ones(single_peak_trigger_node.data.value.shape[-1]), number_points=single_peak_trigger_node.data.value.shape[0], brushes=rgba_pipeline_node.rgba)
    return [node for node in locals().values() if isinstance(node, CNode)]

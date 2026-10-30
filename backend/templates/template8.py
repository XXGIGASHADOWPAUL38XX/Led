import numpy as np
from backend.updatable.updatable import audio_updatable_objects, visual_updatable_objects
from config import DELAY_UPDATE, SAMPLE_RATE
from backend.enums.gradiant.gradiant_mode import GradiantMode
from backend.group_nodes import KickDecayNode
from backend.nodes.broadcast.broadcast_addition import BroadcastAdditionNode
from backend.nodes.broadcast.broadcast_indexes import BroadcastIndexesNode
from backend.nodes.buffer import BufferNode
from backend.nodes.controllers import ESP32Node
from backend.nodes.function import FunctionNode
from backend.nodes.pipelines import AmplitudesNode
from backend.nodes.pipelines.amplitudes.avg_frequencies import AvgFrequenciesNode
from backend.nodes.pipelines.amplitudes.linear_amplitude_transformer_node import LinearAmplitudesTransformerNode
from backend.nodes.pipelines.transforms.operator_node import OperatorPipelineNode
from backend.nodes.pipelines.transforms.value_transformer import ValueTransformerPipelineNode
from backend.nodes.pipelines.visual import SingleColorNode, RGBAPipelineNode, RollingNode
from backend.nodes.playlist_player import SCPlaylistPlayer
from backend.nodes.rainbow import GradiantNode, RainbowNode
from backend.nodes.stream.stream_player_node import StreamPlayerNode
from backend.nodes.visual import BarGraphChartNode
from backend.nodes.window.window import WindowNode
from backend.nodes.windows_fcts import DecreasingAvgWindowFct
from backend.overrides.CNode import CNode

def build_nodes():
    sc_playlist_player_node = SCPlaylistPlayer(cache=True, alias='sc_playlist_player_node')
    analysis_chunk_size = int(SAMPLE_RATE * DELAY_UPDATE / 1000)
    stream_player_node = StreamPlayerNode(audio_in=sc_playlist_player_node.audio, sample_rate_in=sc_playlist_player_node.sample_rate, enqueue_token=sc_playlist_player_node.enqueue_token, chunk_size=analysis_chunk_size, alias='stream_player_node')
    buffer_node = BufferNode(indata=stream_player_node.chunk, chunk_size=stream_player_node.chunk.value.shape[1], length=analysis_chunk_size, alias='buffer_node')
    amplitudes_node = AmplitudesNode(buffer=buffer_node.data, fft_size=analysis_chunk_size, powering=0.4, alias='amplitudes_node')
    amplitudes_node_transformed = ValueTransformerPipelineNode(input_value=amplitudes_node.data, input_value_interval=(-15, 25), output_value_interval=(0, 1))
    avg_frequencies_node = AvgFrequenciesNode(input_amplitudes=amplitudes_node_transformed.output_value, input_frequencies=amplitudes_node.frequencies, alias='avg_frequencies_node')
    avg_frequencies_correlation_offset = ValueTransformerPipelineNode(input_value=avg_frequencies_node.data, input_value_interval=[800, 1000], output_value_interval=[0, 0], alias='avg_frequencies_correlation_offset')
    amplitudes_transformer_node = LinearAmplitudesTransformerNode(input_data=amplitudes_node_transformed.output_value, correlation_offset=avg_frequencies_correlation_offset.output_value, correlation_step=0.02, alias='amplitudes_transformer_node')
    amplitudes_node_normalized = ValueTransformerPipelineNode(input_value=amplitudes_transformer_node.data, input_value_interval=[0, 1], output_value_interval=[0, 1], alias='amplitudes_node_normalized')
    exp_amplitudes = OperatorPipelineNode(arguments=[amplitudes_node_normalized.output_value, '**', '7'], length=amplitudes_node_normalized.output_value.value.shape[-1])
    avg_frequencies_color_level = ValueTransformerPipelineNode(input_value=avg_frequencies_node.data, input_value_interval=[800, 1000], output_value_interval=[0, 1], alias='avg_frequencies_color_level')
    avg_frequencies_color_level_window = WindowNode(input_data=avg_frequencies_color_level.output_value, length=5, shape=(1,), alias='avg_frequencies_color_level_window')
    avg_frequencies_color_level_window_fct = DecreasingAvgWindowFct(window=avg_frequencies_color_level_window, avg_axis=0, alias='avg_frequencies_color_level_window_fct')
    function_node = FunctionNode(points=[(0, 1), (0.15, 0), (0.5, 1), (0.85, 0), (1, 1)])
    broadcast_indexes_node = BroadcastIndexesNode(input_data=exp_amplitudes.data, indexes=function_node.data, alias='broadcast_node')
    gradiant_node_zero = GradiantNode(color_in=(255, 0, 135), color_out=(50, 50, 200), cycle=1, alias='gradiant_node_zero')
    rainbow_node_zero = RainbowNode(gradiant=gradiant_node_zero.data, mode=GradiantMode.MIRROR, alias='rainbow_node_zero')
    gradiant_node_one = GradiantNode(color_in=(200, 50, 50), color_out=(255, 200, 0), cycle=1, alias='gradiant_node_one')
    rainbow_node_one = RainbowNode(gradiant=gradiant_node_one.data, mode=GradiantMode.MIRROR, alias='rainbow_node_one')
    rolling_rainbow_node_zero = RollingNode(input_data=rainbow_node_zero.data, roll_speed=1, alias='rolling_rainbow_node_zero')
    rolling_rainbow_node_one = RollingNode(input_data=rainbow_node_one.data, roll_speed=-1, alias='rolling_rainbow_node_one')
    broadcast_addition = BroadcastAdditionNode(input_data=rolling_rainbow_node_zero.data, secondary_data=rolling_rainbow_node_one.data, level=avg_frequencies_color_level_window_fct.data)
    rgba_pipeline_node = RGBAPipelineNode(rgb=broadcast_addition.data, alpha=broadcast_indexes_node.data)
    spectogram_chart_node = BarGraphChartNode(data=np.ones(broadcast_indexes_node.data.value.shape[-1]), number_points=amplitudes_node.data.value.shape[0], brushes=rgba_pipeline_node.rgba)
    return [node for node in locals().values() if isinstance(node, CNode)]

from config import DELAY_UPDATE, SAMPLE_RATE
from backend.enums.gradiant.gradiant_mode import GradiantMode
from backend.group_nodes import KickDecayNode
from backend.nodes.function.outbounds_fct import OutboundsFctNode
from backend.nodes.pipelines.transforms.operator_node import OperatorPipelineNode
from backend.nodes.pipelines.transforms.value_transformer import ValueTransformerPipelineNode
from backend.nodes.pipelines.visual import RGBAPipelineNode, RollingNode
from backend.updatable.updatable import audio_updatable_objects, visual_updatable_objects
from backend.nodes.buffer import BufferNode
from backend.nodes.visual import BarGraphChartNode
from backend.overrides.CNode import CNode
from backend.nodes.playlist_player import SCPlaylistPlayer
from backend.nodes.rainbow import GradiantNode, RainbowNode
from backend.nodes.simple import ConstantArrayNode, SinArrayNode
from backend.nodes.stream.stream_player_node import StreamPlayerNode

def build_nodes():
    sc_playlist_player_node = SCPlaylistPlayer(alias='sc_playlist_player_node')
    analysis_chunk_size = int(SAMPLE_RATE * DELAY_UPDATE / 1000)
    stream_player_node = StreamPlayerNode(audio_in=sc_playlist_player_node.audio, sample_rate_in=sc_playlist_player_node.sample_rate, enqueue_token=sc_playlist_player_node.enqueue_token, chunk_size=analysis_chunk_size, alias='stream_player_node')
    buffer_node = BufferNode(indata=stream_player_node.chunk, chunk_size=stream_player_node.chunk.value.shape[1], length=analysis_chunk_size, alias='buffer_node')
    sin_array_node = SinArrayNode(alias='sin_array_node', center=0.3, offset=0.1)
    rolling_sin = RollingNode(input_data=sin_array_node.data, roll_speed=2, alias='rolling_sin')
    rainbow_gradiant = GradiantNode(color_in=(0, 0, 255), color_out=(127, 0, 127), cycle=-0.05, alias='rainbow_gradiant')
    gradiant_rainbow = RainbowNode(gradiant=rainbow_gradiant.data, mode=GradiantMode.MIRROR, alias='gradiant_rainbow')
    rolling_rgb = RollingNode(input_data=gradiant_rainbow.data, roll_speed=3, alias='rolling_brushes')
    kick_decay_node = KickDecayNode(buffer_data=buffer_node.data, lowpass_freq=300, threshold=0.3, decay_length=5, alias='kick_decay_node')
    outbounds_up_fct = OutboundsFctNode(y_outbound=kick_decay_node.data, alias='outbounds_up_fct')
    alpha_with_outbound_up = OperatorPipelineNode(arguments=[rolling_sin.data, '+', outbounds_up_fct.data], length=outbounds_up_fct.data.value.shape[-1], alias='alpha_with_outbound_up')
    sin_to_alpha = ValueTransformerPipelineNode(input_value=alpha_with_outbound_up.data, input_value_interval=[0, 1.5], output_value_interval=[0, 1], alias='sin_to_alpha')
    rgba_pipeline = RGBAPipelineNode(rgb=rolling_rgb.data, alpha=sin_to_alpha.output_value)
    constant_array_one = ConstantArrayNode(input_value=1, alias='constant_array_one')
    bar_graph_chart_node = BarGraphChartNode(data=constant_array_one.data, number_points=sin_array_node.data.value.shape[0], brushes=rgba_pipeline.rgba)
    return [node for node in locals().values() if isinstance(node, CNode)]

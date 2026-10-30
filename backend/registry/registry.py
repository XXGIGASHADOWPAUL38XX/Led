
from backend.nodes.broadcast.broadcast_fraction import BroadcastFractionNode
from backend.nodes.trigger.trigger import TriggerNode
from backend.nodes.function.outbounds_fct import OutboundsFctNode
from backend.nodes.windows_fcts.min_window_fct import MinWindowFct
from backend.nodes.pipelines.visual.sliding_amp_gradient import SlidingAmpGradientNode
from backend.nodes.pipelines.difference_node import DifferenceNode
from backend.nodes.broadcast.broadcast_indexes import BroadcastIndexesNode
from backend.nodes.broadcast.broadcast_rescaler import BroadcastRescalerNode
from backend.nodes.controllers import ESP32Node
from backend.nodes.features import (
    ChromaPrismNode,
    CrestFactorNode,
    EntropyNode,
    MidSideEnergyNode,
    OnsetStrengthNode,
    PitchClassChromaNode,
    SpectralCentroidNode,
    SpectralFluxNode,
    ZeroCrossingRateNode,
    SinPeriodicityNode,
)
from backend.nodes.function import FunctionNode
from backend.group_nodes import (
    CenterToEdgeNode,
    EdgeToCenterTriggerNode,
    KickDecayNode,
    SnareDecayNode,
    SinglePeakTriggerNode,
)
from backend.nodes.pipelines.amplitudes.amplitude_level_function import AmplitudesLevelFunction
from backend.nodes.pipelines.amplitudes.avg_frequencies import AvgFrequenciesNode
from backend.nodes.pipelines.amplitudes.linear_amplitude_transformer_node import LinearAmplitudesTransformerNode
from backend.nodes.pipelines.amplitudes.freqscaled_amplitude_transformer_node import FreqScaledAmplitudesTransformerNode
from backend.nodes.pipelines.amplitudes.fct_amplitude_transformer_node import FctAmplitudesTransformerNode
from backend.nodes.pipelines.auditory.filter.band_filter import BandFilterPipelineNode
from backend.nodes.pipelines.auditory.filter.high_filter import HighFilterPipelineNode
from backend.nodes.pipelines.auditory.filter.low_filter import LowFilterPipelineNode
from backend.nodes.pipelines.auditory.rms import RMSPipelineNode
from backend.nodes.pipelines.transforms.operator_node import OperatorPipelineNode
from backend.nodes.pipelines.transforms.clip_node import ClipNode
from backend.nodes.pipelines.transforms.peakfilter_node import PeakFilterNode
from backend.nodes.pipelines.transforms.threshold_filter_node import ThresholdFilterNode
from backend.nodes.pipelines.transforms.value_transformer import ValueTransformerPipelineNode
from backend.nodes.pipelines.visual import RGBAPipelineNode, RollingNode
from backend.nodes.playlist_player import SCPlaylistPlayer
from backend.nodes.offline.stems_recognition import StemsRecognitionNode
from backend.nodes.rainbow import GradiantNode, RainbowNode
from backend.nodes.buffer import BufferNode
from backend.nodes.group_node import GroupNode
from backend.nodes.routing_node import RoutingNode
from backend.nodes.pipelines import AmplitudesNode, SmoothingNode
from backend.nodes.broadcast.broadcast_addition import BroadcastAdditionNode
from backend.nodes.routing_node import GatheringNode
from backend.nodes.stream import StreamPlayerNode, StreamMicNode
from backend.nodes.visual.bar_graph_chart import BarGraphChartNode
from backend.nodes.visual.multi_line_chart import MultiLineChartNode
from backend.nodes.visual.single_line_chart import SingleLineChartNode
from backend.nodes.simple.constant_array import ConstantArrayNode
from backend.nodes.pipelines.visual import SingleColorNode
from backend.nodes.simple.sin_array import SinArrayNode
from backend.nodes.window.window import WindowNode
from backend.nodes.windows_fcts.averaged_window_fct import AveragedWindowFct
from backend.nodes.windows_fcts.ceil_window_fct import CeilWindowFct
from backend.nodes.windows_fcts.decreasing_avg_window_fct import DecreasingAvgWindowFct
from backend.nodes.windows_fcts.max_window_fct import MaxWindowFct
from backend.nodes.windows_fcts.sum_window_fct import SumWindowFct

nodes = [
    TriggerNode,
    OutboundsFctNode,
    MinWindowFct,
    SlidingAmpGradientNode,
    DifferenceNode,
    ESP32Node,
    KickDecayNode,
    SnareDecayNode,
    SinglePeakTriggerNode,
    EdgeToCenterTriggerNode,
    CenterToEdgeNode,
    BufferNode,
    GroupNode,
    RoutingNode,
    GatheringNode,
    ConstantArrayNode,
    FunctionNode,
    SingleColorNode,
    SinArrayNode,
    AmplitudesNode,
    SmoothingNode,
    LowFilterPipelineNode,
    HighFilterPipelineNode,
    BandFilterPipelineNode,
    RMSPipelineNode,
    MidSideEnergyNode,
    ZeroCrossingRateNode,
    SinPeriodicityNode,
    CrestFactorNode,
    EntropyNode,
    SpectralFluxNode,
    OnsetStrengthNode,
    SpectralCentroidNode,
    PitchClassChromaNode,
    ChromaPrismNode,
    WindowNode,
    AveragedWindowFct,
    CeilWindowFct,
    DecreasingAvgWindowFct,
    MaxWindowFct,
    SumWindowFct,
    BarGraphChartNode,
    MultiLineChartNode,
    SingleLineChartNode,
    RainbowNode,
    GradiantNode,
    BroadcastAdditionNode,
    RollingNode,
    ValueTransformerPipelineNode,
    OperatorPipelineNode,
    ClipNode,
    PeakFilterNode,
    ThresholdFilterNode,
    AvgFrequenciesNode,
    LinearAmplitudesTransformerNode,
    FreqScaledAmplitudesTransformerNode,
    FctAmplitudesTransformerNode,
    AmplitudesLevelFunction,
    StreamPlayerNode,
    StreamMicNode,
    SCPlaylistPlayer,
    StemsRecognitionNode,
    RGBAPipelineNode,
    BroadcastFractionNode,
    BroadcastIndexesNode,
    BroadcastRescalerNode,
]

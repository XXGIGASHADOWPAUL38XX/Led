import sys

import numpy as np
from PyQt5 import QtCore, QtWidgets

from backend.updatable.updatable import audio_updatable_objects, visual_updatable_objects
from config import DELAY_UPDATE, SAMPLE_RATE, FREQ_BINS
from frontend.nodes.broadcast.broadcast_addition import BroadcastAdditionNode
from frontend.nodes.broadcast.broadcast_indexes import BroadcastIndexesNode
from frontend.nodes.buffer import BufferNode
from frontend.nodes.controllers import ESP32Node
from frontend.nodes.features import EntropyNode
from frontend.nodes.function import FunctionNode
from frontend.nodes.pipelines import AmplitudesNode
from frontend.nodes.pipelines.amplitudes.linear_amplitude_transformer_node import LinearAmplitudesTransformerNode
from frontend.nodes.pipelines.transforms.value_transformer import ValueTransformerPipelineNode
from frontend.nodes.pipelines.visual import RGBAPipelineNode, RollingNode
from frontend.nodes.playlist_player import SCPlaylistPlayer
from frontend.nodes.rainbow import GradiantNode, RainbowNode
from frontend.enums.gradiant.gradiant_mode import GradiantMode
from frontend.nodes.stream.stream_player_node import StreamPlayerNode
from frontend.nodes.visual import BarGraphChartNode
from frontend.overrides.CFlowchart import CFlowchart
from frontend.overrides.CNode import CNode
from frontend.registry.registry import register_nodes


register_nodes()


def main():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

    sc_playlist_player_node = SCPlaylistPlayer(
        cache=True,
        alias="sc_playlist_player_node"
    )

    analysis_chunk_size = int(SAMPLE_RATE * DELAY_UPDATE / 1000)

    stream_player_node = StreamPlayerNode(
        audio_in=sc_playlist_player_node.audio,
        sample_rate_in=sc_playlist_player_node.sample_rate,
        enqueue_token=sc_playlist_player_node.enqueue_token,
        chunk_size=analysis_chunk_size,
        alias="stream_player_node",
    )

    buffer_node = BufferNode(
        indata=stream_player_node.chunk,
        chunk_size=stream_player_node.chunk.value.shape[1],
        length=analysis_chunk_size,
        alias="buffer_node",
    )

    amplitudes_node = AmplitudesNode(
        buffer=buffer_node.data,
        fft_size=analysis_chunk_size,
        # powering=0.5,
        alias="amplitudes_node",
    )

    entropy_node = EntropyNode(
        amplitudes=amplitudes_node.data,
        alias="entropy_node",
    )

    entropy_level = ValueTransformerPipelineNode(
        input_value=entropy_node.data,
        input_value_interval=[0.85, 0.95],
        output_value_interval=[0, 1],
        alias="entropy_level",
    )

    entropy_correlation_step = ValueTransformerPipelineNode(
        input_value=entropy_node.data,
        input_value_interval=[0.85, 0.95],
        output_value_interval=[0.01, 0.05],
        alias="entropy_correlation_step",
    )

    amplitudes_transformer_node = LinearAmplitudesTransformerNode(
        input_data=amplitudes_node.data,
        correlation_offset=0.1,
        correlation_step=entropy_correlation_step.output_value,
        alias="amplitudes_transformer_node",
    )

    amplitudes_normalized = ValueTransformerPipelineNode(
        input_value=amplitudes_transformer_node.data,
        input_value_interval=[0, 7],
        output_value_interval=[0, 1],
        alias="amplitudes_normalized",
    )

    low_entropy_function_node = FunctionNode(
        points=[(0, 0.1), (0.5, 1), (1, 0.1)],
        alias="height_function_node",
    )

    high_entropy_function_node = FunctionNode(
        points=[(0, 1), (0.5, 0), (1, 1)],
        alias="height_function_node",
    )

    low_entropy_broadcast_node = BroadcastIndexesNode(
        input_data=amplitudes_normalized.output_value,
        indexes=low_entropy_function_node.data,
        alias="height_broadcast_node",
    )

    high_entropy_broadcast_node = BroadcastIndexesNode(
        input_data=amplitudes_normalized.output_value,
        indexes=high_entropy_function_node.data,
        alias="height_broadcast_node",
    )

    entropy_broadcast_node = BroadcastIndexesNode(
        input_data=entropy_level.output_value,
        indexes=np.zeros(FREQ_BINS),
        alias="entropy_broadcast_node",
    )

    broadcast_addition_heights = BroadcastAdditionNode(
        input_data=low_entropy_broadcast_node.data,
        secondary_data=high_entropy_broadcast_node.data,
        level=entropy_broadcast_node.data,
        alias="broadcast_addition",
    )

    gradiant_node_zero = GradiantNode(
        color_in=(255, 0, 12),
        color_out=(255, 132, 0),
        cycle=0,
        alias="gradiant_node_zero"
    )

    rainbow_node_zero = RainbowNode(
        gradiant=gradiant_node_zero.data,
        mode=GradiantMode.MIRROR,
        alias="rainbow_node_zero"
    )

    gradiant_node_one = GradiantNode(
        color_in=(0, 192, 255),
        color_out=(21, 0, 255),
        cycle=0,
        alias="gradiant_node_one"
    )

    rainbow_node_one = RainbowNode(
        gradiant=gradiant_node_one.data,
        mode=GradiantMode.MIRROR,
        alias="rainbow_node_one"
    )

    rolling_rainbow_node_zero = RollingNode(
        input_data=rainbow_node_zero.data,
        roll_speed=1,
        alias="rolling_rainbow_node_zero",
    )

    rolling_rainbow_node_one = RollingNode(
        input_data=rainbow_node_one.data,
        roll_speed=-1,
        alias="rolling_rainbow_node_one",
    )

    broadcast_addition_colors = BroadcastAdditionNode(
        input_data=rolling_rainbow_node_zero.data,
        secondary_data=rolling_rainbow_node_one.data,
        level=entropy_broadcast_node.data,
        alias="broadcast_addition",
    )

    rgba_pipeline_node = RGBAPipelineNode(
        rgb=broadcast_addition_colors.data,
        alpha=broadcast_addition_heights.data,
        alias="rgba_pipeline_node",
    )

    esp32_node = ESP32Node(
        rgba=rgba_pipeline_node.rgba,
        alias="esp32_node",
    )

    bar_chart_node = BarGraphChartNode(
        data=np.ones(broadcast_addition_heights.data.value.shape[-1]),
        title="Amplitudes",
        number_points=FREQ_BINS,
        left_label="Amplitude",
        bottom_label="Frequency",
        brushes=rgba_pipeline_node.rgba,
        y_min=0,
        y_max=1,
        alias="bar_chart_node",
    )

    flowchart = CFlowchart(
        terminals={
            "kick_decay": {"io": "out"},
        },
        nodes=list(filter(lambda x: isinstance(x, CNode) and x.render, list(locals().values()))),
    )

    graph_window = QtWidgets.QMainWindow()
    graph_window.setWindowTitle("---")
    graph_window.setCentralWidget(flowchart.widget())
    graph_window.resize(1100, 700)
    graph_window.show()

    def visual_update():
        for obj in audio_updatable_objects:
            obj.c_update()
        for obj in visual_updatable_objects:
            obj.c_update()

    sc_playlist_player_node.start()

    timer = QtCore.QTimer()
    timer.timeout.connect(visual_update)
    timer.start(DELAY_UPDATE)

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

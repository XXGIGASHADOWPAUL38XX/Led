import sys

import numpy as np
from PyQt5 import QtCore, QtWidgets

from backend.updatable.updatable import audio_updatable_objects, visual_updatable_objects
from config import DELAY_UPDATE, SAMPLE_RATE
from frontend.nodes.buffer import BufferNode
from frontend.group_nodes import CenterToEdgeNode, EdgeToCenterTriggerNode, SinglePeakTriggerNode
from frontend.nodes.pipelines.amplitudes.avg_frequencies import AvgFrequenciesNode
from frontend.nodes.pipelines.transforms.operator_node import OperatorPipelineNode
from frontend.nodes.pipelines.visual import SingleColorNode, RGBAPipelineNode
from frontend.nodes.playlist_player import SCPlaylistPlayer
from frontend.nodes.offline.stems_recognition import StemsRecognitionNode
from frontend.nodes.routing_node import GatheringNode, RoutingNode
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
    stems_recognition_node = StemsRecognitionNode(
        analysis_nb_frames=3,
        similarity_threshold=1,
        level_threshold=0.8,
        min_presence_count=20,
        hop_ms=10,
        alias="stems_recognition_node",
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

    single_peak_trigger_node = SinglePeakTriggerNode(
        buffer_data=buffer_node.data,
        alias="single_peak_trigger_node",
    )

    average_frequency_node = AvgFrequenciesNode(
        input_amplitudes=single_peak_trigger_node.data,
        input_frequencies=single_peak_trigger_node.amplitudes_node.frequencies,
        alias="average_peak_frequency_node",
    )

    low_trigger_node = OperatorPipelineNode(
        arguments=["(", average_frequency_node.data, "<", 600, ")", "&", "(", average_frequency_node.data, ">", 0, ")"],
        length=1,
        alias="low_trigger_node",
    )
    mid_trigger_node = OperatorPipelineNode(
        arguments=["(", average_frequency_node.data, ">", 600, ")", "&", "(", average_frequency_node.data, "<", 2000, ")"],
        length=1,
        alias="mid_trigger_node",
    )
    high_trigger_node = OperatorPipelineNode(
        arguments=[average_frequency_node.data, ">", 2000],
        length=1,
        alias="high_trigger_node",
    )

    bass_edge_trigger_node = EdgeToCenterTriggerNode(
        input_trigger=stems_recognition_node.stem_outputs[0],
        length=single_peak_trigger_node.data.value.shape[-1],
        decay_length=5,
        alias="bass_edge_to_center_node",
    )
    medium_center_trigger_node = CenterToEdgeNode(
        input_trigger=mid_trigger_node.data,
        length=single_peak_trigger_node.data.value.shape[-1],
        decay_length=5,
        alias="medium_center_to_edge_node",
    )
    trigger_alpha_node = OperatorPipelineNode(
        arguments=["(", bass_edge_trigger_node.data, "+", medium_center_trigger_node.data, ")", "/", 2],
        length=single_peak_trigger_node.data.value.shape[-1],
        alias="bass_medium_trigger_alpha_node",
    )

    low_color_node = SingleColorNode(
        color=(0, 100, 255),
        number_points=single_peak_trigger_node.data.value.shape[-1],
        alias="low_frequency_color_node",
    )
    mid_color_node = SingleColorNode(
        color=(0, 255, 100),
        number_points=single_peak_trigger_node.data.value.shape[-1],
        alias="mid_frequency_color_node",
    )
    high_color_node = SingleColorNode(
        color=(255, 60, 0),
        number_points=single_peak_trigger_node.data.value.shape[-1],
        alias="high_frequency_color_node",
    )

    routing_node = RoutingNode(
        operator_nodes=[low_trigger_node, mid_trigger_node, high_trigger_node],
        alias="frequency_routing_node",
    )
    gathering_node = GatheringNode(
        input_datas=[low_color_node.data, mid_color_node.data, high_color_node.data],
        input_booleans=[
            low_trigger_node.data,
            mid_trigger_node.data,
            high_trigger_node.data,
        ],
        alias="frequency_color_gathering_node",
    )

    rgba_pipeline_node = RGBAPipelineNode(
        rgb=gathering_node.data,
        alpha=trigger_alpha_node.data,
    )

    spectogram_chart_node = BarGraphChartNode(
        data=np.ones(single_peak_trigger_node.data.value.shape[-1]),
        title="Amplitudes",
        number_points=single_peak_trigger_node.data.value.shape[0],
        left_label="Frequency",
        bottom_label="Amplitude",
        brushes=rgba_pipeline_node.rgba,
        y_min=0,
        y_max=1,
    )

    flowchart = CFlowchart(
        terminals={
            "kick_decay": {"io": "out"},
        },
        nodes=list(filter(lambda x: isinstance(x, CNode) and x.render, list(locals().values()))),
    )
    sc_playlist_player_node.playlist_player.add_offline_pipeline(stems_recognition_node)

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

import sys

from PyQt5 import QtCore, QtWidgets

from backend.updatable.updatable import audio_updatable_objects, visual_updatable_objects
from config import DELAY_UPDATE, SAMPLE_RATE
from frontend.nodes.offline.stems_recognition import StemsRecognitionNode
from frontend.nodes.playlist_player import SCPlaylistPlayer
from frontend.nodes.stream.stream_player_node import StreamPlayerNode
from frontend.overrides.CFlowchart import CFlowchart
from frontend.registry.registry import register_nodes


register_nodes()


def main():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

    sc_playlist_player_node = SCPlaylistPlayer(cache=True, alias="sc_playlist_player_node")
    stream_player_node = StreamPlayerNode(
        audio_in=sc_playlist_player_node.audio,
        sample_rate_in=sc_playlist_player_node.sample_rate,
        enqueue_token=sc_playlist_player_node.enqueue_token,
        chunk_size=int(SAMPLE_RATE * DELAY_UPDATE / 1000),
        alias="stream_player_node",
    )
    stems_recognition_node = StemsRecognitionNode(alias="stems_recognition_node")

    flowchart = CFlowchart(
        terminals={},
        nodes=[sc_playlist_player_node, stream_player_node, stems_recognition_node],
    )
    sc_playlist_player_node.playlist_player.add_offline_pipeline(stems_recognition_node)

    graph_window = QtWidgets.QMainWindow()
    graph_window.setWindowTitle("Offline stems")
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

from typing import Sequence

from PyQt5 import QtCore, QtWidgets

from frontend.components.elements.element_value import ElementValue
from frontend.components.elements.node_selector.node_selector import NodeSelector
from frontend.components.elements.player.music_player import MusicPlayer


class PlaylistPlayer(QtWidgets.QWidget):
    playRequested = QtCore.pyqtSignal(int)
    pauseRequested = QtCore.pyqtSignal(int)
    seekRequested = QtCore.pyqtSignal(int, float)
    searchRequested = QtCore.pyqtSignal(str)
    addRequested = QtCore.pyqtSignal(object)
    searchResults = QtCore.pyqtSignal(object)
    loadingChanged = QtCore.pyqtSignal(bool)
    removeRequested = QtCore.pyqtSignal(int)
    offlinePipelineAdded = QtCore.pyqtSignal(object)

    def __init__(
        self,
        playlist_metadata: Sequence[dict[str, object]] | None = None,
        node=None,
        offline_pipeline_nodes=None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setMinimumWidth(300)
        self.music_players = []
        self.playlist_metadata = playlist_metadata or []
        self.node = node
        self.offline_pipeline_nodes = offline_pipeline_nodes or (lambda: [])
        self.offline_pipeline_selectors = []

        self.music_player_container = QtWidgets.QWidget(self)
        self.music_player_layout = QtWidgets.QVBoxLayout(self.music_player_container)
        self.music_player_layout.setContentsMargins(0, 0, 0, 0)
        self.music_player_layout.setSpacing(2)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        controls = QtWidgets.QHBoxLayout()
        self.search_input = QtWidgets.QLineEdit()
        self.search_input.setPlaceholderText("Search or paste a music URL")
        self.search_button = QtWidgets.QPushButton("Search")
        self.search_button.clicked.connect(lambda: self.searchRequested.emit(self.search_input.text()))
        self.search_input.returnPressed.connect(self.search_button.click)
        controls.addWidget(self.search_input)
        controls.addWidget(self.search_button)
        self.loader = QtWidgets.QProgressBar()
        self.loader.setRange(0, 0)
        self.loader.setFixedWidth(80)
        self.loader.hide()
        controls.addWidget(self.loader)
        layout.addLayout(controls)
        self.search_results = QtWidgets.QListWidget()
        self.search_results.hide()
        layout.addWidget(self.search_results)
        self.add_selected_button = QtWidgets.QPushButton("Add selected")
        self.add_selected_button.clicked.connect(self._add_selected)
        self.add_selected_button.hide()
        layout.addWidget(self.add_selected_button)
        self.loadingChanged.connect(self.set_loading)
        layout.addWidget(self.music_player_container)

        self.add_offline_pipeline_button = QtWidgets.QPushButton("Add offline pipeline")
        self.add_offline_pipeline_button.clicked.connect(lambda: self.add_offline_pipeline())
        layout.addWidget(self.add_offline_pipeline_button)

        self.set_playlist_metadata(self.playlist_metadata)

    def add_offline_pipeline(self, node=None):
        selector = NodeSelector(
            self.node,
            f"offline_pipeline_{len(self.offline_pipeline_selectors)}",
            ElementValue(None),
            selection_nodes=self.offline_pipeline_nodes,
            register_in_node=False,
        )
        self.offline_pipeline_selectors.append(selector)
        self.music_player_layout.addWidget(selector)
        if node is not None:
            selector.selected_node = node
            selector.refresh_selection_nodes()
            selector.selection_nodes_combobox.setCurrentText(node.name())
            self.offlinePipelineAdded.emit(node)

    def offline_pipelines(self):
        return [selector.selected_node for selector in self.offline_pipeline_selectors if selector.selected_node is not None]

    def set_search_results(self, results):
        self.search_results.clear()
        for result in results:
            item = QtWidgets.QListWidgetItem(
                f"{result.get('uploader', '')} - {result.get('title', result.get('url', ''))}"
            )
            item.setData(QtCore.Qt.ItemDataRole.UserRole, result)
        self.search_results.addItem(item)
        self.search_results.setVisible(bool(results))
        self.add_selected_button.setVisible(bool(results))
        self.set_loading(False)

    def set_loading(self, loading):
        self.loader.setVisible(loading)
        self.search_input.setEnabled(not loading)
        self.search_button.setEnabled(not loading)
        self.search_results.setEnabled(not loading)
        self.add_selected_button.setEnabled(not loading)

    def _add_selected(self):
        item = self.search_results.currentItem()
        if item is not None:
            self.set_loading(True)
            self.addRequested.emit(item.data(QtCore.Qt.ItemDataRole.UserRole))

    def set_playlist_metadata(self, playlist_metadata):
        self.playlist_metadata = playlist_metadata or []
        self.music_players = []

        while self.music_player_layout.count():
            item = self.music_player_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        for index, music_metadata in enumerate(self.playlist_metadata):
            artist = music_metadata.get("artist", "")
            title = music_metadata.get("title", "")
            duration = float(music_metadata.get("duration", 0))

            music_player = MusicPlayer(
                index=index,
                artist=artist,
                title=title,
                music_length=duration,
                disabled=True,
            )
            music_player.playClicked.connect(self.on_play_clicked)
            music_player.pauseClicked.connect(self.on_pause_clicked)
            music_player.seekChanged.connect(self.on_seek_changed)
            music_player.removeClicked.connect(self.removeRequested)

            self.music_player_layout.addWidget(music_player)
            self.music_players.append(music_player)

        self.music_player_container.adjustSize()
        self.adjustSize()

    def set_loaded(self, index, loaded=True):
        if 0 <= index < len(self.music_players):
            self.music_players[index].set_loaded(loaded)

    def set_position(self, index, position):
        if 0 <= index < len(self.music_players):
            self.music_players[index].set_position(position)

    def on_play_clicked(self, index):
        for i, player in enumerate(self.music_players):
            if i != index:
                player.set_playing(False)
        self.playRequested.emit(index)

    def on_pause_clicked(self, index):
        self.pauseRequested.emit(index)

    def on_seek_changed(self, index, ratio):
        self.seekRequested.emit(index, ratio)

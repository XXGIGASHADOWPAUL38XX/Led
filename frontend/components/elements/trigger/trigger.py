import numpy as np
from PyQt5 import QtWidgets

from frontend.components.elements.element import Element


class Trigger(Element):
    def build_value_widget(self, value, font):
        self.square = QtWidgets.QFrame()
        self.square.setFixedSize(16, 16)
        self._set_square(value)
        return self.square

    def refresh_value_label(self):
        if hasattr(self, "square"):
            self._set_square(self.value)

    def _set_square(self, value):
        color = "white" if np.asarray(value).reshape(-1)[-1] == 1 else "black"
        self.square.setStyleSheet(
            f"background-color: {color}; border: 1px solid #777;"
        )


TriggerElement = Trigger

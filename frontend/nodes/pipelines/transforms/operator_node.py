import numpy as np
from PyQt5 import QtCore
from PyQt5.QtGui import QFont
from PyQt5 import QtWidgets

from backend.pipelines.pipeline import AudioPipeline
from frontend.components.elements import AnalysableElement
from frontend.components.elements.element import Element
from frontend.components.elements.element_value import ElementValue
from frontend.components.elements.node_selector.node_selector import NodeSelector
from frontend.components.elements.dropbox.operator import Operator
from frontend.components.elements.textedit.textedit import TextEdit
from frontend.overrides.CNode import CNode

class OperatorPipelineNode(CNode, AudioPipeline):
    nodeName = "OperatorPipeline"
    operations_string = ['(', '+', '-', '*', '**', '/', ')', '<', '<=', '=>', '>', '&']
    successMessage = lambda self, v: f"Operation compiled with success, Value : {v}"
    errorMessage = lambda self, e: f"Operation compile failed: {e}"

    def __init__(self, arguments: list[object] = [], length: int = 0, render: bool = True, parent=None, alias: str | None = None) -> None:
        self.terminals_dict = {
            "data": {"io": "out"}
        }

        self.length = length
        self.arguments = arguments
        self.terminal_element_names = {}
        self.operation_element_names = [self.resolve_element_name(arg) for arg in arguments]

        self.update_terminal()

        super().__init__(node_name=self.nodeName, terminals=self.terminals_dict.copy(), render=render, parent=parent, alias=alias)

        self.operation_elements = self.define_operation_elements(arguments)
        self.built_evaluation = None
        self.build_evaluation_arguments()

        self.data = AnalysableElement(self, "data", ElementValue(np.zeros(self.length)))

        self.operation_state_label = QtWidgets.QLabel(self.successMessage(Element.format_value(self.data.value)))
        label_font = QFont(self.operation_state_label.font())
        label_font.setPointSize(8)
        self.operation_state_label.setFont(label_font)
        self.operation_state_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.elements.append(self.operation_state_label)

    def c_update(self):
        ##!! When the elements argument is being edited, we should skip here
        self.build_evaluation_arguments()
        try:
            if self.data.value.dtype != self.evaluate_arguments().dtype:
                self.data.value = np.asarray((ea:=self.evaluate_arguments()), dtype=ea.dtype)
            else:
                self.data.value[:] = self.evaluate_arguments()
            self.operation_state_label.setText(self.successMessage(Element.format_value(self.data.value)))
        except Exception as e:
            self.operation_state_label.setText(self.errorMessage(e))

    def saveState(self):
        state = super().saveState()
        state["arguments"] = [
            {
                "__element_ref__": {
                    "node_name": arg.node.name(),
                    "element_name": arg.name,
                }
            }
            if isinstance(arg, Element)
            else CNode.serialize_state_value(arg)
            for arg in self.arguments
        ]
        return state

    def resolve_element_name(self, arg):
        if isinstance(arg, Element):
            node_name = getattr(arg.node, "alias", None) or arg.node.name()
            return f"{node_name}:{arg.name}".lower()
        return str(arg)

    def resolve_token(self, token):
        if isinstance(token, Element):
            return self.resolve_token(token.value)
        if callable(token):
            return self.resolve_token(token())
        if isinstance(token, np.ndarray):
            return f"np.array({repr(token.tolist())})"
        return str(token)

    def build_evaluation_arguments(self):
        expression = []

        for element in self.operation_elements:
            expression.append(self.resolve_token(element))
        self.built_evaluation = " ".join(expression)


    def evaluate_arguments(self):
        result = eval(self.built_evaluation)
        if isinstance(result, bool):
            return np.array([result])
        return result

    def update_terminal(self):
        args_elements_indexes = list(map(
            lambda x: x[0], filter(
                lambda y: isinstance(y[1], Element),
                enumerate(self.arguments)
            )
        ))
        for arg_element_index in args_elements_indexes:
            terminal_name = self.operation_element_names[arg_element_index]
            self.terminals_dict[terminal_name] = {"io": "in"}
            self.terminals_dict[f"{terminal_name}_out"] = {"io": "out"}
            self.terminal_element_names[f"{terminal_name}_out"] = terminal_name
        self.pending_terminals = dict(self.terminals_dict)
        # self.init_terminals()

    def terminal_element_name(self, terminal_name):
        return self.terminal_element_names.get(terminal_name, terminal_name)

    def define_operation_elements(self, arguments):
        elements = []

        for name, arg in zip(self.operation_element_names, arguments):
            if isinstance(arg, Element):
                element = NodeSelector(
                    self,
                    name,
                    ElementValue(arg),
                    selection_nodes=self.get_flowchart_visible_nodes
                )
            elif isinstance(arg, str) and arg in self.operations_string:
                element = Operator(self, name, ElementValue(arg))
                element.operator_combobox.currentTextChanged.connect(self.build_evaluation_arguments)
            elif isinstance(arg, str):
                element = TextEdit(self, name, ElementValue(arg))
                element.text_edit.textEdited.connect(self.build_evaluation_arguments)
            else:
                element = TextEdit(self, name, ElementValue(str(arg)))
                element.text_edit.textEdited.connect(self.build_evaluation_arguments)
            setattr(self, name, element)
            elements.append(element)

        return elements

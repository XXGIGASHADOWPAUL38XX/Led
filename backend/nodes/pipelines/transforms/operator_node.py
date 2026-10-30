from backend.components.elements.parameters import Parameter, SequenceElement, DataElement
import numpy as np

from backend.pipelines.pipeline import AudioPipeline
from backend.components.elements import AnalysableElement
from backend.components.elements.element import Element
from backend.components.elements.element_value import ElementValue
from backend.components.elements.node_selector.node_selector import NodeSelector

from backend.overrides.CNode import CNode

class OperatorPipelineNode(CNode, AudioPipeline):
    """Evaluate an expression assembled from Elements and literal tokens.

    Configure ordered `arguments`, such as [source.data, "*", 0.5], and
    output `length`. Element arguments create named inputs and corresponding
    `_out` passthrough terminals; `data` contains the expression result each
    audio update. Boolean scalars become one-element arrays. Uses Python eval;
    supply trusted expressions whose results fit the output buffer."""

    nodeName = "OperatorPipeline"
    operations_string = ['(', '+', '-', '*', '**', '/', ')', '<', '<=', '=>', '>', '&']

    def __init__(self, arguments: list[object] = [], length: int = 0, parent=None, alias: str | None = None) -> None:
        self.terminals_dict = {
            "data": {"io": "out"}
        }

        self.terminal_element_names = {}
        self.operation_element_names = [self.resolve_element_name(arg) for arg in arguments]

        self.update_terminal(arguments)

        super().__init__(node_name=self.nodeName, terminals=self.terminals_dict.copy(), parent=parent, alias=alias)

        self.length = Parameter(self, 'length', length, minimum=0, maximum=4096, integer=True)
        self.arguments = SequenceElement(self, "arguments", arguments, register_in_node=False)
        self.operation_elements = self.define_operation_elements(arguments)
        self.built_evaluation = None
        self.build_evaluation_arguments()

        self.data = AnalysableElement(self, "data", ElementValue(np.zeros(self.length.value)))

    def c_update(self):
        if not self.operation_elements:
            return self.data
        self.build_evaluation_arguments()
        result = np.asarray(self.evaluate_arguments())
        if result.shape != self.data.value.shape or result.dtype != self.data.value.dtype:
            self.data.value = result
        else:
            self.data.value[:] = result
        return self.data

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
            node_name = arg.node.name()
            return f"{node_name}:{arg.name}".lower()
        return str(arg)

    def disconnect_input(self, name, parameters):
        for index, argument in enumerate(self.arguments):
            if isinstance(argument, Element) and self.resolve_element_name(argument) == name:
                parameters["arguments"][index] = np.zeros_like(argument.value)
        return (f"{name}_out",)

    def connect_input(self, name, source, parameters):
        for index, argument in enumerate(self.arguments):
            if isinstance(argument, Element) and self.resolve_element_name(argument) == name:
                parameters["arguments"][index] = source
        source_node = next(node for node in self.get_nodes() if node.name() == source["nodeId"])
        source_element = vars(source_node)[source_node.terminal_element_name(source["element"])]
        new_name = self.resolve_element_name(source_element)
        return new_name, {f"{name}_out": f"{new_name}_out"}

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

    def update_terminal(self, arguments=None):
        args_elements_indexes = list(map(
            lambda x: x[0], filter(
                lambda y: isinstance(y[1], Element),
                enumerate(self.arguments.value if arguments is None else arguments)
            )
        ))
        for arg_element_index in args_elements_indexes:
            terminal_name = self.operation_element_names[arg_element_index]
            self.terminals_dict[terminal_name] = {"io": "in"}
            self.terminals_dict[f"{terminal_name}_out"] = {"io": "out"}
            self.terminal_element_names[f"{terminal_name}_out"] = terminal_name
        self.pending_terminals = dict(self.terminals_dict)

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
                    selection_nodes=self.get_nodes
                )
            elif isinstance(arg, str) and arg in self.operations_string:
                element = Parameter(self, name, arg, kind='choice', choices=self.operations_string)
            elif isinstance(arg, str):
                element = Parameter(self, name, arg, kind='text')
            else:
                element = DataElement(self, name, arg)
            vars(self)[name] = element
            elements.append(element)

        return elements

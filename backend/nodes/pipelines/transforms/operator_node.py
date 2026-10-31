from backend.components.elements.parameters import Parameter, SequenceElement, DataElement
import numpy as np

from backend.pipelines.pipeline import AudioPipeline
from backend.components.elements import AnalysableElement
from backend.components.elements.element import Element
from backend.components.elements.element_value import ElementValue
from backend.components.elements.node_selector.node_selector import NodeSelector

from backend.overrides.CNode import CNode
from .expression import FUNCTIONS, compile_expression

class OperatorPipelineNode(CNode, AudioPipeline):
    """Evaluate a numeric expression over linked arrays and constants.

    `arguments` stores expression fragments interleaved with source references.
    The UI presents named inputs and a single expression; existing saved token
    expressions retain their meaning. Inputs expose `_out` passthroughs. NumPy
    broadcasting determines result shape. Expressions are compiled once and
    restricted to numeric operators and the supported NumPy functions.
    """

    nodeName = "OperatorPipeline"
    operations_string = ['(', '+', '-', '*', '**', '/', ')', '<', '<=', '==', '>=', '>', '&', '|']

    def __init__(self, arguments: list[object] | None = None, length: int = 0, parent=None, alias: str | None = None, input_names=None) -> None:
        arguments = list(arguments or [])
        self.terminals_dict = {
            "data": {"io": "out"},
            "add_element": {"io": "in", "variadic": True},
        }

        self.terminal_element_names = {}
        self.operation_element_names = [self.resolve_element_name(arg) for arg in arguments]

        self.update_terminal(arguments)

        super().__init__(node_name=self.nodeName, terminals=self.terminals_dict.copy(), parent=parent, alias=alias)

        self.input_names = SequenceElement(self, "input_names", list(input_names or []), register_in_node=False)
        self.length = Parameter(self, 'length', length, minimum=0, maximum=4096, integer=True)
        self.add_element = DataElement(self, 'add_element', None, register_in_node=False)
        self.arguments = SequenceElement(self, "arguments", arguments, register_in_node=False)
        self.arguments.input_ports = [name if isinstance(arg, Element) and name not in self.operation_element_names[:index] else None
                                      for index, (name, arg) in enumerate(zip(self.operation_element_names, arguments))]
        self.operation_elements = self.define_operation_elements(arguments)
        self.built_evaluation = None
        self.build_evaluation_arguments()

        self.data = AnalysableElement(self, "data", ElementValue(
            np.atleast_1d(self.evaluate_arguments()) if arguments else np.zeros(self.length.value)))

    def c_update(self):
        if not self.operation_elements:
            return self.data
        result = np.atleast_1d(self.evaluate_arguments())
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
        if name == 'add_element':
            arguments = parameters.setdefault('arguments', [])
            if arguments and not (type(arguments[-1]) is str and arguments[-1] in self.operations_string and arguments[-1] != ')'):
                arguments.append('+')
            arguments.append(source)
        for index, argument in enumerate(self.arguments):
            if isinstance(argument, Element) and self.resolve_element_name(argument) == name:
                parameters["arguments"][index] = source
        source_node = next(node for node in self.get_nodes() if node.name() == source["nodeId"])
        source_element = vars(source_node)[source_node.terminal_element_name(source["element"])]
        new_name = self.resolve_element_name(source_element)
        return new_name, {} if name == 'add_element' else {f"{name}_out": f"{new_name}_out"}

    def build_evaluation_arguments(self):
        # Bind arrays directly instead of converting every sample to Python text.
        self.variables = {f'v{index}': element for index, element in enumerate(self.operation_elements)
                          if type(self.arguments.value[index]) is not str}
        self.built_evaluation = " ".join(
            f'v{index}' if f'v{index}' in self.variables else str(argument)
            for index, argument in enumerate(self.arguments)) or '0'
        self.compiled = compile_expression(self.built_evaluation, self.variables)

    def evaluate_arguments(self):
        return eval(self.compiled, {"__builtins__": {}, **FUNCTIONS},
                    {name: element.value for name, element in self.variables.items()})

    def validate_parameters(self, changes):
        if self.operation_elements:
            try:
                with np.errstate(all='ignore'):
                    self.evaluate_arguments()
            except (ValueError, TypeError, IndexError) as error:
                raise ValueError(f'Expression: {error}') from error

    def configure_graph(self, graph, parameters):
        # References and their visible wires are one binding, including edits.
        sources = [value for value in parameters.get('arguments', [])
                   if type(value) is dict and 'nodeId' in value]
        bindings = {}
        for source in sources:
            node = next(node for node in self.get_nodes() if node.name() == source['nodeId'])
            bindings[self.resolve_element_name(vars(node)[node.terminal_element_name(source['element'])])] = source
        incoming = {edge['target']['element']: edge for edge in graph['connections'] if edge['target']['nodeId'] == self.name()}
        removed = {name for name, options in self.pending_terminals.items() if options['io'] == 'in' and name != 'add_element'} - bindings.keys()
        if any(edge['source']['nodeId'] == self.name() and edge['source']['element'] in {f'{name}_out' for name in removed}
               for edge in graph['connections']):
            raise ValueError('Disconnect the removed input’s passthrough output first')
        graph['connections'] = [edge for edge in graph['connections'] if edge['target']['nodeId'] != self.name()]
        for name, source in bindings.items():
            graph['connections'].append({'id': incoming[name]['id'] if name in incoming else f'{self.name()}:{name}',
                                         'source': source, 'target': {'nodeId': self.name(), 'element': name}})

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
            elif isinstance(arg, str):
                element = Parameter(self, name, arg, kind='text')
            else:
                element = DataElement(self, name, arg)
            vars(self)[name] = element
            elements.append(element)

        return elements

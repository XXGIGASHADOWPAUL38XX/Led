import re
import numpy as np

from backend.components.elements import AnalysableElement
from backend.components.elements.element import Element
from backend.components.elements.element_value import ElementValue
from backend.components.elements.node_selector.node_selector import NodeSelector
from backend.components.elements.parameters import Parameter, SequenceElement, DataElement
from backend.overrides.CNode import CNode
from backend.pipelines.pipeline import AudioPipeline
from .expression import FUNCTIONS, compile_expression


class OperatorPipelineNode(CNode, AudioPipeline):
    """Evaluate several numeric expressions over shared linked inputs.

    `arguments` defines the main `data` output. Additional `operations` are
    dictionaries with a unique output `name` and tokenized `arguments`.
    Tokens interleave expression fragments, constants, and source references.
    The UI exposes shared named inputs and one expression per output. Inputs
    retain `_out` passthroughs. NumPy broadcasting determines each output shape;
    supported numeric expressions are compiled once and evaluated every tick.
    Legacy single-output graphs keep their original arguments and terminals.
    """

    nodeName = 'OperatorPipeline'
    operations_string = ['(', '+', '-', '*', '**', '/', ')', '<', '<=', '==', '>=', '>', '&', '|']

    def __init__(self, arguments=None, length=0, parent=None, alias=None, input_names=None, operations=None):
        arguments, operations = list(arguments or []), list(operations or [])
        groups = [arguments, *[operation['arguments'] for operation in operations]]
        all_arguments = [argument for group in groups for argument in group]
        terminals = {'data': {'io': 'out'}, 'add_element': {'io': 'in', 'variadic': True}}
        self.terminal_element_names = {}
        self.operation_element_names = [self.resolve_element_name(argument) for argument in all_arguments]
        ports = []
        for index, argument in enumerate(all_arguments):
            name = self.operation_element_names[index]
            first = isinstance(argument, Element) and name not in terminals
            ports.append(name if first else None)
            if first:
                terminals[name] = {'io': 'in'}
                terminals[f'{name}_out'] = {'io': 'out'}
                self.terminal_element_names[f'{name}_out'] = name
        super().__init__(self.nodeName, terminals, parent=parent, alias=alias)
        self.arguments = SequenceElement(self, 'arguments', arguments, register_in_node=False)
        self.arguments.input_ports = ports
        self.input_names = SequenceElement(self, 'input_names', list(input_names or []), register_in_node=False)
        self.operations = SequenceElement(self, 'operations', operations, register_in_node=False)
        self.length = Parameter(self, 'length', length, minimum=0, maximum=4096, integer=True)
        self.add_element = DataElement(self, 'add_element', None, register_in_node=False)
        self.programs, self.variables, self.operation_elements = {}, {}, []
        self.compiled = None
        names = ['data']
        for operation in operations:
            name = operation['name']
            if not re.fullmatch(r'[A-Za-z_]\w*', name) or name in names or name in vars(self) or any(name in vars(base) for base in type(self).__mro__):
                raise ValueError('Output names must be unique identifiers and cannot use reserved names')
            names.append(name)
            self.pending_terminals[name] = {'io': 'out'}
        self.operation_elements = self.define_operation_elements(all_arguments)
        self.variables = {f'__input_{index}': element for index, element in enumerate(self.operation_elements)
                          if type(all_arguments[index]) is not str}
        offset = 0
        for name, group in zip(names, groups):
            expression = ' '.join(f'__input_{offset + index}' if type(argument) is not str else argument
                                  for index, argument in enumerate(group)) or '0'
            self.programs[name] = compile_expression(expression, self.variables)
            offset += len(group)
            result = np.atleast_1d(self.evaluate_arguments(name)) if group else np.zeros(length if name == 'data' else 1)
            vars(self)[name] = AnalysableElement(self, name, ElementValue(result))
        self.compiled = self.programs['data']

    def argument_groups(self):
        return [self.arguments.value, *[operation['arguments'] for operation in self.operations]]

    @staticmethod
    def parameter_groups(parameters):
        return [parameters.setdefault('arguments', []), *[operation['arguments'] for operation in parameters.get('operations', [])]]

    def c_update(self):
        values = {name: element.value for name, element in self.variables.items()}
        for name, compiled in self.programs.items():
            if name == 'data' and not self.arguments.value:
                continue
            result = np.atleast_1d(eval(compiled, {'__builtins__': {}, **FUNCTIONS}, values))
            output = vars(self)[name]
            if result.shape != output.value.shape or result.dtype != output.value.dtype:
                output.value = result
            else:
                output.value[:] = result
        return self.data

    def evaluate_arguments(self, name='data'):
        return eval(self.programs[name], {'__builtins__': {}, **FUNCTIONS},
                    {name: element.value for name, element in self.variables.items()})

    def validate_parameters(self, changes):
        try:
            with np.errstate(all='ignore'):
                for name in self.programs:
                    self.evaluate_arguments(name)
        except (ValueError, TypeError, IndexError) as error:
            raise ValueError(f'Expression: {error}') from error

    def saveState(self):
        state = super().saveState()
        state['arguments'] = [
            {'__element_ref__': {'node_name': argument.node.name(), 'element_name': argument.name}}
            if isinstance(argument, Element) else CNode.serialize_state_value(argument)
            for argument in self.arguments]
        return state

    def resolve_element_name(self, argument):
        return f'{argument.node.name()}:{argument.name}'.lower() if isinstance(argument, Element) else str(argument)

    def disconnect_input(self, name, parameters):
        for group, saved in zip(self.argument_groups(), self.parameter_groups(parameters)):
            for index, argument in enumerate(group):
                if isinstance(argument, Element) and self.resolve_element_name(argument) == name:
                    saved[index] = np.zeros_like(argument.value)
        return (f'{name}_out',)

    def connect_input(self, name, source, parameters):
        if name == 'add_element':
            arguments = parameters.setdefault('arguments', [])
            if arguments:
                arguments.append('+')
            arguments.append(source)
        else:
            for group, saved in zip(self.argument_groups(), self.parameter_groups(parameters)):
                for index, argument in enumerate(group):
                    if isinstance(argument, Element) and self.resolve_element_name(argument) == name:
                        saved[index] = source
        node = next(node for node in self.get_nodes() if node.name() == source['nodeId'])
        new_name = self.resolve_element_name(vars(node)[node.terminal_element_name(source['element'])])
        return new_name, {} if name == 'add_element' else {f'{name}_out': f'{new_name}_out'}

    def configure_graph(self, graph, parameters):
        bindings = {}
        for group in self.parameter_groups(parameters):
            for source in group:
                if type(source) is dict and 'nodeId' in source:
                    node = next(node for node in self.get_nodes() if node.name() == source['nodeId'])
                    bindings[self.resolve_element_name(vars(node)[node.terminal_element_name(source['element'])])] = source
        incoming = {edge['target']['element']: edge for edge in graph['connections'] if edge['target']['nodeId'] == self.name()}
        removed_inputs = {name for name, options in self.pending_terminals.items() if options['io'] == 'in' and name != 'add_element'} - bindings.keys()
        removed_outputs = {f'{name}_out' for name in removed_inputs} | (self.programs.keys() - {'data', *[operation['name'] for operation in parameters.get('operations', [])]})
        if any(edge['source']['nodeId'] == self.name() and edge['source']['element'] in removed_outputs for edge in graph['connections']):
            raise ValueError('Disconnect the removed output first')
        graph['connections'] = [edge for edge in graph['connections'] if edge['target']['nodeId'] != self.name()]
        for name, source in bindings.items():
            graph['connections'].append({'id': incoming[name]['id'] if name in incoming else f'{self.name()}:{name}',
                                         'source': source, 'target': {'nodeId': self.name(), 'element': name}})

    def terminal_element_name(self, terminal_name):
        return self.terminal_element_names.get(terminal_name, terminal_name)

    def define_operation_elements(self, arguments):
        elements = []
        for name, argument in zip(self.operation_element_names, arguments):
            if isinstance(argument, Element):
                element = NodeSelector(self, name, ElementValue(argument), selection_nodes=self.get_nodes)
            elif type(argument) is str:
                element = Parameter(self, name, argument, kind='text')
            else:
                element = DataElement(self, name, argument)
            vars(self)[name] = element
            elements.append(element)
        return elements

from frontend.components.elements.dropbox import Dropbox
from frontend.overrides.CNode import CNode


class Operator(Dropbox):
    operations = ['(', '+', '-', '*', '**', '/', ')', '<', '<=', '=>', '>', '&']

    def __init__(self, node: CNode, name: str, value: object = None, **kwargs: object) -> None:
        super().__init__(node, name, value, items=self.operations, **kwargs)
        self.operator_combobox = self.combobox

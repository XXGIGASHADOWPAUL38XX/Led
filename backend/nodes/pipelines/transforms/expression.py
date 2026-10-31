"""Compile numeric expressions once; only named NumPy operations are allowed."""
import ast
import numpy as np

FUNCTIONS = {
    'abs': np.abs, 'clip': np.clip, 'where': np.where,
    'minimum': np.minimum, 'maximum': np.maximum,
    'sin': np.sin, 'cos': np.cos, 'sqrt': np.sqrt, 'log': np.log, 'exp': np.exp,
    'mean': np.mean, 'sum': np.sum, 'min': np.min, 'max': np.max,
    'roll': np.roll, 'reshape': np.reshape, 'stack': np.stack,
    'concatenate': np.concatenate, 'array': np.array,
}
ALLOWED = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Compare, ast.Call,
           ast.Name, ast.Load, ast.Constant, ast.Tuple, ast.List, ast.keyword,
           ast.Subscript, ast.Slice, ast.Add, ast.Sub, ast.Mult, ast.Div,
           ast.FloorDiv, ast.Mod, ast.Pow, ast.BitAnd, ast.BitOr, ast.USub,
           ast.UAdd, ast.Invert, ast.Lt, ast.LtE, ast.Eq, ast.NotEq, ast.GtE, ast.Gt)


def compile_expression(expression, variables):
    if len(expression) > 8192:
        raise ValueError('Expression is too long')
    try:
        tree = ast.parse(expression, mode='eval')
    except SyntaxError as error:
        raise ValueError(f'Invalid expression: {error.msg}') from error
    nodes = list(ast.walk(tree))
    if len(nodes) > 512:
        raise ValueError('Expression is too complex')
    for node in nodes:
        if type(node) not in ALLOWED:
            raise ValueError('Only numeric expressions and supported functions are allowed')
        if type(node) is ast.Name and node.id not in variables and node.id not in FUNCTIONS:
            raise ValueError(f'Unknown variable or function: {node.id}')
        if type(node) is ast.Call and (type(node.func) is not ast.Name or node.func.id not in FUNCTIONS):
            raise ValueError('Only supported NumPy functions can be called')
        if type(node) is ast.Constant and type(node.value) not in (int, float, bool, type(None)):
            raise ValueError('Only numeric constants are allowed')
    return compile(tree, '<operator>', 'eval')

import { isArrayValue } from "../../lib/backend/protocol.ts";

export const expressionFunctions = ['abs', 'clip', 'where', 'minimum', 'maximum', 'sin', 'cos', 'sqrt', 'log', 'exp', 'mean', 'sum', 'min', 'max', 'roll', 'reshape', 'stack', 'concatenate', 'array'];
export type ExpressionInput = { name: string; value: unknown; port?: string };
const isInput = (value: unknown) => isArrayValue(value) || typeof value === 'object' && value !== null;
const inputKey = (value: unknown) => JSON.stringify(value);
export const nextInputName = (inputs: ExpressionInput[]) => {
  let index = inputs.length;
  while (inputs.some((input) => input.name === `v${index}`)) index++;
  return `v${index}`;
};

/** Keep the saved token format; present its references as compact named inputs. */
export function readExpression(arguments_: unknown[], names: string[], ports: (string | null)[] = [], inputs: ExpressionInput[] = []) {
  const tokens = arguments_.map((value, index) => {
    if (!isInput(value)) return String(value);
    let input = inputs.find((input) => inputKey(input.value) === inputKey(value));
    if (!input) {
      const name = names[inputs.length];
      input = { name: name && !inputs.some((input) => input.name === name) ? name : nextInputName(inputs), value, port: ports[index] ?? undefined };
      inputs.push(input);
    }
    return input.name;
  });
  return { inputs, expression: tokens.join(' ') };
}

export function writeExpression(expression: string, inputs: ExpressionInput[]) {
  const names = inputs.map((input) => input.name);
  if (new Set(names).size !== names.length || names.some((name) => !/^[A-Za-z_]\w*$/.test(name) || expressionFunctions.includes(name))) {
    throw Error('Input names must be unique identifiers, different from function names.');
  }
  const arguments_: unknown[] = [];
  // Scientific notation stays intact; only complete identifiers can reference inputs.
  const tokens = expression.match(/(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?|[A-Za-z_]\w*|\s+|./g) ?? [];
  let fragment = '';
  for (const token of tokens) {
    const input = inputs.find((input) => input.name === token);
    if (input) { if (fragment.trim()) arguments_.push(fragment.trim()); arguments_.push(input.value); fragment = ''; }
    else fragment += token;
  }
  if (fragment.trim()) arguments_.push(fragment.trim());
  const used = inputs.filter((input) => arguments_.some((value) => isInput(value) && inputKey(value) === inputKey(input.value)));
  return { arguments: arguments_, input_names: used.map((input) => input.name) };
}


export type ExpressionOutput = { name: string; expression: string };
export type SavedOperation = { name: string; arguments: unknown[] };
export function readExpressions(arguments_: unknown[], operations: SavedOperation[], names: string[], ports: (string | null)[] = []) {
  const inputs: ExpressionInput[] = [];
  let offset = 0;
  const outputs = [{ name: 'data', arguments: arguments_ }, ...operations].map((operation) => {
    const { expression } = readExpression(operation.arguments, names, ports.slice(offset), inputs);
    offset += operation.arguments.length;
    return { name: operation.name, expression };
  });
  return { inputs, outputs };
}

export function writeExpressions(outputs: ExpressionOutput[], inputs: ExpressionInput[]) {
  const names = outputs.map((output) => output.name);
  if (new Set(names).size !== names.length || names.some((name) => !/^[A-Za-z_]\w*$/.test(name))) {
    throw Error('Output names must be unique identifiers.');
  }
  const groups = outputs.map((output) => ({ name: output.name, ...writeExpression(output.expression, inputs) }));
  const ordered: ExpressionInput[] = [];
  for (const group of groups) for (const value of group.arguments) {
    if (!isInput(value) || ordered.some((input) => inputKey(input.value) === inputKey(value))) continue;
    ordered.push(inputs.find((input) => inputKey(input.value) === inputKey(value))!);
  }
  return { arguments: groups[0].arguments, input_names: ordered.map((input) => input.name),
    operations: groups.slice(1).map(({ name, arguments: arguments_ }) => ({ name, arguments: arguments_ })) };
}

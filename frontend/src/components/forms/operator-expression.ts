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
export function readExpression(arguments_: unknown[], names: string[], ports: (string | null)[] = []) {
  const inputs: ExpressionInput[] = [];
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

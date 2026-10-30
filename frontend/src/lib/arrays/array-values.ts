export type NumericArray = (number | NumericArray)[];

export function arrayShape(value: unknown): number[] {
  if (typeof value === "number" && Number.isFinite(value)) return [];
  if (!Array.isArray(value)) throw Error("Use finite numbers and rectangular arrays only.");
  const shapes = value.map(arrayShape);
  if (shapes.some((shape) => String(shape) !== String(shapes[0]))) throw Error("All rows must have matching dimensions.");
  return [value.length, ...(shapes[0] ?? [])];
}

export function parseNumericArray(text: string, original: NumericArray, { integer = false, min = -Infinity, max = Infinity } = {}): NumericArray {
  const next = JSON.parse(text);
  if (!Array.isArray(next) || String(arrayShape(next)) !== String(arrayShape(original))) throw Error("Keep the existing array dimensions.");
  if ((next.flat(Infinity) as number[]).some((number) => number < min || number > max || (integer && !Number.isInteger(number)))) throw Error("Values must match the allowed range and number type.");
  return next;
}

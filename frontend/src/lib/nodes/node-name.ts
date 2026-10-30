export function availableNodeName(title: string, existing: readonly string[]): string {
  const names = new Set(existing);
  let name = title, suffix = 2;
  while (names.has(name)) name = `${title} ${suffix++}`;
  return name;
}

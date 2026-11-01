"use client";

import { useEffect, useRef, useState } from "react";
import { useGraph } from "@/lib/backend/hooks";
import { isArrayValue, type ElementDescriptor, type NodeDescriptor } from "@/lib/backend/protocol";
import { SelectElement } from "../elements";
import { Terminal, terminalKey } from "../workspace/terminal";
import { expressionFunctions, readExpressions, writeExpressions, type SavedOperation } from "./operator-expression";

export function OperatorExpressionControl({ node, element, value, onChange, disabled }: {
  node: NodeDescriptor; element: ElementDescriptor; value: unknown[];
  onChange: (values: Record<string, unknown>) => void; disabled: boolean;
}) {
  const snapshot = useGraph();
  const names = node.elements.find((element) => element.name === 'input_names')?.value as string[] ?? [];
  const operations = node.elements.find((element) => element.name === 'operations')?.value as SavedOperation[] ?? [];
  const [draft, setDraft] = useState(() => readExpressions(value, operations, names, element.itemPorts));
  const [active, setActive] = useState(0);
  const [error, setError] = useState('');
  const [word, setWord] = useState('');
  const text = useRef<HTMLTextAreaElement>(null);
  useEffect(() => { setDraft(readExpressions(value, operations, names, element.itemPorts)); setError(''); setActive((index) => Math.min(index, operations.length)); }, [node]);
  const sources = (snapshot?.nodes ?? []).filter((source) => source.id !== node.id).flatMap((source) => source.ports.filter((port) => port.direction === 'out')
    .map((port) => ({ value: JSON.stringify({ nodeId: source.id, element: port.name }), label: `${source.id}.${port.name}` })));
  const commit = (next = draft) => {
    if (JSON.stringify(next) === JSON.stringify(readExpressions(value, operations, names, element.itemPorts))) return;
    try { const parameters = writeExpressions(next.outputs, next.inputs); setError(''); onChange(parameters); }
    catch (reason) { setError((reason as Error).message); }
  };
  const insert = (value: string, replaceWord = false) => {
    const input = text.current!;
    const end = input.selectionStart, start = end - (replaceWord ? word.length : 0);
    const expression = draft.outputs[active].expression.slice(0, start) + value + draft.outputs[active].expression.slice(input.selectionEnd);
    setDraft({ ...draft, outputs: draft.outputs.map((output, index) => index === active ? { ...output, expression } : output) }); setWord('');
    requestAnimationFrame(() => { input.focus(); input.setSelectionRange(start + value.length, start + value.length); });
  };
  const suggestions = word ? [...draft.inputs.map((input) => input.name), ...expressionFunctions.map((name) => `${name}(`)].filter((name) => name.startsWith(word)).slice(0, 6) : [];
  return <fieldset disabled={disabled} className="space-y-2">
    <legend className="mb-2 text-[10px] uppercase tracking-wider text-zinc-500">Inputs & expressions</legend>
    {draft.inputs.map((input, index) => <div key={index} className="relative flex items-center gap-1">
      {input.port && <Terminal endpoint={{ nodeId: node.id, element: input.port }} direction="input" className="absolute -left-5 top-2.5" />}
      <input aria-label={`Input ${index + 1} name`} className="w-12 rounded border border-white/10 bg-black/20 px-2 py-2 font-mono text-xs text-violet-200 outline-none focus:border-violet-400" value={input.name}
        onChange={(event) => {
          const name = event.target.value;
          const outputs = draft.outputs.map((output) => ({ ...output, expression: /^[A-Za-z_]\w*$/.test(input.name) ? output.expression.replace(new RegExp(`\\b${input.name}\\b`, 'g'), name) : output.expression }));
          setDraft({ outputs, inputs: draft.inputs.map((item, i) => i === index ? { ...item, name } : item) });
        }} onBlur={() => commit()} />
      <div className="min-w-0 flex-1">{isArrayValue(input.value) ? <span className="text-[10px] text-zinc-400">Constant · {input.value.shape.join(' × ')}</span>
        : <SelectElement label="Source" value={JSON.stringify(input.value)} options={sources} onValueChange={(value) => {
          const next = { ...draft, inputs: draft.inputs.map((item, i) => i === index ? { ...item, value: JSON.parse(value) } : item) };
          setDraft(next); commit(next);
        }} />}</div>
      <button type="button" aria-label={`Insert ${input.name}`} onMouseDown={(event) => event.preventDefault()} onClick={() => insert(input.name)} className="px-1 text-xs text-violet-300">↳</button>
      <button type="button" aria-label={`Remove input ${input.name}`} onMouseDown={(event) => event.preventDefault()} className="px-1 text-zinc-500 hover:text-rose-300" onClick={() => {
        const next = { inputs: draft.inputs.filter((_, i) => i !== index), outputs: draft.outputs.map((output) => ({ ...output, expression: output.expression.replace(new RegExp(`\\b${input.name}\\b`, 'g'), '0') })) };
        setDraft(next); commit(next);
      }}>×</button>
      {input.port && <Terminal endpoint={{ nodeId: node.id, element: `${input.port}_out` }} direction="output" className="absolute -right-5 top-2.5" />}
    </div>)}
    <div className="relative rounded border border-dashed border-violet-400/25 px-3 py-2 text-[10px] text-zinc-500" data-terminal={terminalKey({ nodeId: node.id, element: 'add_element' }, 'input')}>
      <Terminal endpoint={{ nodeId: node.id, element: 'add_element' }} direction="input" className="absolute -left-5 top-2" />
      Drag an output here to add an input
    </div>
    {draft.outputs.map((output, index) => <div key={index} className="relative space-y-1 rounded-lg border border-white/10 bg-black/10 p-2">
      <div className="flex items-center gap-2">
        <input aria-label={`Output ${index + 1} name`} value={output.name} readOnly={index === 0}
          className="min-w-0 flex-1 rounded bg-transparent px-1 py-1 font-mono text-xs text-violet-200 outline-none focus:bg-white/5"
          onChange={(event) => setDraft({ ...draft, outputs: draft.outputs.map((item, i) => i === index ? { ...item, name: event.target.value } : item) })} onBlur={() => commit()} />
        {index > 0 && <button type="button" aria-label={`Remove output ${output.name}`} onMouseDown={(event) => event.preventDefault()} className="text-zinc-500 hover:text-rose-300" onClick={() => {
          const next = { ...draft, outputs: draft.outputs.filter((_, i) => i !== index) }; setDraft(next); setActive(0); commit(next);
        }}>×</button>}
      </div>
      {node.ports.some((port) => port.name === output.name && port.direction === 'out') && <Terminal endpoint={{ nodeId: node.id, element: output.name }} direction="output" className="absolute -right-5 top-3" />}
      <textarea ref={index === active ? text : undefined} onFocus={() => { setActive(index); setWord(''); }} aria-label={index === 0 ? "Expression" : `Expression ${output.name}`} spellCheck={false} rows={2} placeholder="clip(v0 + v1 * 0.2, 0, 1)" value={output.expression}
        className="w-full resize-y rounded-lg border border-white/10 bg-black/25 px-3 py-2 font-mono text-xs leading-6 text-violet-100 outline-none focus:border-violet-400/70"
        onChange={(event) => { setDraft({ ...draft, outputs: draft.outputs.map((output, i) => i === index ? { ...output, expression: event.target.value } : output) }); setWord(event.target.value.slice(0, event.target.selectionStart).match(/[A-Za-z_]\w*$/)?.[0] ?? ''); }}
        onBlur={() => { setWord(''); commit(); }} onKeyDown={(event) => {
          if (event.key === 'Escape') { event.stopPropagation(); setWord(''); }
          if (event.key === 'Tab' && suggestions.length) { event.preventDefault(); insert(suggestions[0], true); }
          if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) { event.preventDefault(); setWord(''); commit(); }
        }} />
      {index === active && suggestions.length > 0 && <div className="absolute inset-x-0 top-full z-30 rounded-lg border border-white/10 bg-[#23232e] p-1 shadow-xl">{suggestions.map((name) => <button key={name} type="button" onMouseDown={(event) => event.preventDefault()} onClick={() => insert(name, true)} className="block w-full rounded px-2 py-1 text-left font-mono text-xs text-violet-200 hover:bg-white/10">{name}</button>)}</div>}
    </div>)}
    <button type="button" onMouseDown={(event) => event.preventDefault()} className="w-full rounded border border-dashed border-violet-400/25 px-3 py-2 text-xs text-violet-300 hover:bg-violet-400/10" onClick={() => {
      let index = draft.outputs.length + 1;
      while (draft.outputs.some((output) => output.name === `result_${index}`)) index++;
      const next = { ...draft, outputs: [...draft.outputs, { name: `result_${index}`, expression: draft.inputs[0]?.name ?? '0' }] };
      setDraft(next); setActive(next.outputs.length - 1); commit(next);
    }}>+ Add operation / output</button>
    <p className="text-[10px] text-zinc-500">NumPy broadcasting · Tab to complete · ⌘/Ctrl Enter to apply</p>
    {error && <p role="alert" className="text-[10px] text-rose-300">{error}</p>}
  </fieldset>;
}

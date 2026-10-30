import assert from 'node:assert/strict';
import test from 'node:test';
import { saveFile } from './save-file.ts';

test('native Save As chooses a destination before exporting and writes exact bytes', async () => {
  const calls = [];
  const data = new Uint8Array([0, 128, 255]);
  globalThis.window = { showSaveFilePicker: async (options) => {
    calls.push('picker');
    assert.equal(options.suggestedName, 'template7.led');
    assert.deepEqual(options.types[0].accept['application/octet-stream'], ['.led']);
    return { name: 'my-lights.led', createWritable: async () => ({
      write: async (bytes) => { calls.push('write'); assert.deepEqual(bytes, data); },
      close: async () => { calls.push('close'); },
    }) };
  } };
  try {
    assert.equal(await saveFile('template7.led', async () => { calls.push('export'); return data; }), 'my-lights.led');
    assert.deepEqual(calls, ['picker', 'export', 'write', 'close']);
  } finally { delete globalThis.window; }
});

test('cancelling the picker does not export or write a template', async () => {
  let exported = false;
  globalThis.window = { showSaveFilePicker: async () => { throw new DOMException('Cancelled', 'AbortError'); } };
  try {
    await assert.rejects(saveFile('lights.led', async () => { exported = true; return new Uint8Array(); }), { name: 'AbortError' });
    assert.equal(exported, false);
  } finally { delete globalThis.window; }
});

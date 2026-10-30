import assert from 'node:assert/strict';
import test from 'node:test';
import { clampZoom, zoomScroll } from './viewport.ts';

test('zoom keeps the canvas point under the cursor stationary', () => {
  for (const previous of [0.1, 1, 2]) for (const next of [0.1, 1, 2]) {
    const scroll = 500, cursor = 150;
    const world = (scroll + cursor) / previous;
    assert.equal((zoomScroll(scroll, cursor, previous, next) + cursor) / next, world);
  }
  assert.equal(clampZoom(0.001), 0.1);
  assert.equal(clampZoom(100), 2);
});

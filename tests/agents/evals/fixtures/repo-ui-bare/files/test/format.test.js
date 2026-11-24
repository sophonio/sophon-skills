import { test } from 'node:test';
import assert from 'node:assert/strict';
import { formatCount, formatDuration } from '../src/lib/format.js';

test('formatCount uses the singular for one', () => {
  assert.equal(formatCount(1, 'item'), '1 item');
  assert.equal(formatCount(3, 'item'), '3 items');
});

test('formatDuration splits hours and minutes', () => {
  assert.equal(formatDuration(45), '45 min');
  assert.equal(formatDuration(130), '2 h 10 min');
});

/**
 * Unit tests for the visualizer's map geometry helpers (SIM-4).
 * Run with plain Node.js: `node --test tests/demo/test_map_geometry.test.mjs`
 */

import test from "node:test";
import assert from "node:assert";
import vm from "node:vm";
import fs from "node:fs";

// The helper file is a plain browser script, so run it in a sandbox and read its functions
const source = fs.readFileSync(new URL("../../public/demo/track_visualization_map_geometry.js", import.meta.url), "utf8");
const sandbox = {};
vm.createContext(sandbox);
vm.runInContext(`${source}; this.isValidOutline = isValidOutline; this.projectOutlineToView = projectOutlineToView; this.buildClosedPath = buildClosedPath;`, sandbox);
const { isValidOutline, projectOutlineToView, buildClosedPath } = sandbox;

const SQUARE = [[0, 0], [100, 0], [100, 100], [0, 100]];

test("accepts a normal outline and rejects bad ones", () => {
  assert.strictEqual(isValidOutline(SQUARE), true);
  assert.strictEqual(isValidOutline([[0, 0], [1, 1]]), false);
  assert.strictEqual(isValidOutline("outline"), false);
  assert.strictEqual(isValidOutline([[0, 0], [1, 1], [NaN, 2]]), false);
  assert.strictEqual(isValidOutline([[0, 0], [1, 1], ["a", 2]]), false);
  assert.strictEqual(isValidOutline(Array.from({ length: 2001 }, (_, i) => [i, i])), false);
  assert.strictEqual(isValidOutline(Array.from({ length: 2000 }, (_, i) => [i, i])), true);
});

test("projection stays inside the 700 x 450 view with padding and keeps north up", () => {
  const points = projectOutlineToView(SQUARE);
  for (const p of points) {
    assert.ok(p.x >= 50 - 1e-6 && p.x <= 650 + 1e-6, `x ${p.x}`);
    assert.ok(p.y >= 50 - 1e-6 && p.y <= 400 + 1e-6, `y ${p.y}`);
  }
  // [0,100] is north of [0,0], so it must have the smaller y
  assert.ok(points[3].y < points[0].y);
});

test("projection keeps the true shape (a square stays square)", () => {
  const points = projectOutlineToView(SQUARE);
  const width = Math.abs(points[1].x - points[0].x);
  const height = Math.abs(points[3].y - points[0].y);
  assert.ok(Math.abs(width - height) < 1e-6);
});

test("closed path string starts with M, uses L and ends with Z", () => {
  const path = buildClosedPath(projectOutlineToView(SQUARE));
  assert.match(path, /^M [\d.]+ [\d.]+ L [\d.]+ [\d.]+ L [\d.]+ [\d.]+ L [\d.]+ [\d.]+ Z$/);
});

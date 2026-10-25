import { test } from "node:test";
import assert from "node:assert/strict";
import { series, extent, polylineSegments, playStep, fmtFit } from "../data.js";
import { loadMock } from "./helpers.mjs";

const mock = loadMock();

test("series reads history columns in order", () => {
  assert.deepEqual(series(mock, "n_covered"), [2, 4, 5, 6]);
  assert.equal(series(mock, "best").length, mock.params.gens + 1);
});

test("extent ignores null and widens flat ranges", () => {
  assert.deepEqual(extent([1, null, 3], [-2]), [-2, 3]);
  assert.deepEqual(extent([2, 2]), [1.5, 2.5]);
  assert.equal(extent([null, null]), null);
});

test("polylineSegments splits at null (strict -inf)", () => {
  const segs = polylineSegments([0, 1, null, 1, 0], { width: 4, height: 10, min: 0, max: 1 });
  assert.deepEqual(segs, ["0.00,10.00 1.00,0.00", "3.00,0.00 4.00,10.00"]);
  assert.deepEqual(polylineSegments([null], { width: 4, height: 10, min: 0, max: 1 }), []);
});

test("playStep accumulates fractional generations", () => {
  let s = playStep(0, 16, 10);       // 0.16 gens
  assert.equal(s.step, 0);
  s = playStep(s.acc, 100, 10);      // +1 gen
  assert.equal(s.step, 1);
  assert.equal(playStep(0, 16, 1000).step, 16);   // gens=1000: salta cuadros
});

test("fmtFit shows -inf for null", () => {
  assert.equal(fmtFit(null), "−∞");
  assert.equal(fmtFit(1.0115384615), "1.011538");
});

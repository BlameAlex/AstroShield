import { test } from "node:test";
import assert from "node:assert/strict";
import { frame, viewGen, checkResult } from "../data.js";
import { loadMock } from "./helpers.mjs";

const mock = loadMock();
const cls = f => Object.fromEntries(f.regions.map(r => [r.id, r.cls]));

test("frame final mock", () => {
  const f = frame(mock, "final");
  assert.equal(f.sats.length, 8);
  assert.equal(f.regions.length, 6);
  assert.ok(f.regions.every(r => r.cls === "covered"));
  assert.equal(f.debris.length, 3);
  assert.equal(f.occupied.length, 2);
  assert.equal(f.fitness, 1.011538);
  assert.equal(f.nViol, 0);
  assert.ok(f.sats.every(s => s.violating === false && s.radius === mock.scenario.footprint_deg));
});

test("frame initial mock", () => {
  const f = frame(mock, "initial");
  const c = cls(f);
  assert.equal(c.yucatan, "covered");
  assert.equal(c.japon, "covered");
  for (const id of ["amazonia", "california", "sahel", "australia"]) assert.equal(c[id], "uncovered");
  assert.equal(f.sats[0].violating, true);
  assert.equal(f.violations[0].zone_id, "atlantico_norte");
  assert.ok(f.sats.slice(1).every(s => s.violating === false));
  assert.equal(f.nViol, 1);
});

test("frame gen 1 partial", () => {
  const f = frame(mock, 1);
  const c = cls(f);
  assert.equal(c.california, "partial");
  assert.equal(f.regions.find(r => r.id === "california").cov, 0.82441);
  assert.equal(c.australia, "uncovered");
  assert.ok(f.sats.every(s => s.violating === null));
  assert.equal(f.violations, null);
  assert.equal(f.fitness, mock.history[1].best);
});

test("frame converts [lat, lon] to {lat, lng}", () => {
  const f = frame(mock, "initial");
  assert.deepEqual([f.sats[1].lat, f.sats[1].lng], mock.initial.sats[1]);
  const r = mock.scenario.regions[0];
  assert.deepEqual([f.regions[0].lat, f.regions[0].lng], [r.lat, r.lon]);
  const z = mock.scenario.debris_zones[0];
  assert.deepEqual([f.debris[0].lat, f.debris[0].lng, f.debris[0].radius], [z.lat, z.lon, z.radius_deg]);
});

test("frame gen 0 equals initial", () => {
  const a = frame(mock, 0), b = frame(mock, "initial");
  assert.deepEqual(a.sats, b.sats);
  assert.deepEqual(cls(a), cls(b));
  assert.equal(a.fitness, b.fitness);
});

test("frame last equals final", () => {
  const a = frame(mock, 3), b = frame(mock, "final");
  assert.deepEqual({ ...a, view: null, gen: null }, { ...b, view: null, gen: null });
});

test("frame rejects out-of-range generation", () => {
  assert.throws(() => frame(mock, 4), RangeError);
  assert.throws(() => frame(mock, -1), RangeError);
});

test("viewGen maps views to slider positions", () => {
  assert.equal(viewGen(mock, "initial"), 0);
  assert.equal(viewGen(mock, "final"), 3);
  assert.equal(viewGen(mock, 2), 2);
});

test("checkResult accepts mock and rejects files without best_sats", () => {
  assert.equal(checkResult(mock), null);
  const reval = { ...mock, history: undefined };
  assert.match(checkResult(reval), /best_sats/);
  assert.match(checkResult({ id: "x" }), /escenario/);
  assert.match(checkResult(null), /objeto/);
});

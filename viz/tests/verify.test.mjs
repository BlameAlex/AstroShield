import { test } from "node:test";
import assert from "node:assert/strict";
import { frame, verify } from "../data.js";
import { loadMock } from "./helpers.mjs";

const mock = loadMock();

// Simula lo que app.js lee de las capas: copias independientes, no el mismo objeto.
const drawnFrom = f => structuredClone({
  regions: f.regions.map(({ id, lat, lng, cls, radius }) => ({ id, lat, lng, cls, radius })),
  sats: f.sats.map(({ lat, lng }) => ({ lat, lng })),
  debris: f.debris.map(({ id, lat, lng }) => ({ id, lat, lng })),
  occupied: f.occupied.map(({ id, lat, lng }) => ({ id, lat, lng })),
});

test("verify passes on faithful drawing", () => {
  for (const view of ["initial", "final", 0, 1, 2, 3]) {
    const v = verify(mock, view, drawnFrom(frame(mock, view)));
    assert.equal(v.ok, true, `vista ${view}`);
    assert.equal(v.rows.length, 6);
  }
});

test("verify catches swapped lat/lng", () => {
  const d = drawnFrom(frame(mock, "final"));
  const r = d.regions[2];
  [r.lat, r.lng] = [r.lng, r.lat];
  const v = verify(mock, "final", d);
  assert.equal(v.ok, false);
  assert.equal(v.rows.find(x => x.id === r.id).ok, false);
  assert.ok(v.rows.filter(x => x.id !== r.id).every(x => x.ok));
});

test("verify catches swapped satellite lat/lng", () => {
  const d = drawnFrom(frame(mock, "final"));
  const s = d.sats[3];
  [s.lat, s.lng] = [s.lng, s.lat];
  const v = verify(mock, "final", d);
  assert.equal(v.ok, false);
  assert.equal(v.counts.satPositions, false);
});

test("verify catches wrong color", () => {
  const d = drawnFrom(frame(mock, 1));
  d.regions.find(x => x.id === "california").cls = "covered";
  const v = verify(mock, 1, d);
  assert.equal(v.ok, false);
  assert.equal(v.rows.find(x => x.id === "california").ok, false);
  assert.equal(v.counts.nCovered, false);
});

test("verify catches wrong radius", () => {
  const d = drawnFrom(frame(mock, "final"));
  d.regions[0].radius = 5;
  assert.equal(verify(mock, "final", d).ok, false);
});

test("verify catches missing satellite", () => {
  const d = drawnFrom(frame(mock, "final"));
  d.sats.pop();
  const v = verify(mock, "final", d);
  assert.equal(v.counts.sats, false);
  assert.equal(v.ok, false);
});

test("verify catches missing zone", () => {
  const d = drawnFrom(frame(mock, "final"));
  d.occupied.pop();
  assert.equal(verify(mock, "final", d).counts.occupied, false);
});

test("verify n_covered per generation", () => {
  const v = verify(mock, 2, drawnFrom(frame(mock, 2)));
  assert.equal(v.rows.filter(r => r.drawnCls === "covered").length, 5);
  assert.equal(v.nCoveredJSON, mock.history[2].n_covered);
  assert.equal(v.counts.nCovered, true);
});

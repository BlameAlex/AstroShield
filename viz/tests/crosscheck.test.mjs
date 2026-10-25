// Verificación cruzada: las posiciones que la viz dibuja (frame().sats, ya convertidas a
// {lat, lng}) reproducen la cobertura que reporta el JSON al recalcularla con §5.1/§5.2.
// Esto solo se hace en pruebas: la viz colorea con coverage/best_coverage, no recalcula.
import { test } from "node:test";
import assert from "node:assert/strict";
import { relative, basename } from "node:path";
import { frame, centralAngle, checkResult } from "../data.js";
import { loadJSON, resultFiles, ROOT } from "./helpers.mjs";

function recompute(f) {
  const out = {};
  for (const r of f.regions) {
    let best = 0;
    for (const s of f.sats) {
      const d = centralAngle(s.lat, s.lng, r.lat, r.lng);
      const c = Math.min(1, Math.max(0, (s.radius + r.radius - d) / (2 * r.radius)));
      if (c > best) best = c;
    }
    out[r.id] = best;
  }
  return out;
}

const files = resultFiles();

test("there is at least mock.json to cross-check", () => {
  assert.ok(files.some(p => basename(p) === "mock.json"));
});

for (const path of files) {
  test(`cross-check positions reproduce JSON coverage: ${relative(ROOT, path)}`, () => {
    const result = loadJSON(path);
    assert.equal(checkResult(result), null);
    const tol = result.id === "mock" ? 1e-6 : 1e-9;
    const views = ["initial", "final", ...result.history.map((_, g) => g)];
    for (const view of views) {
      const f = frame(result, view);
      const got = recompute(f);
      for (const r of f.regions) {
        assert.ok(Math.abs(got[r.id] - r.cov) <= tol,
          `${path} vista ${view} región ${r.id}: recalculada ${got[r.id]} vs JSON ${r.cov}`);
      }
      if (typeof view === "number") {
        const nCov = f.regions.filter(r => r.cls === "covered").length;
        assert.equal(nCov, result.history[view].n_covered, `n_covered en gen ${view}`);
      }
    }
  });
}

import { test } from "node:test";
import assert from "node:assert/strict";
import { capPolygon, centralAngle } from "../data.js";

test("centralAngle matches geometry.central_angle borders (§6.2)", () => {
  assert.ok(Math.abs(centralAngle(0, 179.9, 0, -179.9) - 0.2) < 1e-9);
  assert.ok(centralAngle(90, 0, 90, 123) < 1e-12);
  assert.ok(Math.abs(centralAngle(90, 17, 0, -40) - 90) < 1e-9);
  assert.ok(Math.abs(centralAngle(0, 0, 0, 180) - 180) < 1e-9);
});

function checkCap(lat, lon, r, n = 64) {
  const [ring] = capPolygon(lat, lon, r, n);
  assert.deepEqual(ring[0], ring[ring.length - 1], "anillo cerrado");
  for (const [lng, la] of ring.slice(0, n)) {
    assert.ok(Math.abs(centralAngle(lat, lon, la, lng) - r) < 1e-9, `vértice ${la},${lng}`);
  }
  for (let k = 1; k < ring.length; k++) {
    assert.ok(Math.abs(ring[k][0] - ring[k - 1][0]) <= 180, "sin saltos > 180 en lng");
  }
  return ring;
}

test("capPolygon radius", () => {
  checkCap(78, 30, 8);
  const ring = checkCap(0, 179, 5);
  assert.ok(ring.some(([lng]) => lng > 180), "el casquete cruza el antimeridiano de forma continua");
  checkCap(-30, -120, 10, 32);
});

test("capPolygon around a pole closes through the pole", () => {
  const ring = checkCap(85, 10, 10);
  assert.ok(ring.some(([, la]) => la === 90));
  const s = checkCap(-88, -170, 5);
  assert.ok(s.some(([, la]) => la === -90));
});

test("capPolygon tangent to a pole (lat + radius == 90) does not wrap the globe", () => {
  // reducido.json: polar_norte lat 78, radio 12 -> toca el polo sin contenerlo.
  for (const [lat, lon, r] of [[78, 30, 12], [-78, 30, 12]]) {
    const ring = checkCap(lat, lon, r);
    assert.equal(ring.length, 65, "sin vértices extra de cierre por el polo");
    const span = Math.max(...ring.map(p => p[0])) - Math.min(...ring.map(p => p[0]));
    assert.ok(span < 270, `la extensión en lng (${span}) no debe abarcar el globo`);
  }
});
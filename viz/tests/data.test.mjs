import { test } from "node:test";
import assert from "node:assert/strict";
import { toLL, coverageClass } from "../data.js";

test("toLL keeps order", () => {
  assert.deepEqual(toLL([20.5, -89]), { lat: 20.5, lng: -89 });
});

test("coverageClass borders", () => {
  assert.equal(coverageClass(1), "covered");
  assert.equal(coverageClass(0.999999), "partial");
  assert.equal(coverageClass(0), "uncovered");
  assert.equal(coverageClass(0.5), "partial");
});

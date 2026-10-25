// La viz no puede llevar datos fijos del escenario (contrato §11): todo sale del JSON.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { VIZ_DIR } from "./helpers.mjs";

const FORBIDDEN = /yucatan|amazonia|california|sahel|japon|australia|atlantico|pacifico_sur|polar_norte|objeto_[ab]|20\.5|-89/i;

test("no hardcoded scenario data", () => {
  const files = readdirSync(VIZ_DIR).filter(n => /\.(js|html)$/.test(n));
  assert.ok(files.includes("data.js"));
  for (const name of files) {
    const text = readFileSync(join(VIZ_DIR, name), "utf-8");
    const m = text.match(FORBIDDEN);
    assert.equal(m, null, `${name} contiene "${m?.[0]}"`);
  }
});

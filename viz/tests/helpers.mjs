// Utilidades compartidas por las pruebas de la visualización (solo Node).
import { readFileSync, readdirSync, statSync, existsSync } from "node:fs";
import { join, dirname, basename } from "node:path";
import { fileURLToPath } from "node:url";

export const VIZ_DIR = join(dirname(fileURLToPath(import.meta.url)), "..");
export const ROOT = join(VIZ_DIR, "..");
export const RESULTS_DIR = join(ROOT, "results");

export const loadJSON = path => JSON.parse(readFileSync(path, "utf-8"));
export const loadMock = () => loadJSON(join(RESULTS_DIR, "mock.json"));

// Todos los JSON de resultado bajo results/ (recursivo), excluyendo reval_* y escenarios/,
// igual que tests/test_contract.py. No falla si un subdirectorio (p. ej. exp_json/) no existe.
export function resultFiles(dir = RESULTS_DIR) {
  if (!existsSync(dir)) return [];
  const out = [];
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) {
      if (name !== "escenarios") out.push(...resultFiles(p));
    } else if (name.endsWith(".json") && !basename(name).startsWith("reval_")) {
      out.push(p);
    }
  }
  return out.sort();
}

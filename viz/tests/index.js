// Punto de entrada para `node --test viz/tests/`: Node 24 trata el argumento como el
// módulo del directorio (package.json "main"), así que aquí se importan todas las pruebas.
// También funciona `node --test viz/tests/*.test.mjs`.
import { readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
for (const name of readdirSync(here).filter(n => n.endsWith(".test.mjs")).sort()) {
  await import(pathToFileURL(join(here, name)).href);
}

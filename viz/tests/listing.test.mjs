import { test } from "node:test";
import assert from "node:assert/strict";
import { parseListing } from "../data.js";

// Formato de `python -m http.server` (SimpleHTTPRequestHandler.list_directory).
const HTML = `<!DOCTYPE HTML>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Directory listing for /results/</title>
</head>
<body>
<h1>Directory listing for /results/</h1>
<hr>
<ul>
<li><a href="base_penalty_s42.json">base_penalty_s42.json</a></li>
<li><a href="base_repair_s42.json">base_repair_s42.json</a></li>
<li><a href="escenarios/">escenarios/</a></li>
<li><a href="exp_json/">exp_json/</a></li>
<li><a href="exp_reval/">exp_reval/</a></li>
<li><a href="mock.json">mock.json</a></li>
<li><a href="notas.md">notas.md</a></li>
<li><a href="resumen.csv">resumen.csv</a></li>
<li><a href="reval_base_a_inviable.json">reval_base_a_inviable.json</a></li>
<li><a href="con%20espacio.json">con espacio.json</a></li>
</ul>
<hr>
</body>
</html>`;

test("listing parser", () => {
  const { files, dirs } = parseListing(HTML);
  assert.deepEqual(files, ["base_penalty_s42.json", "base_repair_s42.json", "mock.json", "con espacio.json"]);
  assert.deepEqual(dirs, ["exp_json/", "exp_reval/"]);
});

test("listing parser ignores absolute, parent and external links", () => {
  const html = `<a href="../x.json">a</a><a href="/abs.json">b</a><a href="http://e.com/y.json">c</a>
                <a href="./z.json">d</a><a href="ok.json?x=1">e</a><a class="k" href="ok.JSON">f</a>`;
  assert.deepEqual(parseListing(html), { files: ["ok.JSON"], dirs: [] });
});

test("listing parser on non-listing page returns empty", () => {
  assert.deepEqual(parseListing("<html><body>404</body></html>"), { files: [], dirs: [] });
  assert.deepEqual(parseListing(""), { files: [], dirs: [] });
});

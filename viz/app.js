// viz/app.js — cableado del DOM y del globo. La lógica vive en data.js (pura, con pruebas).
import { frame, verify, checkResult, capPolygon, centralAngle, lastGen, viewGen,
         parseListing, playStep, fmtFit, fmtCov } from "./data.js";
import { renderMeta, renderMetrics, renderViolations, renderVerify, buildCharts } from "./panel.js";

const $ = id => document.getElementById(id);
const DEFAULT_FILE = "../results/mock.json";      // contrato §11
const RESULTS_DIR = "../results/";

// Paleta: se lee de las variables CSS (style.css) para no duplicarla.
const css = getComputedStyle(document.documentElement);
const v = name => css.getPropertyValue(name).trim();
const PAL = {
  bg: v("--bg"), atmosphere: v("--c-atmosphere"),
  region: { covered: v("--c-covered"), partial: v("--c-partial"), uncovered: v("--c-uncovered") },
  sat: v("--c-sat"), satViolating: v("--c-sat-violating"), ghost: v("--c-ghost"), arc: v("--c-arc"),
  footprint: v("--c-footprint"), footprintLine: v("--c-footprint-line"),
  debris: v("--c-debris"), debrisLine: v("--c-debris-line"),
  occupied: v("--c-occupied"), occupiedLine: v("--c-occupied-line"),
};
// Inversa color → clase: la verificación lee el color REAL que pinta la capa.
const CLS_OF_COLOR = Object.fromEntries(Object.entries(PAL.region).map(([k, c]) => [c, k]));

const state = { result: null, source: "", view: "initial", playing: false, acc: 0, last: 0,
                showFootprints: true, compare: false, charts: null, tags: new Map() };

// ---------------------------------------------------------------------------
// Globo
// ---------------------------------------------------------------------------
const ALT = { debris: 0.004, occupied: 0.006, region: 0.008, footprint: 0.012 };
const polyFill = d => d.kind === "region" ? PAL.region[d.cls] : d.kind === "footprint" ? PAL.footprint
                    : d.kind === "debris" ? PAL.debris : PAL.occupied;
const polyLine = d => d.kind === "region" ? PAL.region[d.cls] : d.kind === "footprint" ? PAL.footprintLine
                    : d.kind === "debris" ? PAL.debrisLine : PAL.occupiedLine;
const satColor = d => d.kind === "ghost" ? PAL.ghost : d.violating ? PAL.satViolating : PAL.sat;
const yesNo = b => (b === null ? "sin detalle en esta generación" : b ? "sí" : "no");

const globe = new Globe($("globe"))
  .backgroundColor(PAL.bg)
  .globeImageUrl("https://cdn.jsdelivr.net/npm/three-globe@2.45.6/example/img/earth-blue-marble.jpg")
  .bumpImageUrl("https://cdn.jsdelivr.net/npm/three-globe@2.45.6/example/img/earth-topology.png")
  .showGraticules(true)
  .atmosphereColor(PAL.atmosphere)
  .polygonGeoJsonGeometry("geometry")
  .polygonCapColor(polyFill)
  .polygonSideColor(() => "rgba(0,0,0,0)")
  .polygonStrokeColor(polyLine)
  .polygonAltitude(d => ALT[d.kind])
  .polygonsTransitionDuration(0)
  .polygonLabel(d => d.kind === "region"
    ? `<b>${d.name}</b><br>cobertura JSON: ${fmtCov(d.cov)} (${d.cls})<br>prioridad ${d.priority} · w=${d.weight}`
    : d.kind === "footprint" ? `Footprint de S${d.i} · ${d.radius}°`
    : `<b>${d.kind === "debris" ? "⚠ Desechos" : "■ Ocupado"}: ${d.name}</b><br>radio ${d.radius}°`)
  .pointLat(d => d.lat)
  .pointLng(d => d.lng)
  .pointColor(satColor)
  .pointAltitude(d => (d.kind === "ghost" ? 0.03 : 0.05))
  .pointRadius(d => (d.kind === "ghost" ? 0.55 : 0.75))
  .pointsTransitionDuration(0)
  .pointLabel(d => `<b>${d.kind === "ghost" ? "Inicial " : ""}S${d.i}</b><br>lat ${d.lat.toFixed(4)}, lon ${d.lng.toFixed(4)}` +
                   (d.kind === "ghost" ? "" : `<br>viola zona: ${yesNo(d.violating)}`))
  .arcColor(() => PAL.arc)
  .arcStroke(0.35)
  .arcDashLength(0.5)
  .arcDashGap(0.15)
  .arcDashAnimateTime(0)
  .arcsTransitionDuration(0)
  .htmlElement(d => d.el)
  .htmlAltitude(0.02);
globe.controls().autoRotate = false;

function resize() {
  const box = $("globe").getBoundingClientRect();
  globe.width(box.width).height(box.height);
}
new ResizeObserver(resize).observe($("globe"));

// Etiquetas HTML: se crean una vez por archivo y solo cambian texto/clase por cuadro.
function buildTags(f) {
  state.tags = new Map();
  const make = (key, cls, text, d) => {
    const el = document.createElement("div");
    el.className = `tag ${cls}`;
    el.textContent = text;
    state.tags.set(key, el);
    return { lat: d.lat, lng: d.lng, el };
  };
  globe.htmlElementsData([
    ...f.regions.map(r => make(`r:${r.id}`, r.cls, r.id, r)),
    ...f.debris.map(z => make(`d:${z.id}`, "debris", `⚠ ${z.id}`, z)),
    ...f.occupied.map(z => make(`o:${z.id}`, "occupied", `■ ${z.id}`, z)),
  ]);
}
const MARK = { covered: "✓", partial: "◐", uncovered: "✗" };

function draw(f) {
  const cap = (d, kind, extra = {}) => ({ ...d, kind, ...extra, geometry: { type: "Polygon", coordinates: capPolygon(d.lat, d.lng, d.radius) } });
  globe.polygonsData([
    ...f.debris.map(z => cap(z, "debris")),
    ...f.occupied.map(z => cap(z, "occupied")),
    ...f.regions.map(r => cap(r, "region")),
    ...(state.showFootprints ? f.sats.map(s => cap(s, "footprint")) : []),
  ]);
  const ghosts = state.compare ? frame(state.result, "initial").sats.map(s => ({ ...s, kind: "ghost" })) : [];
  globe.pointsData([...f.sats.map(s => ({ ...s, kind: "sat" })), ...ghosts]);
  globe.arcsData(state.compare ? ghosts.map((g, i) => ({ startLat: g.lat, startLng: g.lng, endLat: f.sats[i]?.lat, endLng: f.sats[i]?.lng }))
    .filter(a => a.endLat !== undefined && (a.startLat !== a.endLat || a.startLng !== a.endLng)) : []);
  for (const r of f.regions) {
    const el = state.tags.get(`r:${r.id}`);
    if (el) { el.className = `tag ${r.cls}`; el.textContent = `${MARK[r.cls]} ${r.id} ${(r.cov * 100).toFixed(0)}%`; }
  }
}

// Lo que REALMENTE tienen las capas (datos + accesores de color/posición), para verify().
function drawnFromLayers() {
  const polys = globe.polygonsData(), capColor = globe.polygonCapColor();
  const lat = globe.pointLat(), lng = globe.pointLng();
  const zone = kind => polys.filter(p => p.kind === kind).map(p => ({ id: p.id, lat: p.lat, lng: p.lng }));
  return {
    regions: polys.filter(p => p.kind === "region").map(p => {
      const [vLng, vLat] = p.geometry.coordinates[0][0];
      return { id: p.id, lat: p.lat, lng: p.lng, cls: CLS_OF_COLOR[capColor(p)] ?? null,
               radius: centralAngle(p.lat, p.lng, vLat, vLng) };
    }),
    sats: globe.pointsData().filter(p => p.kind === "sat").sort((a, b) => a.i - b.i)
      .map(p => ({ lat: lat(p), lng: lng(p) })),
    debris: zone("debris"),
    occupied: zone("occupied"),
  };
}

// ---------------------------------------------------------------------------
// Render de una vista
// ---------------------------------------------------------------------------
function render() {
  const r = state.result;
  if (!r) return;
  const f = frame(r, state.view);
  draw(f);
  const g = viewGen(r, state.view);
  $("slider").value = g;
  $("gen-label").textContent = `gen ${g} / ${lastGen(r)} · ${fmtFit(f.fitness)}`;
  $("btn-initial").classList.toggle("active", state.view === "initial");
  $("btn-final").classList.toggle("active", state.view === "final");
  state.charts.setGen(g);
  renderMetrics(r, f);
  renderViolations(f);
  renderVerify(verify(r, state.view, drawnFromLayers()));
}

function setView(view) {
  state.view = view;
  render();
}
const seek = g => setView(Math.max(0, Math.min(lastGen(state.result), g)));
const stepBy = d => { stop(); seek(viewGen(state.result, state.view) + d); };

// ---------------------------------------------------------------------------
// Reproducción (requestAnimationFrame con paso adaptativo: con gens=1000 salta cuadros)
// ---------------------------------------------------------------------------
function tick(t) {
  if (!state.playing) return;
  const { step, acc } = playStep(state.acc, t - state.last, Number($("speed").value));
  state.acc = acc;
  state.last = t;
  if (step > 0) {
    const g = viewGen(state.result, state.view) + step;
    if (g >= lastGen(state.result)) { seek(lastGen(state.result)); stop(); return; }
    seek(g);
  }
  requestAnimationFrame(tick);
}
function play() {
  if (!state.result) return;
  if (viewGen(state.result, state.view) >= lastGen(state.result)) seek(0);
  state.playing = true; state.acc = 0; state.last = performance.now();
  $("btn-play").textContent = "⏸"; $("btn-play").setAttribute("aria-label", "Pausar");
  requestAnimationFrame(tick);
}
function stop() {
  state.playing = false;
  $("btn-play").textContent = "▶"; $("btn-play").setAttribute("aria-label", "Reproducir");
}

// ---------------------------------------------------------------------------
// Carga de resultados
// ---------------------------------------------------------------------------
function showError(msg) {
  $("error").hidden = !msg;
  $("error").textContent = msg ?? "";
}

function setResult(result, source) {
  const err = checkResult(result);
  if (err) { showError(`No se puede mostrar «${source}»: ${err}`); return false; }
  stop();
  showError(null);
  state.result = result;
  state.source = source;
  state.view = "initial";
  $("slider").max = lastGen(result);
  $("subtitle").textContent = `${result.scenario.name ?? result.scenario.id} · ${result.mode} · semilla ${result.seed} · ${source}`;
  renderMeta(result, source);
  state.charts = buildCharts(result, g => { stop(); seek(g); });
  buildTags(frame(result, "initial"));
  render();
  return true;
}

async function loadURL(path) {
  try {
    const res = await fetch(path, { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return setResult(await res.json(), path);
  } catch (e) {
    showError(`No se pudo cargar «${path}»: ${e.message}. Sirve el repo con «python -m http.server» desde la raíz.`);
    return false;
  }
}

// Desplegable a partir del listado HTML de python -m http.server (results/ y un nivel de subdirectorios).
async function fillSelect(current) {
  const sel = $("file-select");
  const list = async dir => {
    const res = await fetch(dir, { cache: "no-store" });
    if (!res.ok || !(res.headers.get("content-type") ?? "").includes("html")) return { files: [], dirs: [] };
    return parseListing(await res.text());
  };
  try {
    const top = await list(RESULTS_DIR);
    const paths = top.files.map(f => RESULTS_DIR + f);
    for (const d of top.dirs) {
      const sub = await list(RESULTS_DIR + d).catch(() => ({ files: [] }));
      paths.push(...sub.files.map(f => RESULTS_DIR + d + f));
    }
    if (!paths.length) return;
    if (current && !paths.includes(current)) paths.unshift(current);
    sel.innerHTML = paths.map(p => `<option value="${p}">${p.replace(RESULTS_DIR, "results/")}</option>`).join("");
    sel.value = current;
    sel.hidden = false;
  } catch { /* otro servidor sin listado: se queda oculto, sin error */ }
}

// ---------------------------------------------------------------------------
// Controles
// ---------------------------------------------------------------------------
$("btn-initial").onclick = () => { stop(); setView("initial"); };
$("btn-final").onclick = () => { stop(); setView("final"); };
$("btn-first").onclick = () => { stop(); seek(0); };
$("btn-last").onclick = () => { stop(); seek(lastGen(state.result)); };
$("btn-prev").onclick = () => stepBy(-1);
$("btn-next").onclick = () => stepBy(1);
$("btn-play").onclick = () => (state.playing ? stop() : play());
$("slider").oninput = e => { stop(); seek(Number(e.target.value)); };
$("tg-footprints").onchange = e => { state.showFootprints = e.target.checked; render(); };
$("tg-labels").onchange = e => document.body.classList.toggle("no-labels", !e.target.checked);
$("tg-compare").onchange = e => { state.compare = e.target.checked; document.body.classList.toggle("comparing", state.compare); render(); };
$("file-select").onchange = async e => {
  if (await loadURL(e.target.value)) {
    const url = new URL(location.href);
    url.searchParams.set("file", e.target.value);
    history.replaceState(null, "", url);
  }
};
$("file-input").onchange = e => {
  const file = e.target.files[0];
  if (!file) return;
  file.text().then(text => {
    try { setResult(JSON.parse(text), file.name); } catch (err) { showError(`«${file.name}» no es JSON válido: ${err.message}`); }
  });
};
document.addEventListener("keydown", e => {
  if (!state.result || e.target.matches("input[type=file], select")) return;
  if (e.key === "ArrowLeft") { e.preventDefault(); stepBy(-1); }
  else if (e.key === "ArrowRight") { e.preventDefault(); stepBy(1); }
  else if (e.key === "Home") { e.preventDefault(); stop(); seek(0); }
  else if (e.key === "End") { e.preventDefault(); stop(); seek(lastGen(state.result)); }
  else if (e.key === " " && !e.target.matches("button")) { e.preventDefault(); state.playing ? stop() : play(); }
});

// Arranque
const initial = new URLSearchParams(location.search).get("file") ?? DEFAULT_FILE;
resize();
loadURL(initial).then(() => fillSelect(initial));
// Para inspección desde la consola o un navegador sin cabeza.
window.astroshield = { state, globe, drawnFromLayers, verifyNow: () => verify(state.result, state.view, drawnFromLayers()) };

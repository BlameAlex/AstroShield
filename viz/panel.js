// viz/panel.js — panel lateral: cabecera, métricas, curvas SVG, violaciones y tabla de
// verificación. Solo DOM; los números vienen de data.js / del JSON.
import { series, extent, polylineSegments, fmtFit, fmtCov, lastGen } from "./data.js";

const SVG = "http://www.w3.org/2000/svg";
const esc = s => String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const $ = id => document.getElementById(id);

// ---------------------------------------------------------------------------
// Cabecera de la ejecución
// ---------------------------------------------------------------------------
export function renderMeta(result, source) {
  const sc = result.scenario, p = result.params;
  const params = `P=${p.pop_size} · G=${p.gens} · k=${p.tournament_k} · pc=${p.p_crossover} · α=${p.blx_alpha}` +
                 ` · pswap=${p.p_swap} · pm=${p.p_mut} · σ=${p.sigma_mut} · elit=${p.elitism}`;
  const env = result.env ? `python ${result.env.python ?? "?"} · numpy ${result.env.numpy ?? "?"}` : "—";
  $("card-meta").innerHTML = `
    <h2>Ejecución</h2>
    <div class="meta-title">${esc(sc.name ?? sc.id)} <span class="muted">(${esc(sc.id)})</span></div>
    <span class="badge ${result.valid ? "ok" : "bad"}">${result.valid ? "válida" : "inválida"}</span>
    <dl class="kv">
      <dt>id</dt><dd>${esc(result.id)}</dd>
      <dt>modo</dt><dd>${esc(result.mode)}</dd>
      <dt>semilla</dt><dd>${esc(result.seed)}</dd>
      <dt>satélites</dt><dd>${esc(sc.n_sats)} · footprint ${esc(sc.footprint_deg)}°</dd>
      <dt>aptitud</dt><dd>K=${esc(sc.fitness?.k_penalty)} · β=${esc(sc.fitness?.redundancy_bonus)}</dd>
      <dt>params</dt><dd>${esc(params)}</dd>
      <dt>entorno</dt><dd>${esc(env)}</dd>
      <dt>contrato</dt><dd>${esc(result.contract_version)}</dd>
      <dt>archivo</dt><dd>${esc(source)}</dd>
    </dl>
    ${result.notes ? `<p class="meta-notes">${esc(result.notes)}</p>` : ""}`;
}

// ---------------------------------------------------------------------------
// Métricas de la vista actual
// ---------------------------------------------------------------------------
export function renderMetrics(result, f) {
  const h = result.history[f.gen];
  const k = f.regions.filter(r => r.cls === "covered").length;
  const label = f.view === "initial" ? "Inicial (gen 0)" : f.view === "final" ? `Final (gen ${f.gen})` : `gen ${f.gen}`;
  const m = (lbl, val, cls = "") => `<div class="metric ${cls}"><div class="lbl">${lbl}</div><div class="val">${val}</div></div>`;
  $("card-metrics").innerHTML = `
    <h2>Vista: ${esc(label)}</h2>
    <div class="metrics">
      ${m("aptitud del mejor", fmtFit(f.fitness))}
      ${m("modo", esc(result.mode))}
      ${m("valid (final)", result.valid ? "sí" : "no")}
      ${m("violaciones del mejor", f.nViol)}
      ${m("regiones cubiertas", `${k}/${f.regions.length}`)}
      ${m("n_invalid (pobl.)", h.n_invalid)}
      ${m("diversidad", h.diversity.toFixed(3))}
      ${m("media pobl.", fmtFit(h.mean))}
      ${m("peor pobl.", fmtFit(h.worst))}
    </div>`;
}

// ---------------------------------------------------------------------------
// Violaciones del mejor individuo
// ---------------------------------------------------------------------------
export function renderViolations(f) {
  let body;
  if (f.violations === null) {
    body = `<p class="muted">El mejor individuo de esta generación tiene <b>${f.nViol}</b> violación(es).
      El JSON solo trae el conteo en generaciones intermedias (<code>best_n_violations</code>);
      el detalle por satélite y zona está en la gen 0 (inicial) y en la final.</p>`;
  } else if (f.violations.length === 0) {
    body = `<p class="muted">Sin violaciones: ningún satélite está dentro de una zona de desechos ni de un objeto ocupado.</p>`;
  } else {
    body = `<table><thead><tr><th>sat</th><th>zona</th><th>tipo</th><th>dist.</th><th>radio</th><th>prof.</th></tr></thead><tbody>
      ${f.violations.map(v => `<tr><td class="num">S${v.sat}</td><td>${esc(v.zone_id)}</td>
        <td>${v.kind === "debris" ? "⚠ desechos" : "■ ocupado"}</td><td class="num">${v.distance_deg.toFixed(3)}°</td>
        <td class="num">${v.radius_deg.toFixed(1)}°</td><td class="num">${v.depth_deg.toFixed(3)}°</td></tr>`).join("")}
      </tbody></table>`;
  }
  $("card-violations").innerHTML = `<h2>Violaciones (${f.nViol})</h2>${body}`;
}

// ---------------------------------------------------------------------------
// Verificación dibujo ↔ JSON
// ---------------------------------------------------------------------------
const CLS_TXT = { covered: "cubierta", partial: "parcial", uncovered: "no cubierta" };
const CHECK_TXT = {
  sats: "nº de satélites dibujados = n_sats = JSON",
  satPositions: "posición de cada satélite dibujado = JSON",
  regions: "nº de regiones dibujadas = escenario",
  debris: "zonas de desechos dibujadas = escenario",
  occupied: "objetos ocupados dibujados = escenario",
  nCovered: "regiones dibujadas en verde = n_covered del JSON",
};

export function renderVerify(v) {
  const rows = v.rows.map(r => `<tr>
      <td>${esc(r.id)}</td><td>${esc(r.priority ?? "")} (${esc(r.weight ?? "")})</td>
      <td class="num">${fmtCov(r.jsonCov)}</td>
      <td><span class="cls ${r.drawnCls ?? ""}">${CLS_TXT[r.drawnCls] ?? "sin dibujar"}</span></td>
      <td class="mark ${r.ok ? "ok" : "bad"}" aria-label="${r.ok ? "coincide" : "no coincide"}">${r.ok ? "✓" : "✗"}</td>
    </tr>`).join("");
  const checks = Object.entries(v.counts).map(([k, ok]) =>
    `<li class="${ok ? "ok" : "bad"}">${ok ? "✓" : "✗"} ${CHECK_TXT[k] ?? k}${k === "nCovered" ? ` (${v.nCoveredJSON})` : ""}</li>`).join("");
  $("card-verify").innerHTML = `
    <h2>Verificación dibujo ↔ JSON <span class="badge ${v.ok ? "ok" : "bad"}">${v.ok ? "todo coincide" : "hay diferencias"}</span></h2>
    <p class="muted" style="margin:0 0 6px;font-size:12px">Se lee lo que realmente tienen las capas del globo
      (posición, radio y color de cada casquete; posición de cada satélite) y se compara con el JSON.</p>
    <table><thead><tr><th>región</th><th>prioridad (w)</th><th>cobertura JSON</th><th>dibujada</th><th></th></tr></thead>
      <tbody>${rows}</tbody></table>
    <ul class="checks">${checks}</ul>`;
}

// ---------------------------------------------------------------------------
// Curvas (SVG). Devuelve un objeto con setGen(g) para mover el cursor.
// ---------------------------------------------------------------------------
function chart(container, lines, { height, onSeek, decimals = 3 }) {
  const W = 400, H = height, M = { l: 46, r: 8, t: 8, b: 16 };
  const pw = W - M.l - M.r, ph = H - M.t - M.b;
  const ext = extent(...lines.map(l => l.values));
  const n = lines[0].values.length;
  container.textContent = "";
  const svg = document.createElementNS(SVG, "svg");
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  svg.setAttribute("role", "img");
  const el = (tag, attrs, parent = svg) => {
    const e = document.createElementNS(SVG, tag);
    for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
    parent.appendChild(e);
    return e;
  };
  el("line", { x1: M.l, y1: M.t + ph, x2: M.l + pw, y2: M.t + ph, class: "axis" });
  el("line", { x1: M.l, y1: M.t, x2: M.l, y2: M.t + ph, class: "axis" });
  const plot = el("g", { transform: `translate(${M.l},${M.t})` });
  if (ext) {
    const [min, max] = ext;
    el("text", { x: M.l - 4, y: M.t + 8, "text-anchor": "end" }).textContent = max.toFixed(decimals);
    el("text", { x: M.l - 4, y: M.t + ph, "text-anchor": "end" }).textContent = min.toFixed(decimals);
    for (const line of lines)
      for (const pts of polylineSegments(line.values, { width: pw, height: ph, min, max }))
        el("polyline", { points: pts, class: line.cls }, plot);
  } else {
    el("text", { x: M.l + pw / 2, y: M.t + ph / 2, "text-anchor": "middle" }).textContent = "sin valores finitos (−∞)";
  }
  el("text", { x: M.l, y: H - 3 }).textContent = "0";
  el("text", { x: M.l + pw, y: H - 3, "text-anchor": "end" }).textContent = String(n - 1);
  const cursor = el("line", { x1: 0, y1: 0, x2: 0, y2: ph, class: "cursor" }, plot);
  svg.addEventListener("click", ev => {
    const box = svg.getBoundingClientRect();
    const x = ((ev.clientX - box.left) / box.width) * W - M.l;
    onSeek(Math.round(Math.min(1, Math.max(0, x / pw)) * (n - 1)));
  });
  container.appendChild(svg);
  return {
    setGen(g) {
      const x = n <= 1 ? pw / 2 : (g / (n - 1)) * pw;
      cursor.setAttribute("x1", x);
      cursor.setAttribute("x2", x);
    },
  };
}

export function buildCharts(result, onSeek) {
  const fit = chart($("chart-fitness"), [
    { values: series(result, "worst"), cls: "s-worst" },
    { values: series(result, "mean"), cls: "s-mean" },
    { values: series(result, "best"), cls: "s-best" },
  ], { height: 170, onSeek, decimals: 3 });
  const legend = document.createElement("div");
  legend.className = "chart-legend";
  legend.innerHTML = `<span><i style="background:var(--c-best)"></i>mejor</span>
    <span><i style="background:var(--c-mean)"></i>media</span>
    <span><i style="background:var(--c-worst)"></i>peor</span>
    <span><i style="background:var(--c-cursor)"></i>generación actual</span>
    <span>huecos = −∞ (strict)</span>`;
  $("chart-fitness").appendChild(legend);
  const minis = [
    chart($("chart-invalid"), [{ values: series(result, "n_invalid"), cls: "s-mini" }], { height: 90, onSeek, decimals: 0 }),
    chart($("chart-covered"), [{ values: series(result, "n_covered"), cls: "s-mini" }], { height: 90, onSeek, decimals: 0 }),
    chart($("chart-diversity"), [{ values: series(result, "diversity"), cls: "s-mini" }], { height: 90, onSeek, decimals: 1 }),
  ];
  return { setGen: g => [fit, ...minis].forEach(c => c.setGen(Math.min(g, lastGen(result)))) };
}

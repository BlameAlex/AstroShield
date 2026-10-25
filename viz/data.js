// viz/data.js — lógica pura de la visualización (sin DOM).
// Se importa igual desde el navegador (app.js) y desde Node (viz/tests/).
// Ningún dato del escenario vive aquí: todo sale del JSON de resultado (contrato §11).

const RAD = Math.PI / 180;
const DEG = 180 / Math.PI;

// ---------------------------------------------------------------------------
// Conversión y clasificación
// ---------------------------------------------------------------------------

// Único punto de conversión [lat, lon] (JSON, §2) → {lat, lng} (globe.gl).
export const toLL = ([lat, lon]) => ({ lat, lng: lon });

// §2: cubierta si c == 1.0, parcial si 0 < c < 1, no cubierta si c == 0.
export const coverageClass = c => (c === 1 ? "covered" : c > 0 ? "partial" : "uncovered");

// ---------------------------------------------------------------------------
// Geometría (solo para dibujar casquetes y para verificaciones cruzadas en pruebas)
// ---------------------------------------------------------------------------

// Ángulo central en grados (haversine), idéntico a geometry.central_angle (§6.2).
export function centralAngle(lat1, lon1, lat2, lon2) {
  const p1 = lat1 * RAD, p2 = lat2 * RAD, l1 = lon1 * RAD, l2 = lon2 * RAD;
  const h = Math.sin((p2 - p1) / 2) ** 2 + Math.cos(p1) * Math.cos(p2) * Math.sin((l2 - l1) / 2) ** 2;
  return 2 * Math.asin(Math.sqrt(Math.min(1, Math.max(0, h)))) * DEG;
}

// Casquete esférico de radio radiusDeg centrado en (lat, lon) como anillo GeoJSON
// [[lng, lat], ...] cerrado. Fórmula de destino sobre la esfera; las longitudes se
// desenvuelven para que no haya saltos de ±360 (globe.gl proyecta con seno/coseno).
// Si el casquete contiene un polo, el anillo se cierra pasando por ese polo.
export function capPolygon(lat, lon, radiusDeg, n = 64) {
  const p1 = lat * RAD, d = radiusDeg * RAD;
  const ring = [];
  let prev = null;
  for (let k = 0; k < n; k++) {
    // Rumbo decreciente (N → O → S → E): sentido antihorario visto desde fuera de la
    // esfera, como pide GeoJSON (RFC 7946) para el anillo exterior.
    const th = -2 * Math.PI * k / n;
    const p2 = Math.asin(Math.sin(p1) * Math.cos(d) + Math.cos(p1) * Math.sin(d) * Math.cos(th));
    let lng = lon + Math.atan2(Math.sin(th) * Math.sin(d) * Math.cos(p1),
                               Math.cos(d) - Math.sin(p1) * Math.sin(p2)) * DEG;
    if (prev !== null) {
      while (lng - prev > 180) lng -= 360;
      while (lng - prev < -180) lng += 360;
    }
    ring.push([lng, p2 * DEG]);
    prev = lng;
  }
  const north = lat + radiusDeg >= 90, south = lat - radiusDeg <= -90;
  if (north || south) {
    const pole = north ? 90 : -90;
    const last = ring[ring.length - 1][0], first = ring[0][0];
    // Cierra por el polo: el anillo abarca 360° de longitud.
    const end = first + (last < first ? -360 : 360);
    ring.push([end, ring[0][1]], [end, pole], [first, pole]);
  }
  ring.push([...ring[0]]);
  return [ring];
}

// ---------------------------------------------------------------------------
// Validación ligera del archivo cargado (la validación formal la hace pytest, §9.4)
// ---------------------------------------------------------------------------

// Devuelve null si el objeto sirve para la visualización, o un mensaje legible si no.
export function checkResult(r) {
  if (!r || typeof r !== "object") return "El archivo no contiene un objeto JSON.";
  const sc = r.scenario;
  if (!sc || typeof sc !== "object" || !Array.isArray(sc.regions))
    return "El archivo no trae el escenario completo (result.scenario). ¿Es un archivo de resultado?";
  for (const k of ["debris_zones", "occupied"])
    if (!Array.isArray(sc[k])) return `Falta scenario.${k} en el archivo.`;
  if (typeof sc.footprint_deg !== "number") return "Falta scenario.footprint_deg en el archivo.";
  for (const k of ["initial", "final"])
    if (!r[k] || !Array.isArray(r[k].sats) || !r[k].coverage)
      return `Falta el bloque ${k} (sats y coverage) en el archivo.`;
  if (!Array.isArray(r.history) || r.history.length === 0 || !Array.isArray(r.history[0].best_sats))
    return "El archivo no trae history[0].best_sats: no es un resultado del AG (¿un reval_*.json?) " +
           "y no se puede reproducir por generación.";
  return null;
}

// ---------------------------------------------------------------------------
// Cuadros por vista
// ---------------------------------------------------------------------------

export const lastGen = result => result.history.length - 1;

// Generación equivalente a una vista (para el control deslizante).
export function viewGen(result, view) {
  if (view === "initial") return 0;
  if (view === "final") return lastGen(result);
  return view;
}

function snapshot(result, view) {
  const h = result.history;
  if (view === "initial" || view === "final") {
    const s = result[view];
    return { sats: s.sats, coverage: s.coverage, fitness: s.fitness,
             nViol: s.violations.length, violations: s.violations };
  }
  if (!Number.isInteger(view) || view < 0 || view >= h.length)
    throw new RangeError(`Generación fuera de rango: ${view}`);
  const g = h[view];
  return {
    sats: g.best_sats, coverage: g.best_coverage, fitness: g.best,
    nViol: g.best_n_violations,
    // El detalle de violaciones solo existe donde el JSON lo trae (gen 0 = initial, última = final).
    violations: view === 0 ? result.initial.violations
              : view === h.length - 1 ? result.final.violations : null,
  };
}

// Estado dibujable para una vista: "initial" | "final" | número de generación.
export function frame(result, view) {
  const snap = snapshot(result, view);
  const sc = result.scenario;
  const zone = z => ({ ...toLL([z.lat, z.lon]), id: z.id, name: z.name ?? z.id, radius: z.radius_deg });
  return {
    view,
    gen: viewGen(result, view),
    sats: snap.sats.map((s, i) => ({
      ...toLL(s), i, radius: sc.footprint_deg,
      violating: snap.violations ? snap.violations.some(v => v.sat === i) : null,
    })),
    regions: sc.regions.map(r => ({
      ...toLL([r.lat, r.lon]), id: r.id, name: r.name ?? r.id, priority: r.priority,
      weight: r.weight, radius: r.radius_deg,
      cov: snap.coverage[r.id], cls: coverageClass(snap.coverage[r.id]),
    })),
    debris: sc.debris_zones.map(zone),
    occupied: sc.occupied.map(zone),
    fitness: snap.fitness,
    nViol: snap.nViol,
    violations: snap.violations,
  };
}

// ---------------------------------------------------------------------------
// Verificación dibujo ↔ JSON
// ---------------------------------------------------------------------------

const TOL = 1e-9;
const near = (a, b) => typeof a === "number" && typeof b === "number" && Math.abs(a - b) <= TOL;

// `drawn` son los datos leídos de las capas reales del globo (no de frame()):
// { regions: [{id, lat, lng, cls, radius?}], sats: [{lat, lng}], debris: [...], occupied: [...] }.
export function verify(result, view, drawn) {
  const f = frame(result, view);
  const rows = f.regions.map(r => {
    const d = drawn.regions.find(x => x.id === r.id);
    const posOk = !!d && d.lat === r.lat && d.lng === r.lng;
    const radiusOk = !d || d.radius === undefined || near(d.radius, r.radius);
    return { id: r.id, name: r.name, priority: r.priority, weight: r.weight,
             jsonCov: r.cov, jsonCls: r.cls, drawnCls: d?.cls ?? null,
             ok: !!d && d.cls === r.cls && posOk && radiusOk };
  });
  const zonesOk = (dz, fz) => dz.length === fz.length &&
    fz.every(z => dz.some(x => x.id === z.id && x.lat === z.lat && x.lng === z.lng));
  const nCoveredJSON = typeof view === "number" ? result.history[view].n_covered
                                                : f.regions.filter(r => r.cls === "covered").length;
  const counts = {
    sats: drawn.sats.length === result.scenario.n_sats && drawn.sats.length === f.sats.length,
    satPositions: drawn.sats.length === f.sats.length &&
                  f.sats.every((s, i) => drawn.sats[i].lat === s.lat && drawn.sats[i].lng === s.lng),
    debris: zonesOk(drawn.debris, f.debris),
    occupied: zonesOk(drawn.occupied, f.occupied),
    regions: drawn.regions.length === f.regions.length,
    nCovered: rows.filter(r => r.drawnCls === "covered").length === nCoveredJSON,
  };
  return { rows, counts, nCoveredJSON,
           ok: rows.every(r => r.ok) && Object.values(counts).every(Boolean) };
}

// ---------------------------------------------------------------------------
// Series para el panel (curvas SVG)
// ---------------------------------------------------------------------------

export const series = (result, key) => result.history.map(h => h[key]);

// Extremos de varias series ignorando null (-inf en strict). null si no hay ningún valor.
export function extent(...arrays) {
  let lo = Infinity, hi = -Infinity;
  for (const a of arrays) for (const v of a) if (v !== null && Number.isFinite(v)) {
    if (v < lo) lo = v;
    if (v > hi) hi = v;
  }
  if (lo === Infinity) return null;
  if (lo === hi) { lo -= 0.5; hi += 0.5; }
  return [lo, hi];
}

// Puntos "x,y" de una polilínea por tramo; un null corta la línea (hueco).
export function polylineSegments(values, { width, height, min, max }) {
  const n = values.length;
  const sx = g => (n <= 1 ? width / 2 : (g / (n - 1)) * width);
  const sy = v => height - ((v - min) / (max - min)) * height;
  const segs = [];
  let cur = [];
  values.forEach((v, g) => {
    if (v === null || !Number.isFinite(v)) {
      if (cur.length) segs.push(cur);
      cur = [];
    } else {
      cur.push(`${sx(g).toFixed(2)},${sy(v).toFixed(2)}`);
    }
  });
  if (cur.length) segs.push(cur);
  return segs.map(s => s.join(" "));
}

// Paso de reproducción adaptativo: cuántas generaciones avanzar en dtMs a speed gens/s.
export function playStep(acc, dtMs, speed) {
  const total = acc + (dtMs / 1000) * speed;
  const step = Math.floor(total);
  return { step, acc: total - step };
}

// ---------------------------------------------------------------------------
// Listado de directorio de `python -m http.server`
// ---------------------------------------------------------------------------

// Devuelve los .json enlazados (sin reval_*) y los subdirectorios (sin ../ ni escenarios/).
export function parseListing(html) {
  const files = [], dirs = [];
  for (const m of html.matchAll(/<a\s[^>]*href\s*=\s*"([^"]+)"/gi)) {
    let href;
    try { href = decodeURIComponent(m[1]); } catch { href = m[1]; }
    if (/^[a-z]+:|^\/|^\.\.?\//i.test(href) || href.includes("?") || href.includes("#")) continue;
    if (href.endsWith("/")) {
      const name = href.slice(0, -1);
      if (name && !name.includes("/") && name !== "escenarios") dirs.push(href);
    } else if (href.toLowerCase().endsWith(".json") && !href.split("/").pop().startsWith("reval_")) {
      files.push(href);
    }
  }
  return { files, dirs };
}

// ---------------------------------------------------------------------------
// Formato
// ---------------------------------------------------------------------------

export const fmtFit = v => (v === null || v === undefined ? "−∞" : v.toFixed(6));
export const fmtCov = v => (typeof v === "number" ? v.toFixed(6) : "—");

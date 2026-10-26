"""Figuras de los experimentos (matplotlib, backend Agg). Leen exp_runs/*.csv y exp_json/*.json."""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

import analysis  # noqa: E402
from astroshield import geometry  # noqa: E402

# Paleta propia (orden categórico fijo, validado para 3 series: azul, naranja, aqua)
MODE_COLOR = {"penalty": "#2a78d6", "repair": "#eb6834", "strict": "#1baf7a"}
NEUTRAL = "#8a8984"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
DEBRIS, OCCUPIED, REGION = "#52514e", "#6250d6", "#008300"
SAVE = {"dpi": 130, "metadata": {"Software": None}, "bbox_inches": "tight"}

plt.rcParams.update({
    "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.spines.top": False,
    "axes.spines.right": False, "font.size": 9, "legend.frameon": False, "figure.facecolor": "white",
})


def _curves(out: Path, name: str) -> dict[str, list[dict]]:
    p = out / "exp_runs" / f"curvas_{name}.csv"
    return analysis._groups(analysis.read_csv(p)) if p.exists() else {}


def _rows(out: Path, name: str) -> list[dict]:
    p = out / "exp_runs" / f"{name}.csv"
    return analysis.read_csv(p) if p.exists() else []


def _arr(rows, key):
    return np.array([np.nan if r.get(key) is None else r[key] for r in rows], dtype=float)


def _mode_of(cfg: str) -> str:
    return cfg.rsplit("_", 1)[-1]


def _n_seeds(rows: list[dict]) -> int:
    return len({r["seed"] for r in rows})


def p2_curves(out: Path, dest: Path) -> None:
    n = _n_seeds(_rows(out, "base"))
    cur = _curves(out, "base")
    rnd = _curves(out, "aleatoria").get("base_aleatoria")
    if not cur:
        return
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharey=False)
    for cfg, rows in cur.items():
        c = MODE_COLOR.get(_mode_of(cfg), NEUTRAL)
        g = _arr(rows, "gen")
        axes[0].fill_between(g, _arr(rows, "best_p25"), _arr(rows, "best_p75"), color=c, alpha=0.18, lw=0)
        axes[0].plot(g, _arr(rows, "best_median"), color=c, lw=2, label=f"{_mode_of(cfg)} (mediana, IQR)")
        axes[1].plot(g, _arr(rows, "mean_mean"), color=c, lw=2, label=_mode_of(cfg))
    if rnd:
        axes[0].plot(_arr(rnd, "gen"), _arr(rnd, "best_median"), color=NEUTRAL, lw=2, ls="--",
                     label="aleatoria, mismo presupuesto")
    axes[0].axhline(analysis.ORACLES["base"], color=INK, lw=1, ls=":", label="óptimo 1.023077")
    axes[0].set(title=f"Mejor aptitud por generación ({n} semillas)", xlabel="generación", ylabel="aptitud del mejor")
    axes[1].set(title=f"Aptitud media de la población (media de {n} semillas)", xlabel="generación",
                ylabel="aptitud media (finitas)")
    axes[0].legend(loc="lower right")
    axes[1].legend(loc="lower right")
    fig.savefig(dest / "p2_curvas_base.png", **SAVE)
    plt.close(fig)
    for key, title, fname in (("diversity_mean", f"Diversidad (°, media de {n} semillas)", "p2_diversidad.png"),
                              ("n_invalid_mean", "Individuos inválidos por generación (de 100)", "p2_invalidos.png")):
        fig, ax = plt.subplots(figsize=(6, 3.6))
        for cfg, rows in cur.items():
            ax.plot(_arr(rows, "gen"), _arr(rows, key), color=MODE_COLOR.get(_mode_of(cfg), NEUTRAL), lw=2,
                    label=_mode_of(cfg))
        ax.set(title=title, xlabel="generación")
        ax.legend()
        fig.savefig(dest / fname, **SAVE)
        plt.close(fig)


def _box(ax, groups: dict[str, np.ndarray], colors: list[str]):
    labels = list(groups)
    bp = ax.boxplot([groups[k] for k in labels], showmeans=True, widths=0.5, patch_artist=True,
                    meanprops={"marker": "D", "markerfacecolor": "white", "markeredgecolor": INK, "markersize": 5},
                    medianprops={"color": INK, "lw": 1.5}, flierprops={"markersize": 4})
    for patch, c in zip(bp["boxes"], colors):
        patch.set_facecolor(c)
        patch.set_alpha(0.55)
        patch.set_edgecolor(INK2)
    rng = np.random.default_rng(0)   # solo para el jitter visual de los puntos
    for i, k in enumerate(labels, start=1):
        ax.scatter(i + rng.uniform(-0.12, 0.12, len(groups[k])), groups[k], s=10, color=INK2, alpha=0.6, zorder=3)
    ax.set_xticks(range(1, len(labels) + 1), labels)


def p7_box(out: Path, dest: Path) -> None:
    rows = _rows(out, "base")
    if not rows:
        return
    g = analysis._groups(rows)
    fig, ax = plt.subplots(figsize=(6, 4))
    _box(ax, {k: _arr(v, "final_penalty_fitness") for k, v in g.items()},
         [MODE_COLOR.get(_mode_of(k), NEUTRAL) for k in g])
    ax.axhline(analysis.ORACLES["base"], color=INK, lw=1, ls=":", label="óptimo 1.023077")
    ax.axhline(1.0, color=NEUTRAL, lw=1, ls="--", label="umbral 6/6 (1.0)")
    ax.set(title=f"Aptitud final (penalty) en base, {_n_seeds(rows)} semillas", ylabel="aptitud final")
    ax.legend(loc="lower left")
    fig.savefig(dest / "p7_boxplot.png", **SAVE)
    plt.close(fig)


def p5_box(out: Path, dest: Path) -> None:
    red = _rows(out, "reducido")
    if not red:
        return
    g = {**analysis._groups(_rows(out, "base")), **analysis._groups(red)}
    fig, ax = plt.subplots(figsize=(8, 4))
    _box(ax, {k.replace("_", "\n", 1): _arr(v, "final_penalty_fitness") for k, v in g.items()},
         [MODE_COLOR.get(_mode_of(k), NEUTRAL) for k in g])
    ax.axhline(analysis.ORACLES["base"], color=INK, lw=1, ls=":", label="óptimo base 1.023077")
    ax.axhline(1.0, color=NEUTRAL, lw=1, ls="--", label="umbral 6/6 (1.0)")
    ax.set(title=f"P5 · Aptitud final (penalty): base vs reducido, {_n_seeds(red)} semillas", ylabel="aptitud final")
    ax.legend(loc="lower left")
    fig.savefig(dest / "p5_boxplot.png", **SAVE)
    plt.close(fig)


def p5_margin(out: Path, dest: Path) -> None:
    red = _rows(out, "reducido")
    if not red:
        return
    base = _rows(out, "base")
    vals = np.concatenate([_arr(red, "min_margin_deg"), _arr(base, "min_margin_deg")])
    bins = np.linspace(np.nanmin(vals), np.nanmax(vals), 40)
    fig, ax = plt.subplots(figsize=(8, 4))
    if base:
        ax.hist(_arr(base, "min_margin_deg"), bins=bins, color=NEUTRAL, alpha=0.5, label="base (3 modos)")
    for m, rs in analysis._groups(red, "mode").items():
        ax.hist(_arr(rs, "min_margin_deg"), bins=bins, histtype="step", lw=2, color=MODE_COLOR.get(m, NEUTRAL),
                label=f"reducido {m}")
    ax.axvline(0, color=INK, lw=1, label="borde de zona (0°)")
    ax.axvline(analysis.P5_MARGIN_ACTIVE, color=INK, lw=1, ls=":", label=f"{analysis.P5_MARGIN_ACTIVE:g}° (activa)")
    ax.set(title="P5 · Margen mínimo satélite–zona al final (min_margin_deg)", xlabel="margen mínimo (°)",
           ylabel="ejecuciones")
    ax.legend(loc="upper center")
    fig.savefig(dest / "p5_margen.png", **SAVE)
    plt.close(fig)


def p6_box(out: Path, dest: Path) -> None:
    inv = _rows(out, "inviable")
    if not inv:
        return
    g = analysis._groups(inv)
    fig, ax = plt.subplots(figsize=(6, 4))
    _box(ax, {k: _arr(v, "final_penalty_fitness") for k, v in g.items()},
         [MODE_COLOR.get(_mode_of(k), NEUTRAL) for k in g])
    ax.axhline(analysis.P6_CAP, color=INK, lw=1, ls=":", label=f"óptimo inviable {analysis.P6_CAP:g} (§10)")
    ax.set(title=f"P6 · Aptitud final (penalty) en inviable, {_n_seeds(inv)} semillas", ylabel="aptitud final")
    ax.legend(loc="lower left")
    fig.savefig(dest / "p6_boxplot.png", **SAVE)
    plt.close(fig)


def _cap(lat, lon, r, n=180):
    """Contorno de un casquete esférico (fórmula de destino), con cortes en el salto ±180."""
    la, lo = np.radians(lat), np.radians(lon)
    d = np.radians(r)
    b = np.linspace(0, 2 * np.pi, n)
    la2 = np.arcsin(np.sin(la) * np.cos(d) + np.cos(la) * np.sin(d) * np.cos(b))
    lo2 = lo + np.arctan2(np.sin(b) * np.sin(d) * np.cos(la), np.cos(d) - np.sin(la) * np.sin(la2))
    x = geometry.wrap_lon(np.degrees(lo2)).astype(float)
    y = np.degrees(la2)
    jumps = np.where(np.abs(np.diff(x)) > 180)[0]
    x = np.insert(x, jumps + 1, np.nan)
    y = np.insert(y, jumps + 1, np.nan)
    return x, y


def _draw_scenario(ax, sc: dict, footprint_of=None):
    for z in sc["debris_zones"]:
        ax.plot(*_cap(z["lat"], z["lon"], z["radius_deg"]), color=DEBRIS, lw=1.4)
        ax.text(z["lon"], z["lat"], z["id"], fontsize=6, color=DEBRIS, ha="center", va="center")
    for z in sc["occupied"]:
        ax.plot(*_cap(z["lat"], z["lon"], z["radius_deg"]), color=OCCUPIED, lw=1.4, ls="--")
        ax.text(z["lon"], z["lat"], z["id"], fontsize=6, color=OCCUPIED, ha="center", va="center")
    for r in sc["regions"]:
        ax.plot(*_cap(r["lat"], r["lon"], r["radius_deg"]), color=REGION, lw=1.2)
        ax.text(r["lon"], r["lat"] + r["radius_deg"] + 2, r["id"], fontsize=6, color=REGION, ha="center")
    ax.set(xlim=(-180, 180), ylim=(-90, 90), xlabel="longitud (°)", ylabel="latitud (°)")
    ax.set_aspect("equal")


def p1_map(out: Path, dest: Path) -> None:
    p = out / "exp_json" / "base_repair_s42.json"
    if not p.exists():
        return
    res = json.loads(p.read_text(encoding="utf-8"))
    sc = res["scenario"]
    fig, axes = plt.subplots(1, 2, figsize=(13, 3.8))
    for ax, key, title in ((axes[0], "initial", "Inicial (gen 0, mejor individuo)"), (axes[1], "final", "Final")):
        _draw_scenario(ax, sc)
        for i, s in enumerate(res[key]["sats"]):
            ax.plot(*_cap(s[0], s[1], sc["footprint_deg"]), color=MODE_COLOR["repair"], lw=1)
            ax.plot(s[1], s[0], "o", ms=5, color=MODE_COLOR["repair"], mec="white", mew=0.8)
            ax.text(s[1] + 2, s[0] + 2, str(i), fontsize=6, color=INK)
        fit = res[key]["fitness"]
        ax.set_title(f"{title}: aptitud {fit:.6f}" if fit is not None else title)
    fig.suptitle("P1 · base, repair, semilla 42 (footprint 10°; verde = regiones, gris = desechos, "
                 "violeta discontinuo = ocupados)", fontsize=9)
    fig.savefig(dest / "p1_mapa.png", **SAVE)
    plt.close(fig)


def p3_map(out: Path, dest: Path) -> None:
    fin = _rows(out, "finales_base")
    if not fin:
        return
    sc = json.loads((analysis.ROOT / "scenarios" / "base.json").read_text(encoding="utf-8"))
    g = analysis._groups(fin)
    fig, axes = plt.subplots(len(g), 1, figsize=(8, 4 * len(g)))
    for ax, (cfg, rows) in zip(np.atleast_1d(axes), g.items()):
        _draw_scenario(ax, sc)
        ax.scatter(_arr(rows, "lon"), _arr(rows, "lat"), s=8, color=MODE_COLOR.get(_mode_of(cfg), NEUTRAL),
                   alpha=0.7, zorder=3)
        ax.set_title(f"{cfg}: {len(rows)} satélites finales de {len({r['seed'] for r in rows})} semillas")
    fig.savefig(dest / "p3_mapa_finales.png", **SAVE)
    plt.close(fig)


def p9_footprint(out: Path, dest: Path) -> None:
    rows = _rows(out, "footprint")
    if not rows:
        return
    g = sorted(analysis._groups(rows).items(), key=lambda kv: kv[1][0]["footprint_deg"])
    fs = [v[0]["footprint_deg"] for _, v in g]
    succ = [sum(analysis.success(r, 6) for r in v) / len(v) for _, v in g]
    ci = np.array([analysis.wilson(sum(analysis.success(r, 6) for r in v), len(v)) for _, v in g])
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    axes[0].errorbar(fs, succ, yerr=[np.array(succ) - ci[:, 0], ci[:, 1] - np.array(succ)], color=MODE_COLOR["repair"],
                     lw=2, marker="o", ms=7, capsize=3)
    axes[0].axvline(18.2, color=NEUTRAL, ls="--", lw=1, label="régimen trivial (18.2°)")
    axes[0].set(title="Éxito (válida y 6/6) vs footprint, IC Wilson 95 %", xlabel="footprint F (°)",
                ylabel=f"fracción de {_n_seeds(rows)} semillas", ylim=(-0.05, 1.05))
    axes[0].legend(loc="lower right")
    _box(axes[1], {f"{f:g}": _arr(v, "final_penalty_fitness") for f, (_, v) in zip(fs, g)},
         [MODE_COLOR["repair"]] * len(g))
    axes[1].axhline(analysis.ORACLES["base"], color=INK, lw=1, ls=":", label="1.023077")
    axes[1].set(title="Aptitud final (repair, 100 gens)", xlabel="footprint F (°)", ylabel="aptitud final")
    axes[1].legend(loc="lower right")
    fig.savefig(dest / "p9_footprint.png", **SAVE)
    plt.close(fig)


def p10_pop(out: Path, dest: Path) -> None:
    rows = _rows(out, "poblacion")
    if not rows:
        return
    g = sorted(analysis._groups(rows).items(), key=lambda kv: kv[1][0]["pop_size"])
    cur = _curves(out, "poblacion")
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    _box(axes[0], {f"P={v[0]['pop_size']}\n{v[0]['gens']} gens": _arr(v, "final_penalty_fitness") for _, v in g},
         [MODE_COLOR["repair"]] * len(g))
    axes[0].axhline(analysis.ORACLES["base"], color=INK, lw=1, ls=":", label="óptimo 1.023077")
    axes[0].set(title="Aptitud final a presupuesto fijo (≈20 100 evaluaciones)", ylabel="aptitud final")
    axes[0].legend(loc="lower right")
    shades = ["#9ec5f4", "#5b9be6", "#2a78d6", "#1a4f91"]   # rampa secuencial de un solo tono (P creciente)
    for (cfg, v), c in zip(g, shades):
        rows_c = cur.get(cfg, [])
        P = v[0]["pop_size"]
        axes[1].plot(_arr(rows_c, "gen") * P + P, _arr(rows_c, "best_median"), color=c, lw=2, label=f"P={P}")
    axes[1].axhline(analysis.ORACLES["base"], color=INK, lw=1, ls=":")
    axes[1].set(title="Mejor aptitud mediana vs evaluaciones", xlabel="evaluaciones", ylabel="aptitud del mejor")
    axes[1].legend(loc="lower right")
    fig.savefig(dest / "p10_poblacion.png", **SAVE)
    plt.close(fig)


def make_all(out: Path) -> list[Path]:
    out = Path(out)
    dest = out / "exp_figuras"
    dest.mkdir(parents=True, exist_ok=True)
    for fn in (p1_map, p2_curves, p3_map, p5_box, p5_margin, p6_box, p7_box, p9_footprint, p10_pop):
        fn(out, dest)
    return sorted(dest.glob("*.png"))

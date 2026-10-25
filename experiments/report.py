"""Inserta las tablas generadas (results/exp_tablas/*.md) en docs/03_pruebas.md.

    python experiments/report.py            # reescribe el documento
    python experiments/report.py --check    # sale con 1 si el documento no está sincronizado

Cada tabla vive entre `<!-- tabla:NOMBRE -->` y `<!-- /tabla -->`; el contenido se toma de
exp_tablas/NOMBRE.md. Así ninguna cifra de las tablas se escribe a mano.
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERN = re.compile(r"(<!-- tabla:([a-z0-9_]+) -->\n)(.*?)(<!-- /tabla -->)", re.S)


def render(doc: str, tables_dir: Path) -> tuple[str, list[str]]:
    """Devuelve (documento con las tablas insertadas, nombres de tabla que faltan en tables_dir)."""
    missing: list[str] = []

    def sub(m):
        p = tables_dir / f"{m.group(2)}.md"
        if not p.exists():
            missing.append(m.group(2))
            return m.group(0)
        return m.group(1) + p.read_text(encoding="utf-8").replace("\r\n", "\n") + m.group(4)

    return PATTERN.sub(sub, doc), missing


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--doc", default=str(ROOT / "docs" / "03_pruebas.md"))
    ap.add_argument("--tables", default=str(ROOT / "results" / "exp_tablas"))
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    doc_path = Path(a.doc)
    doc = doc_path.read_text(encoding="utf-8").replace("\r\n", "\n")
    new, missing = render(doc, Path(a.tables))
    for name in missing:
        print(f"falta la tabla {name}.md", file=sys.stderr)
    if a.check:
        ok = new == doc and not missing
        print("documento sincronizado" if ok else "documento DESACTUALIZADO: corre experiments/report.py")
        return 0 if ok else 1
    doc_path.write_text(new, encoding="utf-8", newline="\n")
    print(f"{doc_path}: {len(PATTERN.findall(new))} tablas")
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())

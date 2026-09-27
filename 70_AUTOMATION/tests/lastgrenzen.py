#!/usr/bin/env python3
"""PHASE 7 — Lastgrenzen in der REALEN Form: N Projekte im Katalog + Baum.
N = 10 / 50 / 100 / 420  (420 = die ehrlich gerechnete Kapazitaet aus v1.3 K7).
Messwerte, keine Hochrechnung. Baeume liegen unter <sandbox>/grenzen/ und werden entfernt.
"""
from __future__ import annotations
import json, os, resource, shutil, subprocess, sys, time
from pathlib import Path

S = Path(__file__).resolve().parents[3]; M = next(p for p in Path(__file__).resolve().parents if (p / "ordner.sh").is_file())
sys.path.insert(0, str(M / "70_AUTOMATION/validation")); sys.path.insert(0, str(M / "70_AUTOMATION/indexing"))
import rules as R, schema_check, indexer

SANDBOX = Path(__file__).resolve().parents[3]


def nur_sandkasten(p) -> Path:
    """Waechter: jede schreibende/loeschende Operation MUSS in der Sandbox liegen."""
    p = Path(p)
    if str(p).startswith(str(SANDBOX) + "/") or p == SANDBOX:
        return p
    raise AssertionError(f"AUSSERHALB DER SANDBOX — verweigert: {p}")

KOPF = (
'schema_version: 1\nnotfallkontakt: "grenze"\npassphrase_ort: "keine"\nrepos:\n'
        '  - schema_version: 1\n    name: system_meta\n    class: system\n    status: paused\n'
        '    owner: t\n    seit: "2026-09-21"\n    bereich: 00_SYSTEM\n    pfad: 00_SYSTEM\n    git: false\n')


def baue(root: Path, n: int):
    if root.exists(): shutil.rmtree(nur_sandkasten(root))
    (root / "00_SYSTEM/manifest").mkdir(parents=True); (root / "00_SYSTEM/schemas").mkdir(parents=True)
    (root / "00_SYSTEM/schemas/repos.schema.json").write_text(
        (M / "00_SYSTEM/schemas/repos.schema.json").read_text(encoding="utf-8"), encoding="utf-8")
    (root / "40_DATEN/pointers").mkdir(parents=True)
    kat = [KOPF]; t0 = time.perf_counter()
    for i in range(n):
        if i < 400:
            thema, name = f"t{i//20:02d}", f"2026-09-21_projekt_{i:03d}"
            pfad = f"20_PROJEKTE/domains/{thema}/{name}"
        else:
            name = f"2026-09-21_eigenstaendig_{i:03d}"; pfad = f"20_PROJEKTE/standalone/{name}"
        for sub in ("01_input", "02_work", "03_output"):
            (root / pfad / sub).mkdir(parents=True, exist_ok=True)
        (root / pfad / "README.md").write_text(f"# {name}\n\nProjekt Nr. {i}. Inhalt: FTS5 Suche Prototyp.\n", encoding="utf-8")
        kat.append(f'  - schema_version: 1\n    name: {name}\n    class: project\n    status: active\n'
                   f'    owner: t\n    seit: "2026-09-21"\n    bereich: 20_PROJEKTE\n    pfad: {pfad}\n'
                   f'    git: false\n    review_am: "2027-09-21"\n    beschreibung: "Testprojekt {i}"\n')
    (root / "00_SYSTEM/manifest/repos.yaml").write_text("".join(kat), encoding="utf-8")
    return {"aufbau_s": round(time.perf_counter() - t0, 2), "projekte": n}


def messe(root: Path, n: int):
    import yaml
    kat = yaml.safe_load((root / "00_SYSTEM/manifest/repos.yaml").read_text(encoding="utf-8"))
    t0 = time.perf_counter(); ctx = R.run_all(root, kat); t_v = time.perf_counter() - t0
    fehler = [f"{f['regel']}/{f['schwere']}" for f in ctx.findings]
    t0 = time.perf_counter(); ib = indexer.build(root, still=True); t_i = time.perf_counter() - t0
    zeiten = []
    for q in ["projekt", "FTS5", "Testprojekt"]:
        t0 = time.perf_counter(); indexer.search(root, q, limit=20); zeiten.append(time.perf_counter() - t0)
    return {"projekte": n, "validator_s": round(t_v, 3), "befunde": len(ctx.findings), "befundliste": fehler[:5],
            "index_s": round(ib["dauer_s"], 3), "index_mb": round(ib["groesse_b"] / 1e6, 3),
            "dokumente": sum(ib["anzahl"].values()),
            "suche_s_mittel": round(sum(zeiten) / len(zeiten), 4),
            "speicher_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)}


if __name__ == "__main__":
    ziel = S / "grenzen/ergebnisse.jsonl"; ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text("", encoding="utf-8")
    print(f"{'Projekte':>9} {'Aufbau':>8} {'Validator':>10} {'Befunde':>8} {'Index':>8} {'Index MB':>9} {'Suche Ø':>9} {'Speicher':>9}")
    for n in [10, 50, 100, 420]:
        root = S / "grenzen" / f"proj_{n}"
        b = baue(root, n); m = messe(root, n); m.update(b)
        print(f"{n:>9} {b['aufbau_s']:>7}s {m['validator_s']:>9}s {m['befunde']:>8} {m['index_s']:>7}s "
              f"{m['index_mb']:>8} {m['suche_s_mittel']*1000:>7.1f}ms {m['speicher_mb']:>7}MB")
        with ziel.open("a", encoding="utf-8") as fh: fh.write(json.dumps(m, ensure_ascii=False) + "\n")
        shutil.rmtree(nur_sandkasten(root), ignore_errors=True)
    print("Ergebnisse:", ziel)

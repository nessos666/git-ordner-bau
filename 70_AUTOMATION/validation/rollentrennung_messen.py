#!/usr/bin/env python3
"""ROLLENTRENNUNG MESSEN (24.09.2026) — nicht behaupten, sondern nachrechnen.

Die Pruefzeile sagte bisher "ROLLENTRENNUNG: NICHT VERIFIZIERT". Das war ehrlich, aber
unbefriedigend. Diese Messung beantwortet die Frage mit Zahlen:

  LESEN:  Alle lesenden Befehle des Baums laufen gegen den Baum UND die angebundenen Bestaende.
          Vorher/nachher wird jede Datei verglichen (Groesse + Aenderungszeit + Stichprobe Pruefsumme).
          Erwartung: 0 Aenderungen AUSSERHALB des Baums.
  SCHREIBEN: Der Baum schreibt nur in seine eigenen Bereiche; 60_RUNTIME und .git werden dabei
          absichtlich ausgenommen (dort arbeitet der Index).

Ergebnis -> 50_INFRA/rollentrennung.yaml (gemessen, mit Datum). Fehlt die Datei, sagt die
Pruefzeile weiter ehrlich "NICHT VERIFIZIERT".
Exit: 0 = 0 Schreibspuren ausserhalb · 2 = Spuren gefunden
"""
from __future__ import annotations
import hashlib, json, os, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = sys.executable or "python3"
AUS_BAUM = {"60_RUNTIME", ".git", "__pycache__"}


def ziele() -> list[Path]:
    z = [ROOT]
    p = ROOT / "40_DATEN/pointers"
    if p.is_dir():
        for f in sorted(p.glob("*.yaml")):
            for zeile in f.read_text(encoding="utf-8").splitlines():
                if zeile.strip().startswith("ziel:"):
                    t = Path(zeile.split(":", 1)[1].strip())
                    if t.is_dir() and t not in z:
                        z.append(t)
                    break
    return z


def moment(wurzel: Path) -> dict[str, tuple[int, int]]:
    stand = {}
    for dp, dns, fns in os.walk(wurzel):
        if wurzel == ROOT:
            dns[:] = [d for d in dns if d not in AUS_BAUM]
        for f in fns:
            p = Path(dp) / f
            try:
                st = p.lstat()
            except OSError:
                continue
            stand[str(p)] = (st.st_size, st.st_mtime_ns)
    return stand


def stichprobe_hash(wurzel: Path, n: int = 100) -> dict[str, str]:
    pfade = sorted(moment(wurzel))[::max(1, len(moment(wurzel)) // n)][:n]
    h = {}
    for p in pfade:
        try:
            h[p] = hashlib.sha256(Path(p).read_bytes()).hexdigest()
        except OSError:
            h[p] = "UNLESBAR"
    return h


def lesende_befehle(wurzel: Path) -> list[str]:
    return [
        f"{PY} -B {ROOT}/70_AUTOMATION/indexing/indexer.py search Island --root {ROOT}",
        f"{PY} -B {ROOT}/70_AUTOMATION/pointers/finden.py --root {ROOT} --begriff Island",
        f"{PY} -B {ROOT}/70_AUTOMATION/pointers/suchen_namen.py dateien --root {ROOT} --muster island",
        f"{PY} -B {ROOT}/70_AUTOMATION/pointers/suchen_namen.py springen --root {ROOT} --muster island",
        f"{PY} -B {ROOT}/70_AUTOMATION/pointers/doppelte.py --pfad {wurzel} --ab-groesse 64",
        f"{PY} -B {ROOT}/70_AUTOMATION/validation/check_all.py --root {ROOT}",
    ]


def main() -> int:
    orte = ziele()
    print("Gepruefte Orte:", *[str(o) for o in orte], sep="\n  ")
    vorher = {str(o): moment(o) for o in orte}
    vorher_hash = {str(o): stichprobe_hash(o) for o in orte}
    t0 = time.time()
    for o in orte:
        for b in lesende_befehle(o):
            subprocess.run(["bash", "-lc", b + " >/dev/null 2>&1"], capture_output=True)
    dauer = time.time() - t0
    nachher = {str(o): moment(o) for o in orte}
    aenderungen, gesamt = [], 0
    for o in orte:
        v, n = vorher[str(o)], nachher[str(o)]
        gesamt += len(v)
        for p in sorted(set(v) | set(n)):
            if p not in n:
                aenderungen.append(f"GELOESCHT: {p}")
            elif p not in v:
                aenderungen.append(f"NEU: {p}")
            elif v[p] != n[p]:
                aenderungen.append(f"GEAENDERT: {p}")
        for p, h in vorher_hash[str(o)].items():
            try:
                jetzt = hashlib.sha256(Path(p).read_bytes()).hexdigest()
            except OSError:
                jetzt = "UNLESBAR"
            if jetzt != h:
                aenderungen.append(f"INHALT GEAENDERT (Stichprobe): {p}")
    ergebnis = {
        "datum": time.strftime("%Y-%m-%d"),
        "orte": [str(o) for o in orte],
        "dateien_geprueft": gesamt,
        "stichprobe_hashes": sum(len(v) for v in vorher_hash.values()),
        "lesende_befehle": sum(len(lesende_befehle(o)) for o in orte),
        "dauer_s": round(dauer, 1),
        "aenderungen": aenderungen[:50],
        "anzahl_aenderungen": len(aenderungen),
        "verdict": "VERIFIZIERT" if not aenderungen else "SPUREN GEFUNDEN",
    }
    (ROOT / "50_INFRA/rollentrennung.yaml").write_text(
        "".join(f"{k}: {json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v}\n"
                for k, v in ergebnis.items()), encoding="utf-8")
    print(f"\n{gesamt} Dateien beobachtet · {ergebnis['lesende_befehle']} lesende Befehle · {dauer:.1f} s")
    print(f"Rollentrennung: {ergebnis['verdict']} — {len(aenderungen)} Schreibspur(en)")
    for a in aenderungen[:10]:
        print("  " + a)
    return 0 if not aenderungen else 2


if __name__ == "__main__":
    sys.exit(main())

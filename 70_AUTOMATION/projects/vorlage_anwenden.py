#!/usr/bin/env python3
"""Vorlage auf einen Projektordner anwenden — Element 3 (24.09.2026).

WARUM: neue Projekte sollen nicht jedes Mal leer anfangen. Die Vorlagen stehen in
`80_VORLAGEN/vorlagen.json` und gehoeren David — er kann sie ohne Programmierkenntnis aendern.
Es wird NICHTS ueberschrieben: existiert ein Unterordner schon, bleibt er unberuehrt.

Aufruf: python3 vorlage_anwenden.py --ordner <Projektordner> --vorlage <name> [--trocken]
Exit:   0 ok · 2 unbekannte Vorlage/Ordner fehlt
"""
from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VORLAGEN = ROOT / "80_VORLAGEN/vorlagen.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ordner", required=True); ap.add_argument("--vorlage", required=True)
    ap.add_argument("--trocken", action="store_true")
    a = ap.parse_args()
    if not VORLAGEN.is_file():
        print(f"STOP: {VORLAGEN} fehlt."); return 2
    daten = json.loads(VORLAGEN.read_text(encoding="utf-8"))
    if a.vorlage not in daten:
        print(f"STOP: Vorlage '{a.vorlage}' unbekannt. Bekannt: {', '.join(sorted(daten))}"); return 2
    ziel = Path(os.path.expanduser(a.ordner)).resolve()
    if not ziel.is_dir():
        print(f"STOP: Ordner '{ziel}' fehlt."); return 2
    gemacht, uebersprungen = [], []
    for unter in daten[a.vorlage]["ordner"]:
        d = ziel / unter
        if d.exists():
            uebersprungen.append(unter); continue
        if not a.trocken:
            d.mkdir(parents=True)
            (d / ".gitkeep").write_text("", encoding="utf-8")
        gemacht.append(unter)
    print(f"Vorlage '{a.vorlage}' ({daten[a.vorlage]['beschreibung']}) auf {ziel} angewendet")
    print(f"  angelegt: {', '.join(gemacht) if gemacht else '-'}")
    if uebersprungen:
        print(f"  unberuehrt gelassen (existierte schon): {', '.join(uebersprungen)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

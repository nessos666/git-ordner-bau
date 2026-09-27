#!/usr/bin/env python3
"""Katalog bereinigen — Eintraege entfernen, die im Baum auf NICHTS zeigen (24.09.2026).

WARUM: ein frisch angelegter Baum (spross) erbte Katalogeintraege des Elternbaums, z. B.
`bereich: 60_RUNTIME, pfad: 60_RUNTIME/artefakt/modell_test`. Im neuen Baum existiert der Pfad nicht
-> K4 meldet einen Fehler. Dieser Aufraeumer entfernt solche Eintraege und SAGT, welche.

Regel: ein Eintrag bleibt nur, wenn sein `pfad` im Baum tatsaechlich existiert.
Ausnahme (bleibt): Eintraege ohne `pfad` (reine Beschreibungen).
Aufruf: python3 katalog_bereinigen.py --ordner <Baum> [--trocken]
Exit: 0 ok · 2 Katalog fehlt/unlesbar
"""
from __future__ import annotations
import argparse, os, re, sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ordner", required=True); ap.add_argument("--trocken", action="store_true")
    a = ap.parse_args()
    baum = Path(os.path.expanduser(a.ordner)).resolve()
    katalog = baum / "00_SYSTEM/manifest/repos.yaml"
    if not katalog.is_file():
        print(f"STOP: {katalog} fehlt."); return 2
    zeilen = katalog.read_text(encoding="utf-8").splitlines(keepends=True)
    # Bloecke: jede Zeile, die (mit beliebigem Einzug) mit "- " beginnt, startet einen Eintrag.
    start = [i for i, z in enumerate(zeilen) if re.match(r"^\s*-\s", z)]
    if not start:
        print("Keine Eintraege gefunden — nichts zu tun."); return 0
    kopf = zeilen[:start[0]]
    bloecke, entfernt = [], []
    for n, i in enumerate(start):
        ende = start[n + 1] if n + 1 < len(start) else len(zeilen)
        block = zeilen[i:ende]
        text = "".join(block)
        m = re.search(r"^\s*pfad:\s*(\S+)\s*$", text, re.M)
        if m:
            p = m.group(1).strip().strip('"')
            if not (baum / p).exists():
                entfernt.append(p); continue
        bloecke.append(block)
    if entfernt:
        print(f"Entfernt (Pfad existiert im Baum nicht): {len(entfernt)}")
        for p in entfernt:
            print("  -", p)
        if not a.trocken:
            katalog.write_text("".join(kopf) + "".join("".join(b) for b in bloecke), encoding="utf-8")
            print(f"Katalog geschrieben: {katalog} ({len(bloecke)} Eintraege bleiben)")
    else:
        print("Nichts zu entfernen — alle Eintraege zeigen auf vorhandene Pfade.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

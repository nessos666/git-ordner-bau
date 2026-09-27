#!/usr/bin/env python3
"""Erzeugt PRUEFSUMMEN_MASTER.txt AUS der Selbstbeschreibung — eine Quelle der Wahrheit.

Befund 25.09.2026: Dieselben Zahlen standen an zwei Stellen, von zwei Codewegen berechnet
(sha256sum in ordner.sh und sha256 in der Selbstbeschreibung). Gemessen: 114 von 114 Zahlen
identisch, keine Abweichung, der einzige Unterschied war die Selbstbeschreibung selbst.
Deshalb wird die Liste jetzt abgeleitet statt neu gerechnet: weniger Code, ein Rechenweg.

Aufruf: liste_aus_crate.py <baum> [ziel]
"""
import hashlib
import json
import sys
from pathlib import Path


def main() -> int:
    baum = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    ziel = Path(sys.argv[2]) if len(sys.argv) > 2 else baum / "PRUEFSUMMEN_MASTER.txt"
    crate = baum / "ro-crate-metadata.json"
    if not crate.is_file():
        print(f"STOP: Selbstbeschreibung fehlt ({crate}) — erst ./ordner.sh summen", file=sys.stderr)
        return 2
    daten = json.loads(crate.read_text(encoding="utf-8"))
    zeilen = {}
    for e in daten.get("@graph", []):
        if not isinstance(e, dict):
            continue
        kennung = str(e.get("@id", "")).strip()
        summe = e.get("sha256")
        if not summe or not kennung or kennung.startswith(("#", "http", "//")):
            continue
        # Gemessen 25.09.2026: die Kennungen stehen OHNE "./" im Graph.
        rel = kennung[2:] if kennung.startswith("./") else kennung
        if rel in ("", "ro-crate-metadata.json", "PRUEFSUMMEN_MASTER.txt"):
            continue
        if not (baum / rel).is_file():
            print(f"WARNUNG: beschrieben, aber nicht vorhanden: {rel}", file=sys.stderr)
            continue
        zeilen[rel] = summe
    # Die Selbstbeschreibung kann sich nicht selbst enthalten — hier wird sie einmal gerechnet.
    zeilen["ro-crate-metadata.json"] = hashlib.sha256(crate.read_bytes()).hexdigest()
    neu = "".join(f"{zeilen[k]}  {k}\n" for k in sorted(zeilen))
    alt = ziel.read_text(encoding="utf-8") if ziel.is_file() else ""
    prov = ziel.with_suffix(ziel.suffix + ".neu")   # erst schreiben, dann umbenennen:
    prov.write_text(neu, encoding="utf-8")        # ein Abbruch darf die alte Liste nicht zerreissen
    prov.replace(ziel)
    print(f"{ziel.name}: {len(zeilen)} Zeilen aus der Selbstbeschreibung abgeleitet"
          + ("" if neu != alt else " (unveraendert)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())

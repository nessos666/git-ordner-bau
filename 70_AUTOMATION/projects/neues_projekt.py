#!/usr/bin/env python3
"""Neues Projekt mit FESTER NUMMER anlegen — Ausbau-Schritt 3 (23.09.2026).

DAS PROBLEM, DAS DAS LOEST: solange ein Projekt nur einen Namen hat, bricht jedes Umbenennen
die Wege dahin (Links, Skripte, Notizen, Zeiger). Mit einer Nummer vorne bleibt die Kennung
gleich, der Name darf sich jederzeit aendern: 021_island_sprache_2026-09-23  ->  021_island_2026-10-01

    Nummer = Kennung (bleibt)      Name = Beschriftung (darf sich aendern)

Das Werkzeug
  * vergibt die naechste freie dreistellige Nummer (001, 002, ...),
  * legt den Projektordner mit STATUS.md an,
  * traegt das Projekt in den Katalog ein (00_SYSTEM/manifest/repos.yaml),
  * aendert NICHTS an bestehenden Ordnern.

Aufruf:
    python3 neues_projekt.py --root <BAUM> --name "island_sprache" [--bereich standalone] [--datum JJJJ-MM-TT]
"""
from __future__ import annotations
import argparse
import datetime as dt
import re
import sys
from pathlib import Path

NAME_OK = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
KATALOG_KOPF = ("# Katalog = Absicht. Die Dateien sind die Wahrheit ueber die Existenz. (v1.3, Abschnitt 7)")


def freie_nummer(projekte: Path) -> int:
    """Hoechste vergebene Nummer + 1. Nummern werden NIE wiederverwendet."""
    hoechste = 0
    if projekte.is_dir():
        for p in projekte.rglob("*"):
            m = re.match(r"^(\d{3})_", p.name)
            if p.is_dir() and m:
                hoechste = max(hoechste, int(m.group(1)))
    return hoechste + 1


def katalog_eintrag(root: Path, name: str, nummer: int, pfad: str, bereich: str,
                    datum: str, status: str, beschreibung: str) -> None:
    """Haengt einen Projekteintrag im selben Format wie die bestehenden an."""
    katalog = root / "00_SYSTEM/manifest/repos.yaml"
    text = katalog.read_text(encoding="utf-8")
    eintrag = (
        f"\n  - schema_version: 1\n"
        f"    name: {nummer:03d}_{name}_{datum}\n"
        f"    class: project\n"
        f"    status: {status}\n"
        f"    owner: prototyp\n"
        f"    seit: \"{datum}\"\n"
        f"    bereich: 20_PROJEKTE\n"
        f"    pfad: {pfad}\n"
        f"    git: false\n"
        f"    remote: prototyp/{name}\n"
        f"    review_am: \"{int(datum[:4]) + 1}{datum[4:]}\"\n"
        f"    beschreibung: \"{beschreibung}\"\n"
    )
    if "    pfad: " + pfad + "\n" in text:
        print(f"  Katalog: Eintrag existiert bereits — nicht doppelt angelegt.")
        return
    katalog.write_text(text.rstrip("\n") + "\n" + eintrag, encoding="utf-8")
    print(f"  Katalog: Eintrag ergaenzt (00_SYSTEM/manifest/repos.yaml)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--name", required=True, help="kleinbuchstaben, zahlen, _ und - (keine Leerzeichen)")
    ap.add_argument("--bereich", default="standalone", help="z.B. standalone oder domains/recherche")
    ap.add_argument("--datum", default=dt.date.today().isoformat())
    ap.add_argument("--status", default="provisional", choices=["provisional", "active"])
    ap.add_argument("--titel", default="", help="Klartext-Titel fuer den Katalog (Standard: der Name)")
    a = ap.parse_args()

    root = Path(a.root).resolve()
    if not (root / "00_SYSTEM/manifest/repos.yaml").exists():
        print(f"STOP: {root} ist kein Git-Ordner-Baum (00_SYSTEM/manifest/repos.yaml fehlt).")
        return 2
    name = a.name.strip().lower().replace(" ", "_")
    if not NAME_OK.match(name):
        print(f"STOP: Name '{a.name}' ist nicht erlaubt. Erlaubt sind nur a-z, 0-9, _ und - "
              f"(Umlaute/Leerzeichen bitte ersetzen, z.B. 'island_sprache').")
        return 2
    try:
        dt.date.fromisoformat(a.datum)
    except ValueError:
        print(f"STOP: Datum '{a.datum}' ist kein JJJJ-MM-TT."); return 2

    projekte = root / "20_PROJEKTE"
    bereich_pfad = projekte / a.bereich
    nummer = freie_nummer(projekte)
    ordnername = f"{nummer:03d}_{name}_{a.datum}"
    ziel = bereich_pfad / ordnername

    if ziel.exists():
        print(f"STOP: {ziel.relative_to(root)} existiert schon — nichts angefasst."); return 3
    for vorhanden in list(bereich_pfad.glob(f"*_{name}_*")) + list(bereich_pfad.glob(f"{name}_*")):
        print(f"STOP: '{name}' gibt es in diesem Bereich schon ({vorhanden.name}) — "
              f"Nummern werden nicht doppelt vergeben und Namen nicht dupliziert."); return 3

    bereich_pfad.mkdir(parents=True, exist_ok=True)
    ziel.mkdir(parents=False)
    (ziel / "STATUS.md").write_text(
        f"# STATUS — {a.titel or name}\n\n"
        f"- **Kennnummer:** {nummer:03d}  (bleibt dauerhaft — auch wenn der Name sich aendert)\n"
        f"- **Projekt:** {ordnername}\n"
        f"- **Bereich:** 20_PROJEKTE/{a.bereich}\n"
        f"- **Angelegt:** {a.datum}\n"
        f"- **Zustand:** {a.status}\n"
        f"- **Naechster Schritt:** (hier eintragen)\n", encoding="utf-8")
    print(f"ANGELEGT: {(ziel).relative_to(root)}")
    print(f"  Nummer {nummer:03d} ist die Kennung — der Name darf sich spaeter aendern.")
    print(f"  STATUS.md angelegt (wird von K3 verlangt).")
    katalog_eintrag(root, name, nummer, str(ziel.relative_to(root)), a.bereich, a.datum,
                    a.status, a.titel or f"Projekt {name} (aktiv angelegt)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

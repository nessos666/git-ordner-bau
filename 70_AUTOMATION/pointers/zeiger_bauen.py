#!/usr/bin/env python3
"""Zeiger bauen — einen Bestand AUSSERHALB des Baums read-only aufnehmen.

Aufruf:
    zeiger_bauen.py <pfad> [--name NAME] [--root BAUMORDNER] [--trocken]

Was passiert:
  1. Der Quellordner wird NUR GELESEN.
  2. Pruefsummen-Liste (eine Zeile je Datei) -> <BAUM>/60_RUNTIME/zeiger/<NAME>_manifest_liste.txt
     (abgeleitete Daten, nie von Git verfolgt, jederzeit neu erzeugbar)
  3. Zeiger-Datei -> <BAUM>/40_DATEN/pointers/<NAME>.yaml  (klein: nur Zeiger, keine Daten)

Wichtig: Die Definition "Datei" kommt aus rules.zaehle_objekt — EINMAL definiert, von
Pruefer und Werkzeug gemeinsam benutzt. Tote Verweise zaehlen nicht als Datei und werden
in der Liste als Kopfzeile ausgewiesen.
"""
import argparse
import hashlib
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "validation"))
from rules import zaehle_objekt, sha256_datei, SCHWELLE_BYTE  # noqa: E402


def baue(pfad: Path, name: str, root: Path, trocken: bool = False) -> dict:
    if not pfad.exists():
        raise SystemExit(f"Quelle existiert nicht: {pfad}")
    dateien, tote = zaehle_objekt(pfad)
    zeilen, gesamt, einzel = [], 0, 0
    # Punkt 3a (freigegeben 26.09.2026): JEDE Datei bekommt eine eigene Pruefsumme.
    # Vorher galt eine 10-MB-Schwelle (Aggregation ueber die Listenpruefsumme). Recherche
    # und Normen sind eindeutig: keine nimmt Dateien unter einer Groesse aus, 94,9 % der
    # Befragten im NDSA-Survey pruefen dateiweise; Hashen kostet hier ~3 min fuer 341 GB.
    # Pruefsumme DIESER Liste abgesichert (Aggregation). Gemessen 25.09.2026: jede Datei zu hashen
    # kostet bei 341 GB Stunden und bringt nichts, was K8 verlangt.
    for f in sorted(dateien, key=lambda x: str(x)):
        try:
            g = f.stat().st_size
        except OSError:
            zeilen.append(f"-  {f.relative_to(pfad)}")
            continue
        gesamt += g
        zeilen.append(f"{sha256_datei(f)}  {f.relative_to(pfad)}")
        einzel += 1
    kopf = ["# Manifest v3: Einzelpruefsumme fuer JEDE Datei (Punkt 3a, 26.09.2026).",
            "# Die Zeile mit '-' steht nur noch fuer unlesbare/tote Eintraege."]
    if tote:
        kopf += [f"# {len(tote)} toter Verweis(e) — zaehlen NICHT als Datei, nur zur Kenntnis:",
                *[f"#   {x.relative_to(pfad)}" for x in sorted(tote, key=str)],
                "#"]
    txt = "\n".join(kopf + zeilen) + "\n"
    agg = hashlib.sha256(txt.encode()).hexdigest()
    ldir = root / "60_RUNTIME/zeiger"
    pdir = root / "40_DATEN/pointers"
    if not trocken:
        ldir.mkdir(parents=True, exist_ok=True)
        pdir.mkdir(parents=True, exist_ok=True)
        (ldir / f"{name}_manifest_liste.txt").write_text(txt, encoding="utf-8")
        (pdir / f"{name}.yaml").write_text(
            "schema_version: 1\nzeiger:\n"
            f'  - typ: objekt\n    name: "{name}"\n'
            f"    ziel: {pfad}\n"
            f"    groesse: {gesamt}\n    dateien: {len(dateien)}\n"
            f"    sha256: {agg}\n"
            f"    manifest_liste: {name}_manifest_liste.txt\n"
            f"    manifest_version: 3\n"
            f"    einzelpruefsummen_je_datei: ja\n"
            f"    einzelpruefsummen: {einzel}\n"
            f"    datum: {__import__('datetime').date.today().isoformat()}\n"
            f'    rekonstruktion: "Original bleibt am Platz; Liste neu erzeugen mit: '
            f'zeiger_bauen.py {pfad} --name {name}"\n', encoding="utf-8")
    return {"name": name, "dateien": len(dateien), "tote_verweise": len(tote), "einzelpruefsummen": einzel,

            "byte": gesamt, "aggregat": agg, "liste": str(ldir / f"{name}_manifest_liste.txt"),
            "zeiger": str(pdir / f"{name}.yaml")}


def main() -> int:
    ap = argparse.ArgumentParser(description="Bestand read-only aufnehmen -> Zeiger + Pruefsummen-Liste")
    ap.add_argument("pfad")
    ap.add_argument("--name")
    ap.add_argument("--root", default=os.path.expanduser("~/prototyp_baum"))
    ap.add_argument("--trocken", action="store_true", help="nur rechnen, nichts schreiben")
    a = ap.parse_args()
    quelle = Path(os.path.expanduser(a.pfad)).resolve()
    name = a.name or quelle.name
    e = baue(quelle, name, Path(os.path.expanduser(a.root)).resolve(), a.trocken)
    print(f"Name:            {e['name']}")
    print(f"Dateien:         {e['dateien']}")
    print(f"Tote Verweise:   {e['tote_verweise']}")
    print(f"Groesse:         {e['byte']} B ({e['byte']/1048576:.1f} MB)")
    print(f"Aggregat:        {e['aggregat']}")
    print(f"Liste:           {e['liste']}")
    print(f"Zeiger:          {e['zeiger']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

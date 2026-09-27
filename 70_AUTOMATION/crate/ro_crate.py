#!/usr/bin/env python3
"""RO-Crate bauen und pruefen — Element 2 (24.09.2026).

WARUM: RO-Crate ist der Standard, mit dem ein Ordner sich SELBST beschreibt
(eine Datei `ro-crate-metadata.json` im Ordner). Damit ist der Baum fuer fremde
Werkzeuge lesbar, ohne dass jemand unsere Doku kennen muss.

Aufruf:
  python3 ro_crate.py --ordner <Ordner> [--name X] [--beschreibung Y]   # schreiben
  python3 ro_crate.py --pruefen <Ordner>                                # nachrechnen
Exit: 0 ok · 2 ungueltig/Fehler
"""
from __future__ import annotations
import argparse, hashlib, json, os, sys, time
from pathlib import Path

AUS = {".git", "__pycache__", ".venv", "node_modules", "60_RUNTIME", ".mypy_cache"}
DATEI = "ro-crate-metadata.json"
# Selbstdarstellende Dateien NICHT mitzaehlen (24.09.2026):
# PRUEFSUMMEN_MASTER.txt listet den Crate, der Crate listet die Pruefsummen-Datei -> Kreislauf.
# Eine Richtung genuegt: PRUEFSUMMEN_MASTER.txt (Git-Manifest) deckt den Crate mit ab.
KREISLAUF = {"PRUEFSUMMEN_MASTER.txt"}
KONTEXT = "https://w3id.org/ro/crate/1.1/context"


def hash_datei(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def dateien(ordner: Path):
    for dp, dns, fns in os.walk(ordner):
        dns[:] = [d for d in dns if d not in AUS]
        for f in sorted(fns):
            p = Path(dp) / f
            # Gemessen 26.09.2026: Verweise waren hier ausgenommen, standen aber in
            # PRUEFSUMMEN_MASTER.txt (die alte sha256sum-Kette folgte ihnen). Seit die Liste
            # aus der Selbstbeschreibung abgeleitet wird, fehlten sie dort und K9 meldete sie
            # als unbeschrieben. Ein Verweis zaehlt jetzt, wenn sein Ziel IM Baum liegt und eine
            # Datei ist; tote Verweise und Ziele ausserhalb bleiben ausgenommen (Sicherheit).
            if p.is_symlink():
                try:
                    _ziel = p.resolve(strict=True)
                except OSError:
                    continue                      # toter Verweis: Regel K8 meldet ihn
                if not _ziel.is_file() or not str(_ziel).startswith(str(ordner.resolve()) + "/"):
                    continue                      # Ziel ausserhalb: nicht beschreiben
                yield p, p.relative_to(ordner).as_posix()   # GLEICHE Form wie unten!
                continue
            if p.is_file() and p.name != DATEI and p.name not in KREISLAUF:
                yield p, p.relative_to(ordner).as_posix()


def bauen(ordner: Path, name: str, beschreibung: str) -> int:
    if not ordner.is_dir():
        print(f"STOP: '{ordner}' fehlt."); return 2
    teile = [{"@id": DATEI, "@type": "CreativeWork",
              "about": {"@id": "./"}, "conformsTo": {"@id": "https://w3id.org/ro/crate/1.1"},
              "description": "RO-Crate Metadaten fuer " + name},
             {"@id": "./", "@type": "Dataset", "name": name, "description": beschreibung,
              "datePublished": time.strftime("%Y-%m-%d"),
              "conformsTo": {"@id": "https://w3id.org/ro/crate/1.1"},
              "license": {"@id": "https://spdx.org/licenses/CC-BY-4.0"},
              "hasPart": []}]
    anzahl, bytes_ = 0, 0
    for p, rel in dateien(ordner):
        h = hash_datei(p); g = p.stat().st_size
        kennung = "data/" + rel if False else rel      # Dateien liegen direkt im Ordner
        teile[1]["hasPart"].append({"@id": kennung})
        teile.append({"@id": kennung, "@type": "File", "name": p.name,
                      "contentSize": g, "sha256": h, "dateModified": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(p.stat().st_mtime))})
        anzahl += 1; bytes_ += g
    (ordner / DATEI).write_text(json.dumps(
        {"@context": KONTEXT, "@graph": teile}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"RO-Crate geschrieben: {ordner/DATEI}\n  {anzahl} Dateien beschrieben · {bytes_/1e6:.2f} MB")
    return 0


def pruefen(ordner: Path) -> int:
    f = ordner / DATEI
    if not f.is_file():
        print(f"FEHLT: {f}"); return 2
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"UNGUELTIG: kein gueltiges JSON ({e})"); return 2
    if d.get("@context") != KONTEXT or not isinstance(d.get("@graph"), list):
        print("UNGUELTIG: @context oder @graph fehlt/falsch."); return 2
    kennungen = [t.get("@id") for t in d["@graph"]]
    if "./" not in kennungen or DATEI not in kennungen:
        print("UNGUELTIG: Wurzel-Dataset ('./') oder Metadaten-Datei fehlt im @graph."); return 2
    fehler, geprueft = [], 0
    for t in d["@graph"]:
        if t.get("@type") != "File":
            continue
        _z = Path(str(t["@id"]))
        # F11 (OpenCode): @id darf den Crate-Ordner nicht verlassen (nur Lesen, aber unnoetig)
        _p = (ordner / _z).resolve()
        try:
            _p.relative_to(ordner.resolve())
        except ValueError:
            fehler.append(f"UNGUELTIG: @id zeigt aus dem Ordner heraus: {t['@id']}"); continue
        p = _p
        if not p.is_file():
            if p.is_symlink() or os.path.islink(p):
                continue      # toter Verweis: meldet die Regel K8 als Warnung, kein Crate-Fehler
            fehler.append(f"FEHLT: {t['@id']}"); continue
        if hash_datei(p) != t.get("sha256"):
            fehler.append(f"GEAENDERT: {t['@id']}"); continue
        geprueft += 1
    # F7 (OpenCode): Dateien, die im Ordner liegen, aber NICHT im Crate stehen, waren unsichtbar.
    def _rein(x):
        x = str(x)
        return x[2:] if x.startswith("./") else x
    _beschrieben = {_rein(t.get("@id")) for t in d["@graph"] if t.get("@type") == "File"}
    for _eintrag in dateien(ordner):
        _datei = _eintrag[0] if isinstance(_eintrag, (tuple, list)) else _eintrag
        if not Path(_datei).is_file():
            continue          # toter Verweis/Sonderfall — nicht als "nicht beschrieben" zaehlen
        _rel = Path(_datei).relative_to(ordner).as_posix()
        if _rel not in _beschrieben:
            fehler.append(f"NICHT BESCHRIEBEN: ./{_rel}")
    if fehler:
        print(f"UNGUELTIG: {len(fehler)} Problem(e)"); [print("  " + x) for x in fehler[:10]]; return 2
    print(f"GUELTIG: {geprueft} Dateien beschrieben und nachgerechnet, alle identisch.")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--ordner", nargs="?"); ap.add_argument("--name"); ap.add_argument("--beschreibung", default="")
    ap.add_argument("--zeiger", help="Name eines Zeigers aus 40_DATEN/pointers -> Ziel wird beschrieben")
    ap.add_argument("--pruefen", nargs="?", const="", default=None)
    a = ap.parse_args()
    if a.pruefen:
        sys.exit(pruefen(Path(os.path.expanduser(a.pruefen)).resolve()))
    if a.zeiger:
        # Anschluss an einen ZEIGER: das Ziel wird aus 40_DATEN/pointers/<name>.yaml gelesen.
        p = Path(__file__).resolve().parents[2] / "40_DATEN/pointers" / f"{a.zeiger}.yaml"
        if not p.is_file():
            print(f"STOP: Zeiger '{a.zeiger}' nicht gefunden ({p})."); sys.exit(2)
        ziel = ""
        for zeile in p.read_text(encoding="utf-8").splitlines():
            if zeile.strip().startswith("ziel:"):
                ziel = zeile.split(":", 1)[1].strip(); break
        if not ziel:
            print(f"STOP: im Zeiger '{a.zeiger}' steht kein ziel."); sys.exit(2)
        if a.pruefen is not None:
            sys.exit(pruefen(Path(ziel).resolve()))
        print(f"Zeiger '{a.zeiger}' -> {ziel}")
        sys.exit(bauen(Path(ziel).resolve(), a.name or a.zeiger, a.beschreibung))
    if a.pruefen is not None:
        sys.exit(pruefen(Path(os.path.expanduser(a.pruefen or ".")).resolve()))
    if not a.ordner:
        print("Nutzung: --ordner <Ordner> | --zeiger <Name> | --pruefen <Ordner>  [--name X] [--beschreibung Y]"); sys.exit(2)
    o = Path(os.path.expanduser(a.ordner)).resolve()
    sys.exit(bauen(o, a.name or o.name, a.beschreibung))

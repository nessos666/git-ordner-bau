#!/usr/bin/env python3
"""Schnell finden und springen — Ausbau-Schritt 4 (24.09.2026).

Zwei Befehle, beide ohne neue Abhaengigkeit (gemessen: `fdfind` und `fzf` sind bereits
installiert; `rg` ebenfalls):

  dateien "muster"    Dateinamen suchen — im Baum UND in den angebundenen Bestaenden.
                      Nutzt fdfind, sonst rg, sonst find (immer ein Rueckfall da).
  springen [muster]   Auswahlliste (fzf), um direkt zu einem Projekt oder Ordner zu kommen.
                      Ohne Textauswahl (kein Terminal) wird die Liste einfach ausgegeben —
                      kein stiller Fehlschlag.

Nur LESEND. Es wird nichts geschrieben und nichts verschoben.

Aufruf:
  python3 suchen_namen.py dateien  --root <BAUM> --muster <TEXT> [--grenze 60] [--json]
  python3 suchen_namen.py springen --root <BAUM> [--muster <TEXT>] [--liste]
Exit:  0 = Treffer/Liste · 1 = nichts gefunden · 2 = nicht ausfuehrbar
"""
from __future__ import annotations
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def ziele_ohne_yaml(text: str) -> list[dict]:
    """Rueckfall, falls PyYAML fehlt: liest die einfachen 'name:'/'ziel:'-Zeilen unseres Schemas."""
    ergebnis: list[dict] = []
    name = "?"
    for zeile in text.splitlines():
        z = zeile.strip()
        if z.startswith("name:"):
            name = z.split(":", 1)[1].strip().strip('"').strip("'")
        elif z.startswith("ziel:"):
            ziel = z.split(":", 1)[1].strip().strip('"').strip("'")
            if ziel:
                ergebnis.append({"name": name, "ziel": ziel})
    return ergebnis


def zeiger_eintraege(datei) -> list[dict]:
    """Zeiger aus einer YAML-Datei — mit PyYAML, sonst mit dem eingebauten Rueckfall."""
    text = datei.read_text(encoding="utf-8")
    try:
        import yaml
        daten = yaml.safe_load(text) or {}
        if not isinstance(daten, dict):
            raise ValueError("kein Abbild")
        return list(daten.get("zeiger") or [])
    except ModuleNotFoundError:
        return ziele_ohne_yaml(text)


def suchwurzeln(root: Path) -> tuple[list[Path], list[str]]:
    """Baum + Ziele der erklaerten Zeiger. Fehlende Ziele werden GEMELDET, nicht verschwiegen."""
    wurzeln = [root]
    stoerungen: list[str] = []
    pdir = root / "40_DATEN/pointers"
    if pdir.is_dir():
        for datei in sorted(pdir.glob("*.yaml")):
            try:
                zeiger = zeiger_eintraege(datei)
            except Exception as ex:
                stoerungen.append(f"{datei.name}: UNLESBAR ({type(ex).__name__})")
                continue
            for z in zeiger:
                ziel = Path(str(z.get("ziel", "")))
                if ziel.exists():
                    if ziel not in wurzeln:
                        wurzeln.append(ziel)
                else:
                    stoerungen.append(f"{z.get('name', datei.stem)}: ZIEL FEHLT — {ziel}")
    return wurzeln, stoerungen


def dateien_finden(muster: str, wurzeln: list[Path], grenze: int) -> tuple[list[str], str, bool]:
    """Dateinamen suchen. Rueckgabe: (Treffer, benutztes Werkzeug, gekuerzt)."""
    if shutil.which("fdfind") or shutil.which("fd"):
        werkzeug = "fdfind" if shutil.which("fdfind") else "fd"
        cmd = [werkzeug, "--type", "f", "--max-results", str(grenze), muster] + [str(w) for w in wurzeln]
    elif shutil.which("rg"):
        werkzeug = "rg"
        cmd = ["rg", "--files", "--iglob", f"*{muster}*"] + [str(w) for w in wurzeln]
    else:
        werkzeug = "find"
        cmd = ["find"] + [str(w) for w in wurzeln] + ["-type", "f", "-iname", f"*{muster}*"]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, errors="replace", timeout=180)
        zeilen = [z for z in p.stdout.splitlines() if z.strip()]
    except (OSError, subprocess.TimeoutExpired):
        if werkzeug == "find":
            return [], werkzeug, False
        return dateien_finden(muster, wurzeln, grenze) if werkzeug != "rg" else ([], "rg", False)
    return zeilen[:grenze], werkzeug, len(zeilen) > grenze


def auswahl_liste(root: Path, muster: str, grenze: int) -> tuple[list[str], list[str]]:
    """Was man anspringen kann: Baum-Bereiche, Projektordner und Ziele der Zeiger."""
    kandidaten: list[str] = []
    for d in sorted((root / "20_PROJEKTE").rglob("*")) if (root / "20_PROJEKTE").is_dir() else []:
        if d.is_dir() and (not muster or muster.lower() in d.name.lower()):
            kandidaten.append(str(d))
    for d in sorted(root.iterdir()):
        if d.is_dir() and (not muster or muster.lower() in d.name.lower()):
            kandidaten.append(str(d))
    wurzeln, stoerungen = suchwurzeln(root)
    for w in wurzeln[1:]:
        if not muster or muster.lower() in w.name.lower():
            kandidaten.append(str(w))
    if muster:                                    # auch Unterordner der Ziele anspringbar machen
        for w in wurzeln[1:]:
            for d in sorted(w.rglob("*")):
                if d.is_dir() and muster.lower() in d.name.lower():
                    kandidaten.append(str(d))
    eindeutig = list(dict.fromkeys(kandidaten))[:grenze]
    return eindeutig, stoerungen


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("befehl", choices=["dateien", "springen"])
    ap.add_argument("--root", required=True)
    ap.add_argument("--muster", default="")
    ap.add_argument("--grenze", type=int, default=60)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--liste", action="store_true", help="keine Auswahl-Dialog, nur ausgeben")
    a = ap.parse_args()
    root = Path(a.root).resolve()
    if not (root / "00_SYSTEM").is_dir():
        print(f"STOP: {root} ist kein Git-Ordner-Baum."); return 2

    if a.befehl == "dateien":
        if not a.muster:
            print("Nutzung: ./ordner.sh dateien \"muster\""); return 2
        wurzeln, stoerungen = suchwurzeln(root)
        treffer, werkzeug, gekuerzt = dateien_finden(a.muster, wurzeln, a.grenze)
        if a.json:
            print(json.dumps({"muster": a.muster, "werkzeug": werkzeug, "treffer": treffer,
                              "wurzeln": len(wurzeln), "stoerungen": stoerungen,
                              "gekuerzt": gekuerzt}, ensure_ascii=False, indent=2))
        else:
            for t in treffer:
                print(t)
            print(f"\n{len(treffer)} Datei(en) mit '{a.muster}' · durchsuchte Orte: {len(wurzeln)} "
                  f"(Baum + angebundene Bestaende) · Werkzeug: {werkzeug}")
            for s in stoerungen:
                print(f"   ACHTUNG: {s}")
            if gekuerzt:
                print("   (gekuerzt: --grenze erhoehen)")
        return 0 if treffer else 1

    kandidaten, stoerungen = auswahl_liste(root, a.muster, a.grenze)
    if not kandidaten:
        print(f"nichts gefunden zu '{a.muster or 'allem'}'"); return 1
    if a.liste or not sys.stdout.isatty() or shutil.which("fzf") is None:
        for k in kandidaten:
            print(k)
        print(f"\n{len(kandidaten)} Ziel(e). Zum Auswaehlen mit Pfeiltasten: ./ordner.sh springen"
              + (f" \"{a.muster}\"" if a.muster else "") + "   (im echten Terminal)")
    else:
        p = subprocess.run(["fzf", "--prompt", "springen > "], input="\n".join(kandidaten),
                           capture_output=True, text=True)
        ziel = p.stdout.strip()
        if ziel:
            print(f"GEWAEHLT: {ziel}")
            print(f"  Ordner: {Path(ziel).parent}")
        else:
            print("Auswahl abgebrochen — nichts geaendert.")
    for s in stoerungen:
        print(f"   ACHTUNG: {s}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

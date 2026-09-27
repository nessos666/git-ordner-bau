#!/usr/bin/env python3
"""Inhaltssuche in den ZIELEN der erklaerten Zeiger — Ausbau-Schritt 5 (Stand 24.09.2026).

WAS DAS SCHLIESST: echte Projekte haengen als Zeiger am Baum — damit waren sie *auffindbar*,
aber nicht *durchsuchbar*. Dieses Werkzeug sucht IM INHALT der angebundenen Bestaende.

ZWEI WEGE, absichtlich getrennt und beide ehrlich gemeldet:
  1. TEXTDATEIEN -> ripgrep (sofort, kein Zwischenschritt)
  2. DOKUMENTE   -> PDF/DOCX/ODT/XLSX/PPTX. Der Text wird herausgeholt (pdftotext bzw.
                    libreoffice) und in `60_RUNTIME/dokumenttext/` zwischengespeichert.
                    Der Zwischenspeicher ist nach dem INHALT der Datei benannt (SHA256) —
                    eine geaenderte Datei bekommt automatisch einen neuen Eintrag, ein
                    veralteter Zwischenspeicher kann also keine falschen Treffer liefern.

Warum nicht Recoll? Recoll verlangt eine Installation mit Administrator-Passwort. Dieses
Werkzeug kommt ohne aus (pdftotext und libreoffice sind vorhanden). Recoll bleibt optional:
`50_INFRA/RECOLL_ANLEITUNG.md`.

Gegenueber den Bestaenden wird NUR gelesen. Geschrieben wird ausschliesslich der
Zwischenspeicher im Baum (`60_RUNTIME`, wird nie von Git verfolgt).

Aufruf:
    python3 finden.py --root <BAUM> --begriff <TEXT> [--grenze 40] [--ohne-dokumente] [--json]
Exit:  0 = Treffer · 1 = keine Treffer · 2 = nicht suchbar (keine Zeiger)
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

DOK_ENDUNGEN = {".pdf", ".docx", ".odt", ".doc", ".rtf", ".xlsx", ".pptx", ".epub"}
MAX_DOKUMENT_MB = 60          # groessere Dateien werden GEMELDET, nicht heimlich uebersprungen


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


def zeiger_ziele(root: Path) -> list[dict]:
    """Alle erklaerten Zeiger-Ziele aus 40_DATEN/pointers/*.yaml (mit Zustand)."""
    eintraege: list[dict] = []
    pdir = root / "40_DATEN/pointers"
    if not pdir.is_dir():
        return eintraege
    for datei in sorted(pdir.glob("*.yaml")):
        try:
            zeiger = zeiger_eintraege(datei)
        except Exception as ex:                                   # unlesbar wird GEMELDET, nicht verschwiegen
            eintraege.append({"name": datei.stem, "ziel": None, "zustand": f"UNLESBAR ({type(ex).__name__})"})
            continue
        for z in zeiger:
            ziel = str(z.get("ziel", "")).strip()
            eintraege.append({"name": z.get("name", datei.stem), "ziel": ziel,
                              "zustand": "ok" if ziel and Path(ziel).exists() else "ZIEL FEHLT"})
    return eintraege


def text_suche(begriff: str, ziel: Path, grenze: int) -> tuple[list[str], bool]:
    """Sucht im Inhalt von `ziel`. Nutzt ripgrep, sonst grep. Nur LESEND."""
    rg = shutil.which("rg")
    if rg:
        cmd = [rg, "--line-number", "--no-heading", "--color=never", "--text",
               "--glob", "!*.pdf", "--glob", "!*.docx", "--glob", "!*.odt",
               "--glob", "!*.xlsx", "--glob", "!*.pptx",
               "--max-count", str(grenze), "--max-filesize", "20M", "--", begriff, str(ziel)]
    else:
        cmd = ["grep", "-rIn", "--binary-files=without-match", "-m", str(grenze), "--", begriff, str(ziel)]
    p = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    zeilen = [z for z in p.stdout.splitlines() if z.strip()]
    return zeilen[:grenze], len(zeilen) > grenze


def dokument_text(pfad: Path, zwischenspeicher: Path) -> tuple[str | None, str]:
    """Holt den Text aus einem Dokument. Rueckgabe: (Text oder None, Zustand)."""
    try:
        kennung = hashlib.sha256()
        with pfad.open("rb") as fh:
            for brocken in iter(lambda: fh.read(1 << 20), b""):
                kennung.update(brocken)
        schluessel = kennung.hexdigest()
        groesse = pfad.stat().st_size
    except OSError as ex:
        return None, f"NICHT LESBAR ({type(ex).__name__})"
    gelagert = zwischenspeicher / f"{schluessel}.txt"
    if gelagert.exists():
        return gelagert.read_text(encoding="utf-8", errors="replace"), "aus Zwischenspeicher"
    if groesse > MAX_DOKUMENT_MB * 1024 * 1024:
        return None, f"UEBERGRENZE {MAX_DOKUMENT_MB} MB (nicht durchsucht)"
    try:
        if pfad.suffix.lower() == ".pdf":
            p = subprocess.run(["pdftotext", "-q", "-layout", str(pfad), "-"],
                               capture_output=True, text=True, errors="replace", timeout=120)
            text = p.stdout
            if p.returncode != 0 and not text.strip():
                return None, f"PDF NICHT LESBAR (pdftotext rc={p.returncode})"
        else:
            zwischenspeicher.mkdir(parents=True, exist_ok=True)
            arbeit = zwischenspeicher / f"{schluessel}.roh"
            arbeit.mkdir(exist_ok=True)
            p = subprocess.run(["soffice", "--headless", "--convert-to", "txt:Text",
                                "--outdir", str(arbeit), str(pfad)],
                               capture_output=True, text=True, errors="replace", timeout=300)
            erzeugt = list(arbeit.glob("*.txt"))
            text = erzeugt[0].read_text(encoding="utf-8", errors="replace") if erzeugt else ""
            shutil.rmtree(arbeit, ignore_errors=True)
            if not erzeugt:
                return None, f"OFFICE NICHT LESBAR (rc={p.returncode})"
    except (OSError, subprocess.TimeoutExpired) as ex:
        return None, f"NICHT LESBAR ({type(ex).__name__})"
    try:
        zwischenspeicher.mkdir(parents=True, exist_ok=True)
        gelagert.write_text(text, encoding="utf-8")
    except OSError:
        pass
    return text, "aus Datei"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--begriff", required=True)
    ap.add_argument("--grenze", type=int, default=40)
    ap.add_argument("--ohne-dokumente", action="store_true", help="nur Textdateien (schnell)")
    ap.add_argument("--max-dokumente", type=int, default=400, help="Obergrenze je Suche")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    root, begriff = Path(a.root).resolve(), a.begriff
    muster = re.compile(re.escape(begriff), re.IGNORECASE)

    ziele = zeiger_ziele(root)
    da = [z for z in ziele if z["zustand"] == "ok"]
    kaputt = [z for z in ziele if z["zustand"] != "ok"]
    if not ziele:
        print("KEINE ZEIGER ERKLAERT — nichts zu durchsuchen (40_DATEN/pointers/ ist leer).")
        return 2
    for z in kaputt:                                   # laut melden, nicht still überspringen
        print(f"  [NICHT DURCHSUCHT] {z['name']}: {z['zustand']}"
              + (f" — {z['ziel']}" if z["ziel"] else ""))

    speicher = root / "60_RUNTIME/dokumenttext"
    treffer: dict[str, list[str]] = {}
    gekuerzt = False
    dok_geprueft = dok_aus_datei = dok_aus_speicher = dok_fehler = dok_ueber = 0
    stoerungen: list[str] = []

    for z in da:
        ziel = Path(z["ziel"])
        zeilen, abgeschnitten = text_suche(begriff, ziel, a.grenze)
        if zeilen:
            treffer[z["name"]] = zeilen
        gekuerzt = gekuerzt or abgeschnitten
        if a.ohne_dokumente:
            continue
        for pfad in sorted(ziel.rglob("*")):
            if dok_geprueft >= a.max_dokumente:
                stoerungen.append(f"OBERGRENZE: nur {a.max_dokumente} Dokumente je Suche geprueft "
                                  f"(--max-dokumente erhoehen)")
                break
            if not pfad.is_file() or pfad.suffix.lower() not in DOK_ENDUNGEN:
                continue
            text, zustand = dokument_text(pfad, speicher)
            if text is None:
                if "UEBERGRENZE" in zustand:
                    dok_ueber += 1
                else:
                    dok_fehler += 1
                    stoerungen.append(f"{pfad.name}: {zustand}")
                continue
            dok_geprueft += 1
            dok_aus_datei += int(zustand == "aus Datei")
            dok_aus_speicher += int(zustand == "aus Zwischenspeicher")
            for i, zeile in enumerate(text.splitlines(), 1):
                if muster.search(zeile):
                    treffer.setdefault(z["name"], []).append(
                        f"{pfad}:{i}: {zeile.strip()[:180]}   [Dokument]")
                    break

    if a.json:
        print(json.dumps({"begriff": begriff, "durchsucht": len(da), "treffer": treffer,
                          "nicht_durchsucht": kaputt, "dokumente_geprueft": dok_geprueft,
                          "dokumente_aus_datei": dok_aus_datei, "dokumente_aus_zwischenspeicher": dok_aus_speicher,
                          "dokumente_fehler": dok_fehler, "dokumente_uebergrenze": dok_ueber,
                          "stoerungen": stoerungen, "gekuerzt": gekuerzt}, ensure_ascii=False, indent=2))
    else:
        for name, zeilen in treffer.items():
            print(f"\n{name}:")
            for z in zeilen:
                print("   " + z)
        n = sum(len(v) for v in treffer.values())
        print(f"\n{n} Treffer in {len(treffer)} von {len(da)} Zeiger(n) — nur gelesen, nichts geschrieben.")
        if not a.ohne_dokumente:
            print(f"   Dokumente: {dok_geprueft} gelesen ({dok_aus_datei} neu, {dok_aus_speicher} aus "
                  f"Zwischenspeicher) · {dok_fehler} nicht lesbar · {dok_ueber} ueber der Groessengrenze")
        for s in stoerungen[:8]:
            print(f"   ACHTUNG: {s}")
        if gekuerzt:
            print("   (gekuerzt: --grenze erhoehen)")
    return 0 if treffer else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""BagIt (RFC 8493) bauen und pruefen — Element 4 (24.09.2026).

WARUM: BagIt ist die genormte Form eines Ordnerbaums mit Pruefsummen-Manifest.
"valid" hat dort eine klare Bedeutung: JEDE Pruefsumme im Manifest wurde nachgerechnet.
Wer unsere Sicherung spaeter mit einem fremden BagIt-Werkzeug prueft, versteht sie ohne unsere Doku.

Aufbau eines Bags (Norm):   <Ziel>/bagit.txt · <Ziel>/manifest-sha256.txt · <Ziel>/bag-info.txt
                            <Ziel>/data/<die eigentliche Nutzlast>
Aufruf:
  python3 bagit_bauen.py --quelle <Ordner> --ziel <BagOrdner>     # bauen
  python3 bagit_bauen.py --pruefen <BagOrdner>                     # nachrechnen
Exit: 0 ok · 2 nicht ausfuehrbar/ungueltig
"""
from __future__ import annotations
import argparse, hashlib, os, shutil, sys, time
from pathlib import Path

AUS = {".git", "__pycache__", ".venv", "node_modules"}
BAGIT = "BagIt-Version: 0.97\nTag-File-Character-Encoding: UTF-8\n"


def hash_datei(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def nutzlast(ordner: Path):
    for dp, dns, fns in os.walk(ordner):
        dns[:] = [d for d in dns if d not in AUS]
        for f in sorted(fns):
            p = Path(dp) / f
            if p.is_file() and not p.is_symlink():
                yield p, p.relative_to(ordner).as_posix()


def bauen(quelle: Path, ziel: Path) -> int:
    if not quelle.is_dir():
        print(f"STOP: Quelle '{quelle}' fehlt."); return 2
    if ziel.exists():
        print(f"STOP: Ziel '{ziel}' existiert schon — nichts ueberschrieben."); return 2
    daten = ziel / "data"; daten.mkdir(parents=True)
    zeilen, anzahl, bytes_ = [], 0, 0
    for p, rel in nutzlast(quelle):
        t = daten / rel; t.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, t)
        zeilen.append(f"{hash_datei(t)}  data/{rel}")
        anzahl += 1; bytes_ += t.stat().st_size
    (ziel / "bagit.txt").write_text(BAGIT, encoding="utf-8")
    (ziel / "manifest-sha256.txt").write_text("\n".join(zeilen) + "\n", encoding="utf-8")
    (ziel / "bag-info.txt").write_text(
        f"Source-Organization: Git-Ordner-Baum (Git-Ordner-Bau)\nBagging-Date: {time.strftime('%Y-%m-%d')}\n"
        f"Bag-Software-Agent: bagit_bauen.py\nPayload-Oxum: {bytes_}.{anzahl}\n"
        f"Quelle: {quelle}\n", encoding="utf-8")
    # tagmanifest: Prüfsummen ueber die METADATEN des Bags (sonst koennte jemand bag-info/manifest aendern)
    tag = ["bagit.txt", "manifest-sha256.txt", "bag-info.txt"]
    (ziel / "tagmanifest-sha256.txt").write_text(
        "".join(f"{hash_datei(ziel / t)}  {t}\n" for t in tag), encoding="utf-8")
    print(f"Bag gebaut: {ziel}\n  {anzahl} Dateien · {bytes_/1e6:.2f} MB · manifest-sha256.txt mit {anzahl} Pruefsummen"
          f" · tagmanifest ueber {len(tag)} Metadatendateien")
    return 0


def pruefen(bag: Path) -> int:
    for pflicht in ("bagit.txt", "manifest-sha256.txt", "data"):
        if not (bag / pflicht).exists():
            print(f"UNGULTIG: '{pflicht}' fehlt."); return 2
    if (bag / "bagit.txt").read_text(encoding="utf-8") != BAGIT:
        print("UNGULTIG: bagit.txt hat nicht den genormten Inhalt."); return 2
    fehler, geprueft, tag_ok = [], 0, 0
    tm = bag / "tagmanifest-sha256.txt"
    if tm.is_file():
        for zeile in tm.read_text(encoding="utf-8").splitlines():
            if not zeile.strip():
                continue
            if "  " not in zeile:
                fehler.append(f"UNGULTIG: Metadatenzeile ohne Trenner: {zeile[:60]}"); continue
            soll, rel = zeile.split("  ", 1)
            p = bag / rel
            if not p.is_file():
                fehler.append(f"METADATEN FEHLEN: {rel}"); continue
            if hash_datei(p) != soll:
                fehler.append(f"METADATEN GEAENDERT: {rel}"); continue
            tag_ok += 1
    for zeile in (bag / "manifest-sha256.txt").read_text(encoding="utf-8").splitlines():
        if not zeile.strip():
            continue
        if "  " not in zeile:
            fehler.append(f"UNGULTIG: Manifestzeile ohne Trenner: {zeile[:60]}"); continue
        soll, rel = zeile.split("  ", 1)
        p = bag / rel
        if not p.is_file():
            fehler.append(f"FEHLT: {rel}"); continue
        if hash_datei(p) != soll:
            fehler.append(f"GEAENDERT: {rel}"); continue
        geprueft += 1
    # Vollstaendigkeit (Befund 7): JEDE Datei im Bag muss im Manifest stehen — sonst ist der Bag
    # nicht "complete". Und ein Bag mit Tag-Dateien ohne tagmanifest ist nicht "valid".
    _gelistet = set()
    for _z in (bag / "manifest-sha256.txt").read_text(encoding="utf-8").splitlines():
        if "  " in _z:
            _gelistet.add(_z.split("  ", 1)[1].strip())
    _tag = {"bagit.txt", "manifest-sha256.txt", "bag-info.txt", "tagmanifest-sha256.txt"}
    for _p in sorted(bag.rglob("*")):
        if not _p.is_file():
            continue
        _rel = str(_p.relative_to(bag)).replace("\\", "/")
        if _rel in _tag:
            continue
        if _rel not in _gelistet:
            fehler.append(f"NICHT GELISTET: {_rel} — Bag ist damit nicht 'complete'")
    if not tm.is_file():
        fehler.append("tagmanifest-sha256.txt FEHLT — Bag ist damit nicht 'valid'")
    # Einzige Stelle, an der ueber gueltig/ungueltig entschieden wird (nach ALLEN Pruefungen,
    # inkl. Vollstaendigkeit und tagmanifest) — 25.09.2026.
    if fehler:
        print(f"UNGULTIG: {len(fehler)} Problem(e)")
        [print("  " + f) for f in fehler[:10]]
        return 2
    print(f"VALID: {geprueft} Pruefsummen nachgerechnet, alle identisch"
          + (f" · {tag_ok} Metadatendateien mitgeprueft (tagmanifest)" if tag_ok else " (ohne tagmanifest)") + ".")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--quelle"); ap.add_argument("--ziel"); ap.add_argument("--pruefen")
    a = ap.parse_args()
    if a.pruefen:
        sys.exit(pruefen(Path(os.path.expanduser(a.pruefen)).resolve()))
    if not (a.quelle and a.ziel):
        print("Nutzung: --quelle X --ziel Y   ODER   --pruefen <Bag>"); sys.exit(2)
    sys.exit(bauen(Path(os.path.expanduser(a.quelle)).resolve(), Path(os.path.expanduser(a.ziel)).resolve()))

#!/usr/bin/env python3
"""Doppelte Dateien BERICHTEN — nur lesend, nie löschen (Element 1, 24.09.2026).

WARUM DAS IN DEN BAUM PASST: es ist ein Bericht, keine Regel. Es braucht keine neue Datenbank,
aendert K1-K8 nicht, laeuft nur auf Zuruf und schreibt nur seine eigene Liste in `60_RUNTIME`
(nie versioniert). Geloescht wird NIE automatisch — die Entscheidung bleibt beim Menschen.

DER PFAD IST PFLICHT (bewusste Empfehlung): so wird nur geprueft, was ausdruecklich gewuenscht
ist — nie „aus Versehen" der ganze Rechner.

DREI FALLEN, DIE DIE ZAHL VERFAELSCHEN — hier vermieden:
 1. HARDLINKS: zwei Namen, EINE Datei auf der Platte. Sie belegen den Speicher nur EINMAL,
    sind also KEINE Dubletten. Sie werden getrennt gezaehlt (extra_bytes = 0).
 2. ZWEISTUFIG: erst die ersten 64 KB vergleichen, nur bei Gleichstand die ganze Datei lesen.
    Sonst liest ein Lauf ueber 300 GB alles komplett.
 3. UNLESBARES wird GEMELDET, nicht verschwiegen.

Aufruf:
    python3 doppelte.py --pfad <ORDNER> [--ab-groesse KB] [--max-dateien N] [--json]
Exit:  0 = Dubletten gefunden · 1 = keine gefunden · 2 = nicht ausfuehrbar
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

AUSSCHLUSS = {".git", "node_modules", "__pycache__", ".venv", ".cache", "snap", ".mypy_cache", ".pytest_cache"}
KOPF_BYTES = 64 * 1024
# Pfade, die man GEF A HRLOS neu erzeugen kann (venv/node_modules): gleiche Bytes, aber kein Datenverlust
WIEDERHERSTELLBAR = re.compile(r"/(venv|\.venv|node_modules|site-packages|__pypackages__|\.tox)/", re.I)


def kopf_hash(pfad: str, groesse: int) -> str | None:
    """Erste 64 KB (oder die ganze Datei, wenn kleiner)."""
    try:
        with open(pfad, "rb") as fh:
            brocken = fh.read(min(KOPF_BYTES, groesse))
        return hashlib.blake2b(brocken, digest_size=16).hexdigest()
    except OSError:
        return None


def voll_hash(pfad: str) -> str | None:
    try:
        h = hashlib.blake2b(digest_size=16)
        with open(pfad, "rb") as fh:
            for brocken in iter(lambda: fh.read(1 << 20), b""):
                h.update(brocken)
        return h.hexdigest()
    except OSError:
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pfad", required=True, help="Ordner, der geprueft wird (Pflicht)")
    ap.add_argument("--ab-groesse", type=int, default=1, help="Mindestgroesse in KB (Standard 1)")
    ap.add_argument("--max-dateien", type=int, default=400000, help="Obergrenze (Schutz vor Extremfaellen)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--root", default="", help="Baum-Wurzel fuer den Bericht (Standard: keine Ablage)")
    a = ap.parse_args()

    pfad = Path(os.path.expanduser(a.pfad)).resolve()
    if not pfad.is_dir():
        print(f"STOP: '{pfad}' ist kein Ordner."); return 2
    mindest = max(0, a.ab_groesse) * 1024
    t0 = time.time()

    # ---- 1) sammeln (nur Metadaten, schnell) ----
    nach_groesse: dict[int, list[tuple[str, int, int]]] = {}
    dateien = klein = 0
    bytes_gesamt = 0
    kopf_budget_aus = False
    for dp, dns, fns in os.walk(pfad, onerror=lambda ex: print(f"  ACHTUNG: Bereich nicht lesbar — {ex}", file=sys.stderr)):
        dns[:] = [d for d in dns if d not in AUSSCHLUSS]
        for f in fns:
            p = os.path.join(dp, f)
            try:
                st = os.lstat(p)
            except OSError:
                continue
            if not os.path.isfile(p) or os.path.islink(p):
                continue
            dateien += 1
            if dateien > a.max_dateien:
                print(f"STOP: mehr als {a.max_dateien} Dateien — Bitte Bereich einschraenken.")
                return 2
            bytes_gesamt += st.st_size
            if st.st_size < mindest:
                klein += 1
                continue
            nach_groesse.setdefault(st.st_size, []).append((p, st.st_ino, st.st_dev))
    t1 = time.time()

    # ---- 2) Kopf-Hash nur fuer gleich grosse Dateien, dann Voll-Hash bei Gleichstand ----
    gruppen: list[dict] = []
    geprueft = 0
    unlesbar: list[str] = []
    for groesse, eintraege in nach_groesse.items():
        if len(eintraege) < 2:
            continue
        nach_kopf: dict[str, list[tuple[str, int, int]]] = {}
        for p, ino, dev in eintraege:
            h = kopf_hash(p, groesse)
            if h is None:
                unlesbar.append(p)
                continue
            nach_kopf.setdefault(h, []).append((p, ino, dev))
        for kandidaten in nach_kopf.values():
            if len(kandidaten) < 2:
                continue
            nach_voll: dict[str, list[tuple[str, int, int]]] = {}
            for p, ino, dev in kandidaten:
                h = voll_hash(p)
                geprueft += 1
                if h is None:
                    unlesbar.append(p)
                    continue
                nach_voll.setdefault(h, []).append((p, ino, dev))
            for inhaltsgleiche in nach_voll.values():
                if len(inhaltsgleiche) < 2:
                    continue
                inodes = {(ino, dev) for _, ino, dev in inhaltsgleiche}
                hardlink_gruppe = len(inodes) < len(inhaltsgleiche)
                # Extra-Speicher: jede WEITERE Datei mit EIGENEM Inode belegt Platz.
                extra = groesse * (len(inodes) - 1)
                pfade = [p for p, _, _ in inhaltsgleiche]
                gruppen.append({"groesse": groesse, "dateien": pfade,
                                "anzahl_pfade": len(inhaltsgleiche), "anzahl_inodes": len(inodes),
                                "hardlinks": hardlink_gruppe, "extra_bytes": extra,
                                "wiederherstellbar": all(WIEDERHERSTELLBAR.search(p) for p in pfade)})
    t2 = time.time()

    gruppen.sort(key=lambda g: -g["extra_bytes"])
    extra_gesamt = sum(g["extra_bytes"] for g in gruppen)
    doppelte_dateien = sum(g["anzahl_inodes"] - 1 for g in gruppen)
    hardlink_gruppen = sum(1 for g in gruppen if g["hardlinks"])
    wieder_bytes = sum(g["extra_bytes"] for g in gruppen if g["wiederherstellbar"])
    wieder_gruppen = sum(1 for g in gruppen if g["wiederherstellbar"])

    bericht = {
        "bereich": str(pfad),
        "ab_groesse_kb": a.ab_groesse,
        "dateien_gesamt": dateien,
        "dateien_kleiner_als_schwelle": klein,
        "bytes_gesamt": bytes_gesamt,
        "doppelgruppen": len(gruppen),
        "doppelte_dateien": doppelte_dateien,
        "hardlink_gruppen": hardlink_gruppen,
        "wiederherstellbar_gruppen": wieder_gruppen,
        "wiederherstellbar_bytes": wieder_bytes,
        "extra_bytes": extra_gesamt,
        "dauer_s": round(t2 - t0, 2),
        "dauer_gruppierung_s": round(t1 - t0, 2),
        "unlesbar": unlesbar[:20],
        "unlesbar_anzahl": len(unlesbar),
        "gruppen": gruppen[:200],
    }

    if a.root:
        ablage = Path(a.root) / "60_RUNTIME/doppelt"
        ablage.mkdir(parents=True, exist_ok=True)
        slug = re.sub(r"[^a-z0-9]+", "_", str(pfad).lower()).strip("_")[:60]
        ziel = ablage / f"{time.strftime('%Y-%m-%d')}_{slug}.json"
        ziel.write_text(json.dumps(bericht, ensure_ascii=False, indent=1), encoding="utf-8")
        bericht["bericht_datei"] = str(ziel)

    if a.json:
        print(json.dumps(bericht, ensure_ascii=False, indent=2))
    else:
        print(f"Bereich: {pfad}")
        print(f"  {dateien} Dateien · {bytes_gesamt/1e9:.2f} GB · Gruppierung in {bericht['dauer_gruppierung_s']} s, "
              f"Pruefung in {bericht['dauer_s']} s")
        print(f"  kleiner als {a.ab_groesse} KB und uebersprungen: {klein} Dateien")
        print(f"  DOPPELTE DATEIEN: {doppelte_dateien} in {len(gruppen)} Gruppen · "
              f"belegter Extra-Speicher: {extra_gesamt/1e9:.3f} GB")
        if hardlink_gruppen:
            print(f"  davon {hardlink_gruppen} Gruppe(n) mit HARDLINKS — dieselbe Datei, kein echter Mehrverbrauch")
        if wieder_gruppen:
            print(f"  DAVON WIEDERHERSTELLBAR (venv/node_modules): {wieder_gruppen} Gruppen = "
                  f"{wieder_bytes/1e9:.3f} GB — neu erzeugbar, dabei geht KEIN Datenverlust verloren")
        for g in gruppen[:10]:
            print(f"\n  {g['groesse']/1024:.0f} KB × {g['anzahl_pfade']} "
                  f"({'Hardlink' if g['hardlinks'] else 'getrennte Dateien'}, extra {g['extra_bytes']/1024:.0f} KB):")
            for p in g["dateien"][:4]:
                print(f"     {p}")
            if g["anzahl_pfade"] > 4:
                print(f"     … {g['anzahl_pfade']-4} weitere")
        if unlesbar:
            print(f"\n  ACHTUNG: {len(unlesbar)} Datei(en) NICHT LESBAR (nicht mitgezaehlt):")
            for p in unlesbar[:5]:
                print(f"     {p}")
        if bericht.get("bericht_datei"):
            print(f"\n  Bericht: {bericht['bericht_datei']}  (60_RUNTIME — nie in Git)")
        print("  NICHTS geloescht, nichts verschoben — nur berichtet.")
    return 0 if gruppen else 1


if __name__ == "__main__":
    sys.exit(main())

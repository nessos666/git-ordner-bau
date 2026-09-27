#!/usr/bin/env python3
"""Budget-Pruefung 40_DATEN (v1.3: Katalog/Zeiger/Manifest — KEIN Datenlager).
Grenze hart aus v1.3: 40_DATEN < 1 MB. Meldet nur, loescht nie.

Nachgezogen (RT-C Befunde):
 * 40_DATEN muss ein VERZEICHNIS sein — als 5-MB-Datei meldete die Pruefung vorher 0 B/PASS.
 * Symlinks werden KETTENAUFLOESEND gezaehlt (auch Ziel enthaelt interne Verzeichnis-Symlinks):
   vorher waren 5 MB erreichbar, waehrend das Budget 1234 B/PASS sagte.
"""
from __future__ import annotations
import json, os, sys
from pathlib import Path

GRENZE = 1 << 20          # 1 MB — exakt die v1.3-Vorgabe


def _groesse(p: Path, tiefe=0):
    """Groesse eines Pfades, Symlink-Ketten aufgeloest, Verzeichnisse rekursiv."""
    if tiefe > 32: return 0
    try:
        r = Path(os.path.realpath(p))
        if r.is_dir(): return sum(_groesse(x, tiefe + 1) for x in r.rglob("*") if not x.is_dir())
        if r.is_file(): return r.stat().st_size
    except OSError:
        return 0
    return 0


def pruefe(root: Path):
    """Rueckgabe: dict mit status/fehler/werten — 'fehler' ist eine Liste lesbarer Meldungen."""
    d = Path(root) / "40_DATEN"
    fehler = []
    if not d.exists():
        return {"status": "FAIL", "fehler": ["40_DATEN fehlt."], "groesse_b": 0, "grenze_b": GRENZE}
    if not d.is_dir():
        g = d.stat().st_size
        return {"status": "FAIL", "fehler": [f"40_DATEN ist ein VERZEICHNIS nicht — sondern eine Datei "
                                             f"({g} B). Inhalt wird nicht geprueft: {d}"],
                "groesse_b": g, "grenze_b": GRENZE, "art": "datei"}
    dateien, symlinks, gesehen, gesamt = [], [], set(), 0
    for dp, dns, fns in os.walk(d, followlinks=False):
        for n in list(dns) + list(fns):
            q = Path(dp) / n
            if not (q.is_symlink() or q.is_dir()):
                continue
            if q.is_symlink():
                ziel = os.path.realpath(q)
                if ziel in gesehen: continue
                gesehen.add(ziel)
                g = _groesse(q)
                gesamt += g; symlinks.append({"b": g, "pfad": str(q.relative_to(root)), "ziel": ziel})
    if not symlinks:
        for dp, dns, fns in os.walk(d, followlinks=False):
            for n in fns:
                q = Path(dp) / n
                try: g = q.stat().st_size
                except OSError: continue
                gesamt += g; dateien.append((g, str(q.relative_to(root))))
    else:
        for dp, dns, fns in os.walk(d, followlinks=False):
            for n in fns:
                q = Path(dp) / n
                if q.is_symlink(): continue
                try: g = q.stat().st_size
                except OSError: continue
                gesamt += g; dateien.append((g, str(q.relative_to(root))))
    dateien.sort(reverse=True)
    if symlinks:
        fehler.append(f"{len(symlinks)} Symlink(s) in 40_DATEN — Ziel wird MITGEZAEHLT (Kettenantwort): "
                      + ", ".join(f"{s['pfad']} -> {s['b']} B" for s in symlinks[:3]))
    if gesamt >= GRENZE:
        fehler.append(f"40_DATEN-Budget ueberschritten: {gesamt} B >= {GRENZE} B.")
    return {"symlinks": symlinks, "status": "PASS" if gesamt < GRENZE else "FAIL",
            "fehler": fehler, "grenze_b": GRENZE, "groesse_b": gesamt,
            "auslastung_pct": round(100 * gesamt / GRENZE, 2),
            "anzahl_dateien": len(dateien), "groesste": dateien[:5], "reserve_b": GRENZE - gesamt}


if __name__ == "__main__":
    root = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[2])
    r = pruefe(Path(root).expanduser().resolve())
    print(json.dumps(r, ensure_ascii=False, indent=2))
    sys.exit(0 if r["status"] == "PASS" else 1)

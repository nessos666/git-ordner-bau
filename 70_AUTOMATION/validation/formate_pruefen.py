#!/usr/bin/env python3
"""Formate und Dateinamen pruefen — Erweiterung (24.09.2026).

Pruefsummen sichern BITS, nicht VERSTEHBARKEIT. Dieses Werkzeug markiert:
  * Dateitypen je Bereich (mit dem vorhandenen 'file')
  * risikoreiche Typen (unbekannt/binär/austauschbar) -> HINWEIS, kein Urteil
  * Dateinamen mit Leerzeichen/Sonderzeichen -> HINWEIS (RFC 8493 warnt vor Namensproblemen)
Es verurteilt nichts und aendert nichts. Exit: 0 keine Auffaelligkeit · 1 Auffaelligkeit.
"""
from __future__ import annotations
import collections, os, re, subprocess, sys
from pathlib import Path

AUS = {".git", "60_RUNTIME", "__pycache__"}
RISIKO = {"application/octet-stream", "application/x-dosexec", "application/x-executable",
          "application/x-sharedlib", "inode/x-empty"}
NAME_OK = re.compile(r"^[A-Za-z0-9._-]+$")


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("--ordner", required=True); ap.add_argument("--still", action="store_true")
    a = ap.parse_args()
    wurzel = Path(os.path.expanduser(a.ordner)).resolve()
    typen, risiko, namen, dateien = collections.Counter(), [], [], 0
    for dp, dns, fns in os.walk(wurzel):
        dns[:] = [d for d in dns if d not in AUS]
        for f in sorted(fns):
            p = Path(dp) / f
            if not p.is_file() or p.is_symlink():
                continue
            dateien += 1
            try:
                t = subprocess.run(["file", "-b", "--mime-type", str(p)], capture_output=True, text=True, timeout=20).stdout.strip()
            except Exception:
                t = "unbekannt"
            typen[t or "unbekannt"] += 1
            if t in RISIKO:
                risiko.append(f"{p.relative_to(wurzel)} ({t})")
            if not NAME_OK.match(f):
                namen.append(str(p.relative_to(wurzel)))
    if not a.still:
        print(f"Formate: {dateien} Dateien geprueft\n  haeufigste Typen:")
        for t, n in typen.most_common(8):
            print(f"    {n:5}  {t}")
        if risiko:
            print(f"  HINWEIS {len(risiko)} Datei(en) mit risikoreichem Typ (nicht automatisch falsch):")
            for x in risiko[:10]:
                print("    -", x)
        if namen:
            print(f"  HINWEIS {len(namen)} Datei(en) mit Leerzeichen/Sonderzeichen im Namen:")
            for x in namen[:10]:
                print("    -", x)
        print("  Nichts geaendert, nichts verurteilt — nur markiert.")
    return 1 if (risiko or namen) else 0


if __name__ == "__main__":
    sys.exit(main())

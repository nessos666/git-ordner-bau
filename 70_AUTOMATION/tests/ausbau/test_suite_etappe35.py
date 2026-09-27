#!/usr/bin/env python3
"""ETAPPE 3.5 — Doppelte Dateien BERICHTEN (Element 1, 24.09.2026).

Fuenf Tests. Vier davon pruefen, dass die ZAHL stimmt — und einer, dass die groesste Falle
der Doppelten-Suche vermieden wird: ein HARDLINK ist KEINE Dublette (dieselbe Datei, zweimal
benannt), sonst behauptet der Bericht Ersparnis, die es laengst gibt.

i1 echte Dublette wird gefunden (Extra-Speicher stimmt) · i2 Hardlink wird als Hardlink erkannt
(Extra 0) · i3 nichts doppelt -> klare Nullmeldung · i4 Unlesbares wird GEMELDET ·
i5 fehlender Pfad -> STOP (nichts passiert)
"""
from __future__ import annotations
import json
import os
import shlex
import subprocess
import unittest
from pathlib import Path

M = next(p for p in Path(__file__).resolve().parents if (p / "ordner.sh").is_file())
WERK = M / "70_AUTOMATION/pointers/doppelte.py"
B = M.parent / "tmp35"
ENV = {"PATH": "/usr/bin:/bin:/usr/local/bin", "HOME": str(Path.home()), "LANG": "C.UTF-8",
       "GIT_CONFIG_NOSYSTEM": "1", "GIT_OPTIONAL_LOCKS": "0"}


def aufraeumen(z):
    z = Path(z).resolve(); b = B.resolve(); sb = M.parent
    if not b.name.startswith("tmp") or sb not in b.parents:
        raise RuntimeError(f"TESTWIESE UNPLAUSIBEL: {b}")
    if z != b and b not in z.parents:
        raise RuntimeError(f"LOESCHEN VERWEIGERT: {z} liegt nicht unter {b}")
    subprocess.run(["bash", "-lc", f"chmod -R u+rwX {shlex.quote(str(z))} 2>/dev/null; rm -rf {shlex.quote(str(z))}"],
                   capture_output=True)


def lauf(ziel: Path, *extra: str):
    p = subprocess.run(["python3", "-B", str(WERK), "--pfad", str(ziel), "--json", *extra],
                       capture_output=True, text=True, errors="replace", env=ENV)
    try:
        daten = json.loads(p.stdout)
    except Exception:
        daten = None
    return p, daten


class I_DoppelteDateien(unittest.TestCase):

    def test_i1_echte_dublette_wird_gefunden(self):
        t = B / "i1"; t.mkdir(parents=True, exist_ok=True)
        inhalt = b"X" * 500000
        (t / "a.dat").write_bytes(inhalt)
        (t / "b.dat").write_bytes(inhalt)
        (t / "anders.dat").write_bytes(b"Y" * 500000)
        p, d = lauf(t)
        self.assertEqual(p.returncode, 0, p.stdout[-300:])
        self.assertEqual(d["doppelgruppen"], 1)
        self.assertEqual(d["doppelte_dateien"], 1)
        self.assertGreater(d["extra_bytes"], 400000)      # rund eine Datei geht verloren
        self.assertEqual(d["hardlink_gruppen"], 0)

    def test_i2_hardlink_ist_keine_dublette(self):
        t = B / "i2"; t.mkdir(parents=True, exist_ok=True)
        a = t / "original.dat"; a.write_bytes(b"Z" * 300000)
        os.link(a, t / "zweiter_name.dat")                # dieselbe Datei auf der Platte
        p, d = lauf(t)
        self.assertEqual(p.returncode, 0, p.stdout[-300:])
        self.assertEqual(d["hardlink_gruppen"], 1, "Hardlink muss als Hardlink erkannt werden")
        self.assertEqual(d["extra_bytes"], 0, "Hardlink belegt KEINEN Extra-Speicher")
        self.assertEqual(d["doppelte_dateien"], 0)

    def test_i3_ohne_dubletten_klare_nullmeldung(self):
        t = B / "i3"; t.mkdir(parents=True, exist_ok=True)
        (t / "eins.dat").write_bytes(b"1" * 200000)
        (t / "zwei.dat").write_bytes(b"2" * 210000)
        p, d = lauf(t)
        self.assertEqual(p.returncode, 1)
        self.assertEqual(d["doppelgruppen"], 0)
        self.assertIn("DOPPELTE DATEIEN: 0", subprocess.run(
            ["python3", "-B", str(WERK), "--pfad", str(t)], capture_output=True, text=True).stdout)

    def test_i4_unlesbares_wird_gemeldet(self):
        t = B / "i4"; t.mkdir(parents=True, exist_ok=True)
        for name in ("gesperrt_a.dat", "gesperrt_b.dat"):
            f = t / name; f.write_bytes(b"G" * 100000); f.chmod(0o000)
        p, d = lauf(t)
        self.assertEqual(d["unlesbar_anzahl"], 2, f"unlesbar_anzahl={d.get('unlesbar_anzahl')}")
        self.assertGreater(len(d["unlesbar"]), 0)

    def test_i5_fehlender_pfad_stoppt(self):
        p, _ = lauf(B / "gibt_es_nicht_xyz")
        self.assertEqual(p.returncode, 2)
        self.assertIn("STOP", p.stdout)


class J_Wiederherstellbar(unittest.TestCase):
    """venv/node_modules sind neu erzeugbar — der Bericht muss das GETRENNT ausweisen."""

    def test_i6_venv_dubletten_werden_als_wiederherstellbar_gemeldet(self):
        t = B / "i6" / "projekt" / "venv" / "lib" / "site-packages"; t.mkdir(parents=True, exist_ok=True)
        for i in (1, 2):
            (t / f"kopie{i}.so").write_bytes(b"V" * 400000)
        p, d = lauf(B / "i6")
        self.assertEqual(p.returncode, 0, p.stdout[-300:])
        self.assertEqual(d["wiederherstellbar_gruppen"], 1)
        self.assertGreater(d["wiederherstellbar_bytes"], 300000)


if __name__ == "__main__":
    B.mkdir(parents=True, exist_ok=True)
    try:
        unittest.main(verbosity=2)
    finally:
        if B.exists():
            aufraeumen(B)

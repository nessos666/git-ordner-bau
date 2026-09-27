#!/usr/bin/env python3
"""ETAPPE 3.7 — Rollentrennung, Stichprobe, Zeiger-Crate, Sicherung mit Bag (24.09.2026).

t1 die Messung existiert und sagt VERIFIZIERT
t2 EHRLICHKEIT: ohne Messdatei sagt die Pruefzeile "NICHT VERIFIZIERT" (kein erfundenes OK)
t3 der 50-MB-Zeiger wird per STICHPROBE geprueft und sagt den Rest ehrlich "ungeprueft"
t4 der Crate des angebundenen Bestands ist gueltig (Zeiger -> Selbstbeschreibung)
t5 die Sicherung erzeugt mit --bag eine normgerechte BagIt-Ablage, die sich pruefen laesst
"""
from __future__ import annotations
import shlex, shutil, subprocess, unittest
from pathlib import Path

M = next(p for p in Path(__file__).resolve().parents if (p / "ordner.sh").is_file())
B = M.parent / "tmp37"
PY = "python3"


def lauf(befehl: str, zeit: int = 900):
    return subprocess.run(["bash", "-lc", befehl], capture_output=True, text=True, errors="replace", timeout=zeit)


class Rollen(unittest.TestCase):
    def test_t1_messung_sagt_verifiziert(self):
        f = M / "50_INFRA/rollentrennung.yaml"
        self.assertTrue(f.is_file(), "Messdatei fehlt")
        txt = f.read_text(encoding="utf-8")
        self.assertIn("verdict: VERIFIZIERT", txt)
        self.assertIn("anzahl_aenderungen: 0", txt)
        # Schaerfung (27.09.2026): Vorher genuegte das Wort VERIFIZIERT — eine Messung eines
        # FREMDEN Baums haette den Test ebenfalls bestanden. Jetzt muss sie diesen Baum nennen.
        self.assertIn(str(M), txt,
                      "die Messung nennt DIESEN Baum nicht — sie koennte von einem anderen stammen")

    def test_t2_ohne_messung_kein_erfundenes_ok(self):
        f = M / "50_INFRA/rollentrennung.yaml"; weg = f.with_suffix(".weg")
        f.rename(weg)
        try:
            p = lauf(f"{PY} -B {M}/70_AUTOMATION/validation/check_all.py --root {M}")
            self.assertIn("ROLLENTRENNUNG: NICHT VERIFIZIERT", p.stdout + p.stderr)
        finally:
            weg.rename(f)
        p2 = lauf(f"{PY} -B {M}/70_AUTOMATION/validation/check_all.py --root {M}")
        self.assertIn("ROLLENTRENNUNG: VERIFIZIERT", p2.stdout + p2.stderr)

    def test_t3_stichprobe_statt_gar_nichts(self):
        p = lauf(f"{PY} -B {M}/70_AUTOMATION/validation/check_all.py --root {M}")
        aus = p.stdout + p.stderr
        self.assertIn("rollierend", aus, "rollierende Pruefung fehlt")
        self.assertIn("naechster Lauf ab Eintrag", aus, "Fortsetzungsstelle fehlt")
        self.assertIn("Rest gilt als UNGEPRUEFT", aus, "ehrlicher Hinweis fehlt")

    def test_t4_zeiger_crate_ist_gueltig(self):
        p = lauf(f"{PY} -B {M}/70_AUTOMATION/crate/ro_crate.py --zeiger 47_Island_Sprache --pruefen")
        self.assertEqual(p.returncode, 0, p.stdout[-300:] + p.stderr[-300:])
        self.assertIn("GUELTIG", p.stdout)


class Sicherung(unittest.TestCase):
    def test_t5_kopie_mit_bag_ist_normgerecht(self):
        z = B / "kopie"
        p = lauf(f"bash {M}/sicherung.sh kopie {z} --bag", 900)
        self.assertEqual(p.returncode, 0, p.stdout[-400:])
        self.assertTrue((z / "bag/bagit.txt").is_file(), "bagit.txt fehlt")
        q = lauf(f"{PY} -B {M}/70_AUTOMATION/bagit/bagit_bauen.py --pruefen {z}/bag")
        self.assertEqual(q.returncode, 0, q.stdout[-300:])
        self.assertIn("VALID", q.stdout)


if __name__ == "__main__":
    B.mkdir(parents=True, exist_ok=True)
    try:
        unittest.main(verbosity=2)
    finally:
        if B.exists():
            subprocess.run(["bash", "-lc", f"rm -rf {shlex.quote(str(B))}"])

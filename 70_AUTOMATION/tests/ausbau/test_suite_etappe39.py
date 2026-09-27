#!/usr/bin/env python3
"""ETAPPE 3.9 — spross.sh unter Aufsicht (25.09.2026, Befund eines unabhaengigen Pruefers).

Der Befund war: spross committete die Pruefsummenliste des ELTERN-Baums (Liste erst NACH `git add -A`
erzeugt), wodurch jeder neue Baum sofort "schmutzig" war und ein Klon 15 Pruefsummen-Fehler zeigte.
Die neue Automatik war durch KEINEN Test gedeckt. Das holt diese Suite nach:
  s1 nach dem Anlegen ist der neue Baum sauber (git status --porcelain leer)
  s2 die Pruefsummenliste im Commit passt zum Arbeitsbaum und ein KLON prueft fehlerfrei
  s3 ein zweiter Lauf auf ein vorhandenes Ziel bricht ab (nichts ueberschrieben)
  s4 der neue Baum kann sich selbst pruefen (Selbsttest nicht DEFEKT)
"""
from __future__ import annotations
import shutil, subprocess, unittest
from pathlib import Path

BAUM = next(p for p in Path(__file__).resolve().parents if (p / "ordner.sh").is_file())
B = BAUM.parent / "tmp39"


def r(cmd: str, cwd=None, zeit: int = 900):
    return subprocess.run(["bash", "-lc", cmd], cwd=cwd, capture_output=True, text=True, errors="replace", timeout=zeit)


class Spross(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Punkt 8 (Fremdpruefung 27.09.2026): die EIGENE Testwiese zuerst leeren.
        # Vorher brach die Suite ab, wenn ein Lauf vorher abgebrochen war
        # ('existiert schon — nichts ueberschrieben'), und der Ordner blieb liegen.
        import shutil as _sh
        _wiese = BAUM.parent / "tmp39"
        if _wiese.is_dir():
            _sh.rmtree(_wiese)
        B.mkdir(parents=True, exist_ok=True)
        cls.ziel = B / "Neu"

    def test_s1_neuer_baum_ist_sauber(self):
        p = r(f"bash {BAUM}/spross.sh {self.ziel} Probe", cwd=BAUM)
        self.assertEqual(p.returncode, 0, p.stdout[-300:])
        st = r(f"git -C {self.ziel} status --porcelain").stdout.strip()
        self.assertEqual(st, "", f"neuer Baum nicht sauber: {st!r}")

    def test_s2_klon_prueft_fehlerfrei(self):
        k = B / "klon"
        if k.exists():
            shutil.rmtree(k)
        self.assertEqual(r(f"git clone -q {self.ziel} {k}").returncode, 0)
        p = r("sha256sum -c PRUEFSUMMEN_MASTER.txt", cwd=k)
        self.assertEqual(p.returncode, 0, p.stdout[-300:])
        self.assertNotIn("GESCHEITERT", p.stdout)

    def test_s3_zweiter_lauf_bricht_ab(self):
        p = r(f"bash {BAUM}/spross.sh {self.ziel} Probe", cwd=BAUM)
        self.assertEqual(p.returncode, 2)
        self.assertIn("existiert schon", p.stdout)

    def test_s4_neuer_baum_prueft_sich_selbst(self):
        p = r("./ordner.sh pruefen", cwd=self.ziel, zeit=900)
        self.assertNotIn("Selbsttest: DEFEKT", p.stdout + p.stderr, p.stdout[-400:])
        self.assertNotIn("STATUS: CRITICAL", p.stdout)


if __name__ == "__main__":
    B.mkdir(parents=True, exist_ok=True)
    try:
        unittest.main(verbosity=2)
    finally:
        if B.exists():
            shutil.rmtree(B, ignore_errors=True)

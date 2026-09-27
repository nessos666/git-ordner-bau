#!/usr/bin/env python3
"""ETAPPE 3.1 — Redundanz wird GEMESSEN (Ausbau-Schritt 2, 23.09.2026).

Vorher stand in jeder Pruefzeile `REDUNDANZ: FEHLT`, weil die Funktion nur einen fest
verdrahteten Ort neben dem Baum kannte. Jetzt gelten die in `50_INFRA/redundanz.yaml`
ERKLAERTEN Kopien, und jede wird dreifach gemessen: existiert sie? ist sie AKTUELL
(Pruefsummenliste identisch)? liegt sie auf einem ANDEREN Geraet?

Die drei Tests sind die drei Wahrheiten: aktuell · veraltet · fehlt.
"""
from __future__ import annotations
import shlex
import shutil
import subprocess
import unittest
from pathlib import Path

M = next(p for p in Path(__file__).resolve().parents if (p / "ordner.sh").is_file())
CHK = M / "70_AUTOMATION/validation/check_all.py"
B = M.parent / "tmp31"
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


def kopie(name: str) -> Path:
    z = B / name
    if z.exists():
        aufraeumen(z)
    shutil.copytree(M, z)
    subprocess.run(["git", "-C", str(z), "add", "-A"], capture_output=True, env=ENV)
    subprocess.run(["git", "-C", str(z), "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-q", "-m", "Testkopie"], capture_output=True, env=ENV)
    return z


def pruefe(root: Path):
    return subprocess.run(["python3", "-B", str(CHK), "--root", str(root), "--no-selftest"],
                          capture_output=True, text=True, errors="replace", env=ENV)


class E_Redundanz(unittest.TestCase):

    def _mit_kopie(self, name: str, kopie_pfad: str | None = None):
        """Baut eine echte zweite Kopie NEBEN der Testwiese (nicht im Baum!) und erklaert sie."""
        t = kopie(name)
        ziel = B / f"{name}_kopie"
        if ziel.exists():
            aufraeumen(ziel)
        p = subprocess.run(["bash", str(t / "sicherung.sh"), "kopie", str(ziel)],
                           capture_output=True, text=True, errors="replace", env=ENV)
        self.assertEqual(p.returncode, 0, (p.stdout + p.stderr)[-300:])
        (t / "50_INFRA/redundanz.yaml").write_text(
            "schema_version: 1\nkopien:\n  - pfad: " + (kopie_pfad or str(ziel)) + "\n", encoding="utf-8")
        return t, ziel

    def test_e1_aktuelle_kopie_wird_erkannt_und_als_gleiche_platte_benannt(self):
        t, ziel = self._mit_kopie("e1")
        r = pruefe(t); aus = r.stdout + r.stderr
        self.assertIn("Kopie(n), aktuell", aus, aus[-500:])
        self.assertIn("GLEICHE PLATTE", aus, "Gleiche Platte muss ehrlich benannt werden (P0)")

    def test_e2_veraltete_kopie_wird_erkannt(self):
        t, ziel = self._mit_kopie("e2")
        # "veraltet" heisst: die Kopie haelt einen ANDEREN Quellstand fest als der Baum heute hat.
        (ziel / "README.txt").write_text("ZEIT=x\nQUELLSTAND=0000000000000000000000000000000000000000000000000000000000000000\n",
 encoding="utf-8")
        r = pruefe(t); aus = r.stdout + r.stderr
        self.assertIn("VERALTET", aus, aus[-500:])

    def test_e3_fehlende_kopie_wird_erkannt(self):
        t, ziel = self._mit_kopie("e3", kopie_pfad=str(B / "gibt_es_nicht_xyz"))
        r = pruefe(t); aus = r.stdout + r.stderr
        self.assertIn("FEHLT (keine der erklaerten Kopien", aus, aus[-500:])


if __name__ == "__main__":
    B.mkdir(parents=True, exist_ok=True)
    try:
        unittest.main(verbosity=2)
    finally:
        if B.exists():
            aufraeumen(B)

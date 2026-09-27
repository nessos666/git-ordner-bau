#!/usr/bin/env python3
"""ETAPPE 3.3 — Feste Projekt-Nummern (Ausbau-Schritt 3, 23.09.2026).

Die Nummer ist die Kennung, der Name ist die Beschriftung:
    021_island_sprache_2026-09-23   ->   021_island_2026-10-01    (Name aendert sich, Pfad bleibt)

Fuenf Tests: Anlegen (Nummer 001) · naechste Nummer (002) · Doppelvergabe = FEHLER ·
Nummer nicht dreistellig = HINWEIS · unerlaubter Name wird abgewiesen (nichts angelegt).
Der Baum muss nach dem Anlegen WEITER gruen sein — das ist der eigentliche Beweis.
"""
from __future__ import annotations
import shlex
import shutil
import subprocess
import unittest
from pathlib import Path

M = next(p for p in Path(__file__).resolve().parents if (p / "ordner.sh").is_file())
NEU = M / "70_AUTOMATION/projects/neues_projekt.py"
CHK = M / "70_AUTOMATION/validation/check_all.py"
B = M.parent / "tmp33"
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


def anlegen(root: Path, name: str, bereich: str = "standalone", datum: str = "2026-09-23"):
    p = subprocess.run(["python3", "-B", str(NEU), "--root", str(root), "--name", name,
                        "--bereich", bereich, "--datum", datum],
                       capture_output=True, text=True, errors="replace", env=ENV)
    # Seit 25.09.2026 sind Crate + Pruefsummen nach JEDER Aenderung verfolgter Dateien veraltet —
    # die neue Regel K9 meldet das zu Recht. Der dokumentierte Ablauf zieht sie daher nach.
    subprocess.run(["bash", "-lc", f"cd {root} && ./ordner.sh summen >/dev/null 2>&1"],
                   capture_output=True, text=True, env=ENV)
    return p


def pruefe(root: Path):
    return subprocess.run(["python3", "-B", str(CHK), "--root", str(root), "--no-selftest"],
                          capture_output=True, text=True, errors="replace", env=ENV)


class G_Nummern(unittest.TestCase):

    def test_g1_anlegen_vergibt_001_und_baum_bleibt_gruen(self):
        t = kopie("g1")
        p = anlegen(t, "island_sprache")
        self.assertEqual(p.returncode, 0, (p.stdout + p.stderr)[-400:])
        ordner = t / "20_PROJEKTE/standalone/001_island_sprache_2026-09-23"
        self.assertTrue(ordner.is_dir(), "Projektordner fehlt")
        self.assertTrue((ordner / "STATUS.md").is_file(), "STATUS.md fehlt (K3 verlangt sie)")
        self.assertIn("001_island_sprache_2026-09-23", (t / "00_SYSTEM/manifest/repos.yaml").read_text(encoding="utf-8"))
        r = pruefe(t)
        self.assertIn("0 Fehler", r.stdout, (r.stdout + r.stderr)[-500:])   # der eigentliche Beweis

    def test_g2_zweites_projekt_bekommt_002(self):
        t = kopie("g2")
        anlegen(t, "erstes")
        p = anlegen(t, "zweites")
        self.assertEqual(p.returncode, 0, (p.stdout + p.stderr)[-400:])
        self.assertTrue((t / "20_PROJEKTE/standalone/002_zweites_2026-09-23").is_dir())
        self.assertIn("002", p.stdout)

    def test_g3_doppelte_nummer_ist_ein_fehler(self):
        t = kopie("g3")
        anlegen(t, "eins")
        anlegen(t, "zwei")
        # Katalog absichtlich verbiegen: beide Projekte auf Nummer 001
        k = t / "00_SYSTEM/manifest/repos.yaml"
        k.write_text(k.read_text(encoding="utf-8").replace("002_zwei_2026-09-23", "001_zwei_2026-09-23"),
                     encoding="utf-8")
        r = pruefe(t); aus = r.stdout + r.stderr
        self.assertIn("Nummer 001 doppelt vergeben", aus, aus[-500:])
        self.assertIn("ERROR", aus)

    def test_g4_nummer_nicht_dreistellig_ist_ein_hinweis(self):
        t = kopie("g4")
        p = anlegen(t, "kurz")
        self.assertEqual(p.returncode, 0)
        alt = t / "20_PROJEKTE/standalone/001_kurz_2026-09-23"
        neu = t / "20_PROJEKTE/standalone/21_kurz_2026-09-23"
        alt.rename(neu)
        k = t / "00_SYSTEM/manifest/repos.yaml"
        k.write_text(k.read_text(encoding="utf-8").replace("pfad: 20_PROJEKTE/standalone/001_kurz_2026-09-23",
                                                           "pfad: 20_PROJEKTE/standalone/21_kurz_2026-09-23"),
                     encoding="utf-8")
        r = pruefe(t); aus = r.stdout + r.stderr
        self.assertIn("Nummer nicht dreistellig", aus, aus[-500:])

    def test_g5_unerlaubter_name_wird_abgewiesen(self):
        t = kopie("g5")
        p = anlegen(t, "Mein Projekt! mit Umlauten ÖÄÜ")
        self.assertEqual(p.returncode, 2, (p.stdout + p.stderr)[-300:])
        self.assertIn("STOP", p.stdout)
        self.assertEqual(sorted(x.name for x in (t / "20_PROJEKTE/standalone").iterdir()),
                         ["2026-09-21_frisch"], "Es darf nichts angelegt worden sein")


if __name__ == "__main__":
    B.mkdir(parents=True, exist_ok=True)
    try:
        unittest.main(verbosity=2)
    finally:
        if B.exists():
            aufraeumen(B)

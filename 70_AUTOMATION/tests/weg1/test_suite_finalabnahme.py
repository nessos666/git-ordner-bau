#!/usr/bin/env python3
"""FINAL-ABNAHME-Regression (Teil A1/A2/A3) — mindestens ein Test je Korrektur.
Kein bestehender Test wird entfernt oder abgeschwaecht."""
from __future__ import annotations
import json, os, shutil, subprocess, sys, unittest, datetime
from pathlib import Path

S = next(p for p in Path(__file__).resolve().parents if (p / "ordner.sh").is_file()).parent; M = next(p for p in Path(__file__).resolve().parents if (p / "ordner.sh").is_file())
M = next(p for p in Path(__file__).resolve().parents if (p / "ordner.sh").is_file())
for u in ("validation", "indexing", "maintenance", "cross-repo"):
    sys.path.insert(0, str(M / "70_AUTOMATION" / u))
import rules as R, status_sim as SS
import yaml

CHECK = M / "70_AUTOMATION/validation/check_all.py"
B = S / "tmp_final"
KAT = {"repos": [{"pfad": "20_PROJEKTE/p", "name": "p"}]}
SECRET = "AKIA" + "IOSFODNN7EXAMPLE"


def git(c, *a):
    return subprocess.run(["git", "-C", str(c), "-c", "user.email=t@t", "-c", "user.name=t", *a],
                          capture_output=True, text=True, env={"PATH": "/usr/bin:/bin", "HOME": "/tmp"})


def baum(n, repo=True):
    r = B / n
    if r.exists():
        shutil.rmtree(r)
    (r / "00_SYSTEM/manifest").mkdir(parents=True)
    (r / "00_SYSTEM/schemas").mkdir(parents=True)
    (r / "40_DATEN/pointers").mkdir(parents=True)
    shutil.copy(M / "00_SYSTEM/schemas/repos.schema.json", r / "00_SYSTEM/schemas/repos.schema.json")
    (r / "00_SYSTEM/manifest/repos.yaml").write_text("repos: []\n", encoding="utf-8")
    if not repo:
        return r
    q = r / "20_PROJEKTE/p"
    q.mkdir(parents=True)
    git(r / "20_PROJEKTE", "init", "-q", str(q))
    return r, q


def k2(r):
    c = R.run_all(r, KAT)
    return c, [(x["schwere"], x["meldung"][:70]) for x in c.findings if x["regel"] == "K2"], c.abdeckung.get("k2_scope")


class T_A1_Scope(unittest.TestCase):
    """A1: Secret-Pruefung trennt tracked / untracked / ignoriert / ausgeschlossen."""

    def test_1_tracked_secret(self):
        r, q = baum("s_tracked"); (q / "a.md").write_text("x " + SECRET, encoding="utf-8"); git(q, "add", "-A")
        c, f, sc = k2(r)
        self.assertTrue(any(s == "CRITICAL" for s, _ in f), f)

    def test_2_untracked_secret(self):
        r, q = baum("s_untracked"); (q / "neu.md").write_text("x " + SECRET, encoding="utf-8")
        c, f, sc = k2(r)
        self.assertTrue(any(s == "CRITICAL" and "NICHT GEFUEHRTER" in m for s, m in f), f)

    def test_3_ignored_secret(self):
        r, q = baum("s_ignored"); (q / ".gitignore").write_text("lokal.md\n", encoding="utf-8")
        (q / "lokal.md").write_text("x " + SECRET, encoding="utf-8"); git(q, "add", ".gitignore")
        c, f, sc = k2(r)
        self.assertTrue(any(s == "CRITICAL" and "ignoriert" in m for s, m in f), f)

    def test_4_ausgeschlossener_bereich_wird_BENANNT_nicht_still_als_sauber(self):
        r, q = baum("s_scope"); (q / "node_modules").mkdir(); (q / "node_modules/x.js").write_text("ok", encoding="utf-8")
        c, f, sc = k2(r)
        self.assertTrue(sc["ausgeschlossen"] >= 1, sc)
        self.assertTrue(c.abdeckung.get("k2_scope_ausgeschlossen"), "ausgeschlossener Bereich nicht benannt")

    def test_5_normale_untracked_datei_ist_sauber_und_wird_gezaehlt(self):
        r, q = baum("s_normal"); (q / "harmlos.md").write_text("nichts", encoding="utf-8")
        c, f, sc = k2(r)
        self.assertEqual([x for x in f if x[0] == "CRITICAL"], [])
        self.assertGreaterEqual(sc["untracked"], 1, sc)

    def test_6_binaerdatei_wird_nicht_als_text_geprueft(self):
        r, q = baum("s_bin"); (q / "daten.bin").write_bytes(b"\x00\x01\x02" * 100)
        c, f, sc = k2(r)
        self.assertEqual([x for x in f if x[0] == "CRITICAL"], [])

    def test_7_symlink_wird_nicht_verfolgt_und_benannt(self):
        r, q = baum("s_sym")
        aussen = B / "geheim_s.txt"; aussen.write_text("x " + SECRET, encoding="utf-8")
        (q / "verweis.md").symlink_to(aussen)
        c, f, sc = k2(r)
        self.assertEqual([x for x in f if x[0] == "CRITICAL"], [], "Symlink-Ziel wurde gelesen")
        self.assertTrue(any("Symlink" in u["grund"] or "Symlink" in u["pfad"] for u in c.ungeprueft), c.ungeprueft)

    def test_8_datei_ohne_textendung_wird_geprueft(self):
        r, q = baum("s_noext"); (q / "zugang").write_text("x " + SECRET, encoding="utf-8")
        c, f, sc = k2(r)
        self.assertTrue(any(s == "CRITICAL" for s, _ in f), f)

    def test_9_statuszeile_nennt_den_scope(self):
        r, q = baum("s_zeile"); (q / "harmlos.md").write_text("nichts", encoding="utf-8")
        x = subprocess.run([sys.executable, str(CHECK), "--root", str(r), "--no-selftest"],
                           capture_output=True, text=True)
        self.assertIn("K2-Scope: tracked", x.stdout)


class T_A2_Identitaet(unittest.TestCase):
    """A2: fehlende/widerspruechliche Identitaet -> nie OK."""

    def _gesund(self, n):
        r, q = baum(n); SS.lief(r); SS.zustellen(r, "OK", True); SS.waechter_lauf(r); return r, r / "60_RUNTIME/state"

    def _schreib(self, d, pid_je_rolle, quitt_verdikt="zugestellt ok"):
        z = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
        (d / "herzschlag").write_text(f"{z} erzeuger=check_all pid={pid_je_rolle[0]}\n", encoding="utf-8")
        (d / "waechter_herzschlag").write_text(f"{z} erzeuger=waechter pid={pid_je_rolle[1]}\n", encoding="utf-8")
        (d / "quittung").write_text(f"{z} OK quittiert_von=zustellung {quitt_verdikt}"
                                    f" pid={pid_je_rolle[2]}\n", encoding="utf-8")

    def test_10_gleiche_pid_ist_nicht_ok(self):
        r, d = self._gesund("i_gleich"); self._schreib(d, ("111", "111", "111"))
        self.assertNotEqual(SS.waechter(r)[0], "OK")

    def test_11_fehlende_pid_ist_nicht_ok(self):
        r, d = self._gesund("i_keine")
        z = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
        (d / "herzschlag").write_text(f"{z} erzeuger=check_all\n", encoding="utf-8")
        (d / "waechter_herzschlag").write_text(f"{z} erzeuger=waechter\n", encoding="utf-8")
        (d / "quittung").write_text(f"{z} OK quittiert_von=zustellung zugestellt ok\n", encoding="utf-8")
        self.assertNotEqual(SS.waechter(r)[0], "OK")

    def test_12_falscher_erzeuger_ist_nicht_ok(self):
        r, d = self._gesund("i_falsch")
        z = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
        (d / "herzschlag").write_text(f"{z} erzeuger=fremdprozess pid=1\n", encoding="utf-8")
        self.assertNotEqual(SS.waechter(r)[0], "OK")

    def test_13_fifo_als_beweis_haengt_nicht(self):
        r, d = self._gesund("i_fifo")
        p = d / "herzschlag"; p.unlink(); os.mkfifo(p)
        x = subprocess.run([sys.executable, "-c",
                            "import sys;sys.path.insert(0,%r);sys.path.insert(0,%r);import status_sim as S;from pathlib import Path;"
                            "print(S.waechter(Path(%r))[0])" % (str(M / "70_AUTOMATION/maintenance"), str(M / "70_AUTOMATION/validation"), str(r))],
                           capture_output=True, text=True, timeout=25)
        self.assertEqual(x.stdout.strip(), "UNBESTAETIGT", x.stdout + x.stderr[-120:])

    def test_14_symlink_als_beweis_ist_nicht_ok(self):
        r, d = self._gesund("i_sym")
        ziel = B / "beweis_kopie.txt"; ziel.write_text("x", encoding="utf-8")
        p = d / "herzschlag"; p.unlink(); p.symlink_to(ziel)
        self.assertNotEqual(SS.waechter(r)[0], "OK")

    def test_15_beschaedigte_json_ist_nicht_ok(self):
        r, d = self._gesund("i_json")
        for roh in ("{kaputt", "null", "[]", "42"):
            (d / "status.json").write_text(roh, encoding="utf-8")
            self.assertNotEqual(SS.waechter(r)[0], "OK", roh)

    def test_16_zukunfts_und_alt_timestamp(self):
        r, d = self._gesund("i_zeit")
        zuk = (datetime.datetime.now().astimezone() + datetime.timedelta(hours=99)).isoformat(timespec="seconds")
        (d / "herzschlag").write_text(f"{zuk} erzeuger=check_all pid=1\n", encoding="utf-8")
        self.assertNotEqual(SS.waechter(r)[0], "OK")
        alt = "2026-09-01T10:00:00+02:00"
        (d / "herzschlag").write_text(f"{alt} erzeuger=check_all pid=1\n", encoding="utf-8")
        self.assertEqual(SS.waechter(r)[0], "UNBESTAETIGT")


class T_A3_Einzelpunkte(unittest.TestCase):
    """A3: je Punkt FIX NOW (Test) oder DOCUMENTED LIMIT (hier festgehalten)."""

    def test_17_selftest_zeile_luegt_nicht(self):
        x = subprocess.run([sys.executable, str(CHECK), "--no-selftest"], capture_output=True, text=True)
        self.assertIn("Selbsttest: uebersprungen", x.stdout)
        self.assertNotIn("Selbsttest: ok", x.stdout)

    def test_18_basis_ausserhalb_wird_verweigert(self):
        aussen = Path("/tmp/fa_basis_aussen")
        shutil.rmtree(aussen, ignore_errors=True)
        with self.assertRaises(AssertionError):
            SS.szenario_gewalten(aussen)
        self.assertFalse(aussen.exists(), "Basis ausserhalb wurde angelegt")

    def test_19_scope_im_json(self):
        r, q = baum("s_json"); (q / "harmlos.md").write_text("x", encoding="utf-8")
        x = subprocess.run([sys.executable, str(CHECK), "--root", str(r), "--json", "--no-selftest"],
                           capture_output=True, text=True)
        d = json.loads(x.stdout)
        self.assertIn("k2_scope", json.dumps(d))


def _aufraeumen():
    """Die eigene Testwiese MUSS weg: liegen gelassene Baeume verfaelschen K7 (Tiefe) des Sandkastens."""
    shutil.rmtree(B, ignore_errors=True)
    shutil.rmtree(Path("/tmp/fa_basis_aussen"), ignore_errors=True)


if __name__ == "__main__":
    try:
        unittest.main(verbosity=2, exit=False)
    finally:
        _aufraeumen()

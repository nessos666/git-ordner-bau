#!/usr/bin/env python3
"""ETAPPE 2.6 — ROTE Tests fuer die sechs reproduzierbaren Blocker.
Reihenfolge (Pflicht): erst ROT gegen 4feaafe beweisen, dann reparieren, dann gruen.
Kein bestehender Test wird entfernt oder abgeschwaecht. Aufraeumen ist Pflicht."""
from __future__ import annotations
import json, os, shutil, socket, subprocess, sys, unittest
from pathlib import Path

S = next(p for p in Path(__file__).resolve().parents if (p / "ordner.sh").is_file()).parent; M = next(p for p in Path(__file__).resolve().parents if (p / "ordner.sh").is_file())
M = next(p for p in Path(__file__).resolve().parents if (p / "ordner.sh").is_file())
sys.path.insert(0, str(M / "70_AUTOMATION/validation"))
sys.path.insert(0, str(M / "70_AUTOMATION/maintenance"))
sys.path.insert(0, str(M / "70_AUTOMATION/indexing"))
import rules as R
import status_sim as SS

IDX = M / "70_AUTOMATION/indexing/indexer.py"
CHK = M / "70_AUTOMATION/validation/check_all.py"
B = S / "t26"   # KURZ: AF_UNIX-Sockets brechen ab ~107 Zeichen ab (Lehre 23.09.2026)   # Testwiese INNERHALB des Pruefbereichs, per finally geraeumt
# HOME bleibt ECHT: Path.home() definiert die kanonische Sandbox — ein falsches HOME hat
# die zentrale Schranke (zu Recht) ausgeloest und die Tests vor den Blocker gestellt (Harness-Fehler).
ENV = {"PATH": "/usr/bin:/bin:/usr/local/bin", "HOME": str(Path.home()), "LANG": "C.UTF-8",
       "XDG_CONFIG_HOME": "/tmp/b26_cfg", "GIT_CONFIG_NOSYSTEM": "1", "GIT_OPTIONAL_LOCKS": "0"}
SOCK = None


def git(c, *a):
    return subprocess.run(["git", "-C", str(c), "-c", "user.email=t@t", "-c", "user.name=t", *a],
                          capture_output=True, text=True, env=ENV)


def baum(n, repo=True):
    r = B / n
    if r.exists():
        shutil.rmtree(r)
    (r / "00_SYSTEM/manifest").mkdir(parents=True)
    (r / "00_SYSTEM/schemas").mkdir(parents=True)
    (r / "40_DATEN/pointers").mkdir(parents=True)
    shutil.copy(M / "00_SYSTEM/schemas/repos.schema.json", r / "00_SYSTEM/schemas/repos.schema.json")
    (r / "00_SYSTEM/manifest/repos.yaml").write_text(
        'schema_version: 1\nnotfallkontakt: "t"\npassphrase_ort: "keine"\nrepos:\n'
        '  - schema_version: 1\n    name: 2026-09-21_p\n    class: project\n    status: active\n'
        '    owner: t\n    seit: "2026-09-21"\n    bereich: 20_PROJEKTE\n    pfad: 20_PROJEKTE/p\n'
        f'    git: {"true" if repo else "false"}\n    review_am: "2027-09-21"\n    beschreibung: "Test"\n', encoding="utf-8")
    q = r / "20_PROJEKTE/p"
    q.mkdir(parents=True)
    if repo:
        git(r / "20_PROJEKTE", "init", "-q", str(q))
    return r, q


def idx(*a, timeout=60):
    return subprocess.run([sys.executable, "-B", str(IDX), *a], capture_output=True, text=True,
                          timeout=timeout, env=ENV, cwd=str(M / "70_AUTOMATION"))


def chk(*a, timeout=120):
    return subprocess.run([sys.executable, "-B", str(CHK), *a], capture_output=True, text=True,
                          timeout=timeout, env=ENV, cwd=str(M))


class B1_NichtUTF8(unittest.TestCase):
    """BLOCKER 1: beliebige Linux-Dateinamen duerfen den Index nicht toeten."""

    def _mit_name(self, n, rohname: bytes):
        r, q = baum(n)
        p = os.path.join(str(q).encode(), rohname)
        fd = os.open(p, os.O_CREAT | os.O_WRONLY, 0o644)
        os.write(fd, "harmlos".encode()); os.close(fd)
        x = idx("build", "--root", str(r))
        return x

    def test_1_ungueltiges_utf8_kein_crash(self):
        x = self._mit_name("b1_utf8", b"kaputt_\xff\xfe.md")
        self.assertEqual(x.returncode, 0, x.stderr[-300:])
        self.assertNotIn("Traceback", x.stderr + x.stdout)

    def test_2_ungueltiges_utf8_tief_im_baum(self):
        r, q = baum("b1_tief")
        tief = q / "a/b/c/d"; tief.mkdir(parents=True)
        fd = os.open(os.path.join(str(tief).encode(), b"t\xff.md"), os.O_CREAT | os.O_WRONLY, 0o644)
        os.write(fd, b"x"); os.close(fd)
        x = idx("build", "--root", str(r)); self.assertEqual(x.returncode, 0, x.stderr[-300:])

    def test_3_umlaut_unicode_nfc_nfd(self):
        r, q = baum("b1_unicode")
        for n in ["Ärger.md", "日本語.md", "e\u0301.md", "\u00e9.md"]:
            (q / n).write_text("ok", encoding="utf-8")
        x = idx("build", "--root", str(r)); self.assertEqual(x.returncode, 0, x.stderr[-300:])
        y = idx("search", "Ärger", "--root", str(r), "--json")
        self.assertEqual(y.returncode, 0, y.stderr[-200:])

    def test_4_kein_stilles_weglassen_ohne_ausweis(self):
        x = self._mit_name("b1_ausweis", b"still_\xff.txt")
        d = idx("status", "--root", str(B / "b1_ausweis"), "--json")
        roh = d.stdout
        self.assertTrue("escaped" in roh.lower() or "UNVERIF" in roh or "ungeprueft" in roh.lower()
                        or "kodierung" in roh.lower(), roh[:300])


class B2_SpecialFiles(unittest.TestCase):
    """BLOCKER 2: kein unbekannter Dateityp darf blockierend geoeffnet werden."""

    def _haenger(self, n, machen):
        r, q = baum(n); machen(q)
        try:
            x = idx("build", "--root", str(r), timeout=25)
        except subprocess.TimeoutExpired:
            return "HAENGER"
        return x

    def test_5_fifo(self):
        self.assertNotEqual(self._haenger("b2_fifo", lambda q: os.mkfifo(str(q / "roehre"))), "HAENGER")

    def test_6_fifo_mit_bin_endung(self):
        self.assertNotEqual(self._haenger("b2_fifo2", lambda q: os.mkfifo(str(q / "roehre.bin"))), "HAENGER")

    def test_7_unix_socket(self):
        global SOCK
        def mk(q):
            global SOCK
            SOCK = socket.socket(socket.AF_UNIX); SOCK.bind(str(q / "s.sock"))
        self.assertNotEqual(self._haenger("b2_sock", mk), "HAENGER")

    def test_8_broken_symlink(self):
        self.assertNotEqual(self._haenger("b2_sym", lambda q: (q / "tot").symlink_to(B / "gibt_es_nicht")), "HAENGER")

    def test_9_status_haengt_auch_nicht(self):
        r, q = baum("b2_status"); os.mkfifo(str(q / "roehre"))
        idx("build", "--root", str(r), timeout=25)
        try:
            x = idx("status", "--root", str(r), timeout=25)
        except subprocess.TimeoutExpired:
            self.fail("status haengt an der FIFO")
        self.assertNotIn("Traceback", x.stderr)


class B3_SandboxSchranke(unittest.TestCase):
    """BLOCKER 3: VALIDATE BEFORE WRITE — zentrale Schranke, kein Schreiben ausserhalb."""

    def test_10_zentrale_funktion_existiert(self):
        self.assertTrue(hasattr(R, "assert_write_inside_sandbox"), "zentrale Schranke fehlt")

    def test_11_basis_ausserhalb_legt_kein_verzeichnis_an(self):
        ziel = Path("/tmp/b26_aussen")
        shutil.rmtree(ziel, ignore_errors=True)
        try:
            x = subprocess.run([sys.executable, "-B", str(M / "70_AUTOMATION/maintenance/status_sim.py"),
                                "--basis", str(ziel)], capture_output=True, text=True, timeout=120, env=ENV)
        except subprocess.TimeoutExpired:
            self.fail("status_sim haengt")
        self.assertFalse(ziel.exists(), "Verzeichnis ausserhalb der Sandbox wurde angelegt")
        self.assertNotEqual(x.returncode, 0)

    def test_12_fixtures_ausserhalb_schreibt_nicht(self):
        ziel = Path("/tmp/b26_fx"); shutil.rmtree(ziel, ignore_errors=True)
        r, q = baum("b3_fx")
        chk("--root", str(r), "--fixtures", str(ziel))
        self.assertFalse(ziel.exists(), "--fixtures wurde ausserhalb angelegt")

    def test_13_schranke_weist_die_faelle_ab(self):
        s = R.SANDBOX
        ok = [s, s / "tmp_26", s / "MASTER/70_AUTOMATION/tmp_neu"]
        boese = [Path("/tmp/x"), s.parent / (s.name + "_ESCAPE"), Path("/tmp/../tmp/y")]
        for p in ok:
            R.assert_write_inside_sandbox(p)
        for p in boese:
            with self.assertRaises(Exception):
                R.assert_write_inside_sandbox(p)


class B4_K2Coverage(unittest.TestCase):
    """BLOCKER 4: Coverage ehrlich und rekursiv — kein stilles 'sauber'."""

    KAT = {"repos": [{"schema_version": 1, "name": "2026-09-21_p", "class": "project",
                      "status": "active", "owner": "t", "seit": "2026-09-21",
                      "bereich": "20_PROJEKTE", "pfad": "20_PROJEKTE/p", "git": False,
                      "review_am": "2027-09-21", "beschreibung": "Test"}]}
    SEC = "AKIA" + "IOSFODNN7EXAMPLE"

    def test_14_nested_excluded_wird_gezaehlt(self):
        r, q = baum("b4_node")
        (q / "node_modules/pkg").mkdir(parents=True)
        (q / "node_modules/pkg/secret.txt").write_text("x " + self.SEC, encoding="utf-8")
        c = R.run_all(r, self.KAT)
        sc = c.abdeckung.get("k2_scope", {})
        self.assertGreaterEqual(sc.get("ausgeschlossen", 0), 1, sc)
        self.assertTrue(c.abdeckung.get("k2_scope_ausgeschlossen"), "Bereich nicht benannt")

    def test_15_nicht_git_bereich_mit_secret(self):
        r, q = baum("b4_nongit", repo=False)
        (q / "keys").mkdir(); (q / "keys/id_rsa").write_text("x " + self.SEC, encoding="utf-8")
        c = R.run_all(r, self.KAT)
        self.assertTrue(any(f["regel"] == "K2" for f in c.findings), [f["meldung"][:60] for f in c.findings])
        self.assertTrue(c.abdeckung.get("k2_scope_nicht_git") is not None, "Nicht-Git-Bereich nicht erfasst")

    def test_16_bare_repo_wird_erkannt(self):
        r, q = baum("b4_bare")
        bare = r / "20_PROJEKTE/bare.git"
        subprocess.run(["git", "init", "-q", "--bare", str(bare)], capture_output=True, env=ENV)
        c = R.run_all(r, {"repos": [{"pfad": "20_PROJEKTE/bare.git", "name": "bare"}]})
        self.assertTrue(any("bare" in json.dumps(f).lower() for f in c.findings)
                        or "bare" in json.dumps(c.abdeckung).lower(), json.dumps(c.abdeckung)[:300])

    def test_17_history_coverage_wird_ausgewiesen(self):
        r, q = baum("b4_hist"); (q / "a.md").write_text("x " + self.SEC, encoding="utf-8"); git(q, "add", "-A")
        x = chk("--root", str(r), "--json", "--no-selftest")
        d = json.loads(x.stdout)
        self.assertIn("history_coverage", json.dumps(d).lower(),
                      "Kein Ausweis der History-Coverage: 'sauber' wird behauptet")

    def test_18_secret_geloescht_aber_in_history_kein_stilles_OK(self):
        r, q = baum("b4_del"); (q / "a.md").write_text("x " + self.SEC, encoding="utf-8"); git(q, "add", "-A")
        git(q, "commit", "-qm", "mit secret"); (q / "a.md").write_text("harmlos", encoding="utf-8")
        x = chk("--root", str(r), "--json", "--no-selftest")
        d = json.loads(x.stdout)
        hist = json.dumps(d).lower()
        self.assertTrue("history_coverage" in hist and "partial" in hist, hist[:400])


class B5_Rollentrennung(unittest.TestCase):
    """BLOCKER 5: keine Sicherheitsbehauptung, die nicht beweisbar ist."""

    def test_19_keine_falsche_behauptung_im_code(self):
        for f in [M / "70_AUTOMATION/maintenance/status_sim.py", M / "70_AUTOMATION/validation/check_all.py"]:
            t = f.read_text(encoding="utf-8")
            self.assertNotIn("keiner stellt sich alle selbst aus", t.lower())
            self.assertNotIn("keiner stellt sich alle Beweise selbst aus", t.lower())

    def test_20_status_weist_rollentrennung_als_nicht_verifiziert_aus(self):
        r, q = baum("b5_status")
        SS.lief(r); SS.zustellen(r, "OK", True); SS.waechter_lauf(r)
        x = chk("--root", str(r), "--json", "--no-selftest")
        d = json.loads(x.stdout)
        self.assertIn("NICHT VERIFIZIERT", json.dumps(d).upper(), json.dumps(d)[:300])

    def test_21_drei_erfundene_pids_kein_verifiziertes_OK(self):
        r, q = baum("b5_fake")
        SS.lief(r); SS.zustellen(r, "OK", True); SS.waechter_lauf(r)
        d = r / "60_RUNTIME/state"
        import datetime
        z = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
        (d / "herzschlag").write_text(f"{z} erzeuger=check_all pid=11\n", encoding="utf-8")
        (d / "waechter_herzschlag").write_text(f"{z} erzeuger=waechter pid=22\n", encoding="utf-8")
        (d / "quittung").write_text(f"{z} OK quittiert_von=zustellung zugestellt ok pid=33\n", encoding="utf-8")
        x = chk("--root", str(r), "--json", "--no-selftest")
        d2 = json.loads(x.stdout)
        self.assertNotIn('"rollentrennung": "OK"', json.dumps(d2))
        self.assertIn("NICHT VERIFIZIERT", json.dumps(d2).upper())


class B6_IndexWahrheit(unittest.TestCase):
    """BLOCKER 6: 'frisch' nur bei COMPLETE, definierte Exitcodes, keine Tracebacks."""

    def test_22_fehlender_katalog_kein_frisch_und_kein_null(self):
        r, q = baum("b6_kat")
        (r / "00_SYSTEM/manifest/repos.yaml").unlink()
        x = idx("build", "--root", str(r))
        self.assertIn(x.returncode, (2, 3, 4), f"Exit {x.returncode} — MISSING darf kein OK sein: {x.stdout[:200]}")
        self.assertNotIn("Traceback", x.stderr)

    def test_23_unlesbarer_ordner_kein_COMPLETE(self):
        r, q = baum("b6_eacces")
        op = q / "dicht"; op.mkdir(); (op / "x.md").write_text("x", encoding="utf-8")
        os.chmod(op, 0o000)
        try:
            x = idx("build", "--root", str(r))
            y = idx("status", "--root", str(r), "--json")
            roh = (x.stdout + y.stdout)
            self.assertIn("PARTIAL", roh.upper() + y.stderr.upper() + x.stderr.upper(),
                          "unlesbarer Bereich ohne COMPLETE/PARTIAL-Ausweis: " + roh[:200])
            self.assertNotIn('"frisch": true', roh)
        finally:
            os.chmod(op, 0o755)

    def test_24_kaputter_index_kein_traceback(self):
        r, q = baum("b6_kaputt"); idx("build", "--root", str(r))
        for db in r.rglob("*.db"):
            db.write_bytes(b"kein sqlite")
        x = idx("status", "--root", str(r))
        self.assertNotIn("Traceback", x.stderr)
        self.assertIn(x.returncode, (1, 2, 3, 4), f"Exit {x.returncode}")

    def test_25_exitcodes_zentral_dokumentiert(self):
        t = (M / "70_AUTOMATION/indexing/indexer.py").read_text(encoding="utf-8")
        self.assertIn("UNBESTAETIGT", t.upper(), "kein zentraler UNBESTAETIGT-Exitcode")
        d = idx("status", "--root", str(B / "gibt_es_nicht"))
        self.assertIn(d.returncode, (2, 3, 4), f"fehlender Baum: Exit {d.returncode}")

    def test_26_frisch_nur_bei_complete(self):
        r, q = baum("b6_frisch"); (q / "a.md").write_text("hallo", encoding="utf-8")
        idx("build", "--root", str(r))
        y = json.loads(idx("status", "--root", str(r), "--json").stdout)
        self.assertIn("quellen_zustand", json.dumps(y).lower(), json.dumps(y)[:250])
        self.assertIn("complete", json.dumps(y).lower())


def _aufraeumen():
    global SOCK
    try:
        if SOCK is not None:
            SOCK.close()
    except Exception:
        pass
    shutil.rmtree(B, ignore_errors=True)
    for p in ("/tmp/b26_aussen", "/tmp/b26_fx"):
        shutil.rmtree(p, ignore_errors=True)


if __name__ == "__main__":
    try:
        unittest.main(verbosity=2, exit=False)
    finally:
        _aufraeumen()


# BLOCKER 7A (2.7): Aufraeumen darf NICHT vom __main__-Zweig abhaengen — sonst bleiben Testbaeume
# liegen (K7/K4/K2-Falschbefunde im naechsten Lauf). Deshalb zusaetzlich zentral beim Prozessende.
import atexit as _atexit
_atexit.register(lambda: __import__("shutil").rmtree(B, ignore_errors=True))
_atexit.register(lambda: __import__("shutil").rmtree(Path(B).parent / "tmp26", ignore_errors=True))

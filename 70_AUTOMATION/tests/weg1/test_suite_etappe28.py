#!/usr/bin/env python3
"""ETAPPE 2.8 — Dauerhafte Regressionstests fuer die behobenen Blocker F1-F6.

Regel dieser Datei: jeder Test enthaelt eine POSITIVKONTROLLE. Ein Test, dessen
Positivkontrolle fehlschlaegt, beweist nichts. Alle Testbaeume liegen INNERHALB des
Pruefbereichs (70_AUTOMATION/tests/tmp28) und werden im tearDownClass entfernt.

F1  unlesbares Programmteil  -> sichtbare Meldung + Exitcode, KEIN Traceback, kein stilles OK
F2  Sonderdatei (FIFO) als Index -> kein Haenger, klare Meldung, Exitcode != 0
F8  Statusdatei vollstaendig und deckungsgleich mit dem Lauf (status/exit/geprueft)
F5  Obergrenze 5000 Dateien -> sichtbare Meldung statt stillem Abschneiden
F3  ungewoehnliche Dateinamen -> UTF-8 lesbar, keine kaputten Bytes, rc = 0
F4  --json liefert NUR JSON (json.loads ueber die gesamte Ausgabe)
"""
from __future__ import annotations
import json, os, shlex, shutil, subprocess, sys, unittest
from pathlib import Path

M = next(p for p in Path(__file__).resolve().parents if (p / "ordner.sh").is_file())
IDX = M / "70_AUTOMATION/indexing/indexer.py"
CHK = M / "70_AUTOMATION/validation/check_all.py"
# Testwiese AUSSERHALB von M (sonst kopiert sich der Baum in sich selbst -> Rekursion),
# aber INNERHALB der Sandbox die Projekt-Sandbox (die zentrale Schranke prueft das).
B = M.parent / "tmp28"
ENV = {"PATH": "/usr/bin:/bin:/usr/local/bin", "HOME": str(Path.home()), "LANG": "C.UTF-8",
       "GIT_CONFIG_NOSYSTEM": "1", "GIT_OPTIONAL_LOCKS": "0"}


def kopie(name: str) -> Path:
    """Frische Kopie des Baums — nach JEDER Aenderung neu kopieren, nie eine alte messen."""
    z = B / name
    if z.exists():
        aufraeumen(z)
    shutil.copytree(M, z)
    # Die Kopie als eigenstaendigen, sauberen Stand festschreiben: ein nicht versionierter
    # Rest (z. B. gerade bearbeitete Datei) darf die Positivkontrolle nicht verfaelschen.
    subprocess.run(["git", "-C", str(z), "add", "-A"], capture_output=True, env=ENV)
    subprocess.run(["git", "-C", str(z), "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-q", "-m", "Testkopie (Ausgangsstand)"], capture_output=True, env=ENV)
    return z


def aufraeumen(z):
    """chmod vor rm -rf: ein Test setzt absichtlich Rechte auf 000.
    SCHRANKE (Lehre 23.09.2026): geloescht wird NUR unterhalb von B. Die Sandbox selbst,
    der Baum oder deren Eltern NIEMALS — ein falsch berechneter Pfad hat hier den ganzen
    Baum geloescht (Variable zeigte auf die Sandbox statt auf die Testwiese)."""
    z = Path(z).resolve()
    b = B.resolve()
    sb = M.parent
    if not b.name.startswith(("tmp", "f1", "scratch")) or sb not in b.parents:
        raise RuntimeError(f"TESTWIESE UNPLAUSIBEL — Loeschen abgebrochen: {b}")
    if z != b and b not in z.parents:
        raise RuntimeError(f"LOESCHEN VERWEIGERT: {z} liegt nicht unter der Testwiese {b}")
    q = shlex.quote(str(z))
    subprocess.run(["bash", "-lc", f"chmod -R u+rwX {q} 2>/dev/null; rm -rf {q}"], capture_output=True)


def lauf(root: Path, *args, timeout=300):
    """Werkzeug im Testbaum starten. TimeoutExpired wird NICHT verschluckt.

    check_all wird hier mit --no-selftest gerufen: der interne VALIDATOR-SELBSTTEST sucht
    seine Fixtures neben der Baumwurzel und wuerde in einer Testkopie fehlschlagen (er ist
    nicht Gegenstand dieser Suite — die uebrigen Suiten pruefen ihn ausfuehrlich)."""
    args = list(args)
    if args and args[0].endswith("check_all.py"):
        args.insert(1, "--no-selftest")
    return subprocess.run([sys.executable, "-B", *args], cwd=root / "70_AUTOMATION",
                          capture_output=True, text=True, env=ENV, timeout=timeout)


class F1_ProgrammteilUnlesbar(unittest.TestCase):
    def test_positivkontrolle_und_unlesbares_regelmodul(self):
        t = kopie("f1")
        p = lauf(t, "validation/check_all.py", "--root", str(t))
        self.assertLessEqual(p.returncode, 1, f"Positivkontrolle rot: {p.stdout[-200:]}")   # Hinweis erlaubt
        self.assertNotIn("Traceback", p.stdout + p.stderr)
        # Rot: Regelmodul unlesbar -> Meldung + Exitcode, kein Traceback, kein stilles OK
        os.chmod(t / "70_AUTOMATION/validation/rules.py", 0)
        q = lauf(t, "validation/check_all.py", "--root", str(t))
        self.assertNotEqual(0, q.returncode, "unlesbares Regelmodul darf NIE 0 ergeben")
        self.assertNotIn("Traceback", q.stderr, "kein Traceback, sondern kontrollierte Meldung")
        aus = (q.stdout + q.stderr).upper()
        # Eigenschaft pruefen, nicht einen Wortlaut: sichtbarer Abbruch ODER sichtbarer Fehler,
        # kein Traceback, Exitcode != 0 (die Meldung haengt davon ab, WELCHE Datei unlesbar ist).
        self.assertTrue("ABBRUCH" in aus or "NICHT LESBAR" in aus, aus[-200:])
        self.assertNotIn("TRACEBACK", aus)
        aufraeumen(t)


class F8_StatusdateiVollstaendig(unittest.TestCase):
    def test_statusdatei_deckungsgleich(self):
        t = kopie("f8")
        p = lauf(t, "validation/check_all.py", "--root", str(t))
        d = json.loads((t / "60_RUNTIME/state/status.json").read_text(encoding="utf-8"))
        self.assertIn(d["status"], ("OK", "WARNING"))   # Hinweis erlaubt, Fehler nicht
        self.assertLessEqual(d["exit"], 1, "Exitcode muss in der Statusdatei stehen (Hinweis erlaubt)")
        self.assertGreater(d["geprueft"], 0, "Anzahl gepruefter Objekte fehlte frueher (None)")
        # Rot-Variante: Katalog entfernen -> Datei muss CRITICAL mit exit != 0 zeigen
        (t / "00_SYSTEM/manifest/repos.yaml").unlink()
        q = lauf(t, "validation/check_all.py", "--root", str(t))
        e = json.loads((t / "60_RUNTIME/state/status.json").read_text(encoding="utf-8"))
        self.assertEqual("CRITICAL", e["status"])
        self.assertEqual(q.returncode, e["exit"], "Datei und Lauf muessen denselben Exitcode nennen")
        self.assertNotEqual(0, e["exit"])
        aufraeumen(t)


class F2_SonderdateiKeinHaenger(unittest.TestCase):
    def test_fifo_als_index_haengt_nicht(self):
        t = kopie("f2")
        db = t / "60_RUNTIME/cache/index/suche.db"
        # Positivkontrolle: normaler Index laeuft
        p = lauf(t, "indexing/indexer.py", "status", "--root", str(t))
        self.assertLessEqual(p.returncode, 1, f"Positivkontrolle rot: {p.stdout[-200:]}")   # Hinweis erlaubt
        if db.exists():
            db.unlink()
        os.mkfifo(db)
        try:
            q = lauf(t, "indexing/indexer.py", "search", "test", "--root", str(t), timeout=20)
        except subprocess.TimeoutExpired:
            self.fail("Sonderdatei als Index: Werkzeug HAENGT (Timeout) statt sauber abzubrechen")
        self.assertNotEqual(0, q.returncode)
        self.assertIn("SONDERDATEI", (q.stdout + q.stderr).upper())
        aufraeumen(t)


class F5_ObergrenzeSichtbar(unittest.TestCase):
    def test_5000_deckel_wird_gemeldet(self):
        t = kopie("f5")
        subprocess.run(["bash", "-lc", f"rm -rf {t}/.git"], capture_output=True)   # Nicht-Git-Baum
        d = t / "20_PROJEKTE/standalone/2026-09-21_frisch"
        d.mkdir(parents=True, exist_ok=True)
        for i in range(5001):
            (d / f"d{i:05d}.md").write_text("x", encoding="utf-8")
        p = lauf(t, "validation/check_all.py", "--root", str(t), timeout=600)
        txt = (p.stdout + p.stderr).upper()
        self.assertIn("OBERGRENZE", txt, "stilles Abschneiden ist verboten — Meldung fehlt")
        self.assertIn("NICHT", txt)
        aufraeumen(t)


class F3_UngewoehnlicheNamen(unittest.TestCase):
    def test_nicht_utf8_name_bleibt_lesbar(self):
        t = kopie("f3")
        d = t / "20_PROJEKTE/standalone/2026-09-21_frisch"
        d.mkdir(parents=True, exist_ok=True)
        p = os.path.join(os.fsencode(d), b"fremdname_\xff\xfe.md")
        with open(p, "wb") as fh:
            fh.write(b"# Test\n")
        qb = lauf(t, "indexing/indexer.py", "build", "--root", str(t))
        self.assertEqual(0, qb.returncode, f"build: {qb.stdout[-150:]}")   # Positivkontrolle
        qs = lauf(t, "indexing/indexer.py", "search", "fremdname", "--root", str(t))
        self.assertEqual(0, qs.returncode, f"search: {qs.stdout[-150:]}")
        self.assertIn(r"\xff", qs.stdout,
                      "ungewoehnlicher Name muss escaped (\\xff) erscheinen, nicht als rohe Bytes")
        aufraeumen(t)


class F4_JsonAuslesbar(unittest.TestCase):
    def test_json_ist_nur_json(self):
        t = kopie("f4")
        faelle = [("indexing/indexer.py", "build", "--root", str(t), "--json"),
                  ("indexing/indexer.py", "status", "--root", str(t), "--json"),
                  ("indexing/indexer.py", "search", "test", "--root", str(t), "--json"),
                  ("validation/check_all.py", "--root", str(t), "--json")]
        for args in faelle:
            q = lauf(t, *args)
            try:
                json.loads(q.stdout)
            except Exception as ex:                # kein stilles "ist halt so"
                self.fail(f"{args[1] if len(args) > 1 else args[0]} --json nicht auslesbar: "
                          f"{type(ex).__name__} | erste Zeile: {q.stdout.strip().splitlines()[:1]}")
        aufraeumen(t)


class F9_Loeschschranke(unittest.TestCase):
    """LEHRE 23.09.2026: ein falsch berechneter Pfad hat den ganzen Baum geloescht.
    Die Schranke ist jetzt Teil der Suite — sie muss rot werden, wenn sie faellt."""

    def test_verweigert_sandbox_und_baum(self):
        for ziel in (next(p for p in Path(__file__).resolve().parents if (p / "ordner.sh").is_file()).parent, M, M.parent):
            with self.assertRaises(RuntimeError, msg=f"nicht verweigert: {ziel}"):
                aufraeumen(ziel)

    def test_erlaubt_testwiese_unterhalb_B(self):
        z = B / "f9probe"; z.mkdir(parents=True, exist_ok=True); (z / "x.txt").write_text("x")
        aufraeumen(z)
        self.assertFalse(z.exists())


if __name__ == "__main__":
    B.mkdir(parents=True, exist_ok=True)
    try:
        unittest.main(verbosity=2)
    finally:
        aufraeumen(B)

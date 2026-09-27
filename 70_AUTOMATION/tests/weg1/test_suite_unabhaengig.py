#!/usr/bin/env python3
"""REGRESSIONSSUITE der UNABHAENGIGEN ABNAHMERUNDE (Etappe 2).

Jeder Test entspricht einem echten Fund der drei unabhaengigen Pruefer (A Daten/Skalierung,
B Git/Isolation, C Waechter/Mensch). Reihenfolge nach dem Muster der Runde:
  Fund -> Ursache -> minimale Korrektur -> Regressionstest
Ein Test, der hier fehlschlaegt, bedeutet: die Korrektur ist zurueckgefallen.
"""
from __future__ import annotations
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

S = next(p for p in Path(__file__).resolve().parents if (p / "ordner.sh").is_file()).parent; M = next(p for p in Path(__file__).resolve().parents if (p / "ordner.sh").is_file())
M = next(p for p in Path(__file__).resolve().parents if (p / "ordner.sh").is_file())
sys.path.insert(0, str(M / "70_AUTOMATION/validation"))
sys.path.insert(0, str(M / "70_AUTOMATION/indexing"))
sys.path.insert(0, str(M / "70_AUTOMATION/maintenance"))
sys.path.insert(0, str(M / "70_AUTOMATION/cross-repo"))
sys.path.insert(0, str(M / "70_AUTOMATION/tests"))
import rules as R
import indexer, status_sim, adapter_readonly as AD, check_all as CA
import yaml


def baum(name: str, eintraege=None, dirs=(), state_schreibbar=True):
    r = S / "tmp_unabh" / name
    if r.exists(): shutil.rmtree(r)
    (r / "00_SYSTEM/manifest").mkdir(parents=True); (r / "00_SYSTEM/schemas").mkdir(parents=True)
    shutil.copy(M / "00_SYSTEM/schemas/repos.schema.json", r / "00_SYSTEM/schemas/repos.schema.json")
    (r / "40_DATEN/pointers").mkdir(parents=True)
    for d in dirs: (r / d).mkdir(parents=True, exist_ok=True)
    z = ['schema_version: 1\nnotfallkontakt: "x"\npassphrase_ort: "keine"\nrepos:\n',
         '  - schema_version: 1\n    name: sys\n    class: system\n    status: paused\n'
         '    owner: t\n    seit: "2026-09-21"\n    bereich: 00_SYSTEM\n    pfad: 00_SYSTEM\n    git: false\n']
    (r / "00_SYSTEM/manifest/repos.yaml").write_text("".join(z + (eintraege or [])), encoding="utf-8")
    if state_schreibbar:
        (r / "60_RUNTIME/state").mkdir(parents=True, exist_ok=True)
    return r


def kat(r): return yaml.safe_load((r / "00_SYSTEM/manifest/repos.yaml").read_text(encoding="utf-8"))
def lauf(r):
    x = subprocess.run([sys.executable, str(M / "70_AUTOMATION/validation/check_all.py"),
                        "--root", str(r), "--json", "--no-selftest"], capture_output=True, text=True)
    try: return json.loads(x.stdout), x.returncode
    except Exception: return {"roh": x.stdout[-300:], "stderr": x.stderr[-300:]}, x.returncode


class T_RT_A_Daten(unittest.TestCase):
    def test_95_zeiger_kein_mapping_kein_absturz(self):
        """RT-A F11: Zeigerdatei, die kein Mapping ist, darf den Pruefer NICHT toeten."""
        r = baum("f11")
        (r / "40_DATEN/pointers/boese.yaml").write_text("- nur\n- eine\n- liste\n", encoding="utf-8")
        d, code = lauf(r)
        self.assertIn("status", d, f"Pruefer abgestuerzt: {d}")
        self.assertEqual(d["status"], "ERROR")
        self.assertTrue(any("Mapping" in f["meldung"] for f in d["findings"]))
        self.assertTrue((r / "60_RUNTIME/state/herzschlag").exists(), "Herzschlag fehlt nach Fehler")

    def test_96_pfad_dublette_ueber_punkt(self):
        """RT-A F8: zwei Eintraege auf denselben Ordner ueber '.'-Schreibweise."""
        r = baum("f8", dirs=["20_PROJEKTE/d1"],
                 eintraege=['  - schema_version: 1\n    name: eins\n    class: project\n    status: paused\n'
                            '    owner: t\n    seit: "2026-09-21"\n    bereich: 20_PROJEKTE\n'
                            '    pfad: 20_PROJEKTE/d1\n    git: false\n',
                            '  - schema_version: 1\n    name: zwei\n    class: project\n    status: paused\n'
                            '    owner: t\n    seit: "2026-09-21"\n    bereich: 20_PROJEKTE\n'
                            '    pfad: 20_PROJEKTE/d1/.\n    git: false\n'])
        ctx = R.run_all(r, kat(r))
        self.assertTrue([f for f in ctx.findings if f["regel"] == "K5" and "DENSELBEN" in f["meldung"]],
                        [f["meldung"] for f in ctx.findings if f["regel"] == "K5"])

    def test_97_case_kollision_bei_dateien(self):
        """RT-A F9: K6 muss auch DATEIEN vergleichen, nicht nur Ordner."""
        r = baum("f9", dirs=["20_PROJEKTE/d1"])
        (r / "20_PROJEKTE/d1/Notiz.md").write_text("a", encoding="utf-8")
        (r / "20_PROJEKTE/d1/notiz.md").write_text("b", encoding="utf-8")
        ctx = R.run_all(r, kat(r))
        self.assertTrue([f for f in ctx.findings if f["regel"] == "K6" and "Kollision" in f["meldung"]])

    def test_98_secret_in_grosser_datei(self):
        """RT-A F10: Secret in einer 3,2-MB-Datei (der 2-MB-Deckel war blind)."""
        r = baum("f10", dirs=["20_PROJEKTE/d1"])
        repo = r / "20_PROJEKTE/d1"
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        # KEIN Secret-Literal im Repo: das Testmuster wird erst zur Laufzeit zusammengesetzt
        # (der Pruefer meldete das Literal zu Recht als Secret im eigenen Repo).
        muster = "AKIA" + "IOSFODNN7EXAMPLE"
        (repo / "gross.txt").write_text("x" * (3_200_000) + "\n" + muster + "\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)   # K2 prueft VERSIONIERTE Inhalte
        ctx = R.run_all(r, kat(r))
        self.assertTrue([f for f in ctx.findings if f["regel"] == "K2" and f["schwere"] == "CRITICAL"],
                        [f["meldung"] for f in ctx.findings if f["regel"] == "K2"])

    def test_99_symlink_in_40_daten_wird_gerechnet(self):
        """RT-A F7: Symlink auf ein Datenverzeichnis darf das Budget nicht umgehen."""
        r = baum("f7")
        ziel = r / "20_PROJEKTE/grosse_daten"; ziel.mkdir(parents=True, exist_ok=True)
        (ziel / "d.bin").write_bytes(b"0" * (2 << 20))
        (r / "40_DATEN/pointers/verweis").symlink_to(ziel)
        import importlib
        b = importlib.import_module("budget")
        d = b.pruefe(r)
        self.assertEqual(d["status"], "FAIL")
        self.assertTrue(d["groesse_b"] > (1 << 20), d)
        ctx = R.run_all(r, kat(r))
        self.assertTrue([f for f in ctx.findings if "Symlink in 40_DATEN" in f["meldung"]])

    def test_100_leerer_index_wird_erkannt(self):
        """RT-A F1/F2: gueltige, aber leere bzw. ausgeraeumte DB ist KEIN Index."""
        r = baum("f1")
        indexer.build(r, still=True)
        import sqlite3
        v = sqlite3.connect(str(indexer.index_pfad(r))); v.execute("DELETE FROM dokumente"); v.commit(); v.close()
        st = indexer.status(r)
        self.assertTrue(st.get("defekt"), st)
        self.assertIn("LEER", json.dumps(st))

    def test_101_indexverzeichnis_statt_datei(self):
        """RT-A F4: suche.db als VERZEICHNIS darf keinen Traceback erzeugen."""
        r = baum("f4")
        indexer.index_pfad(r).mkdir(parents=True, exist_ok=True)
        t, fehler = indexer.search(r, "x")
        self.assertEqual(t, [])
        self.assertIn("VERZEICHNIS", fehler or "")

    def test_102_frische_erkennt_tiefe_neue_datei(self):
        """RT-A F3: eine neue Datei in 20_PROJEKTE muss 'veraltet: ja' ergeben."""
        r = baum("f3")
        indexer.build(r, still=True)
        self.assertEqual(indexer.status(r)["veraltet_gegenueber_quellen"], "nein")
        (r / "20_PROJEKTE/neu").mkdir(parents=True)
        (r / "20_PROJEKTE/neu/tief.md").write_text("neu", encoding="utf-8")
        self.assertEqual(indexer.status(r)["veraltet_gegenueber_quellen"], "ja")

    def test_103_suche_schreibt_nie(self):
        """RT-B: das LESENDE Unterkommando darf keinen Index anlegen."""
        r = baum("f5")
        t, fehler = indexer.search(r, "x")
        self.assertEqual(t, [])
        self.assertFalse(indexer.index_pfad(r).exists(), "Suche hat eine Indexdatei angelegt!")


class T_RT_B_Git(unittest.TestCase):
    def test_104_git_allowlist_haelt(self):
        """RT-B CRITICAL: schreibende Argumentformen duerfen nicht durchkommen."""
        r = baum("b_git"); repo = r / "20_PROJEKTE/repo"; repo.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        for args in (("log", "-1", "--output=/tmp/x"), ("config", "core.fsmonitor", "true"),
                     ("branch", "neu"), ("symbolic-ref", "HEAD", "refs/heads/x"),
                     ("status", "--porcelain", "--untracked-files=all", "extra")):
            with self.assertRaises(AssertionError, msg=f"{args} wurde erlaubt!"):
                AD.git(repo, *args)
        self.assertIn(("config", "--get", "core.fsmonitor"), AD.LESEND)
        self.assertNotIn("GIT_DIR", AD.UMGEBUNG)

    def test_105_readme_symlink_wird_nicht_gelesen(self):
        """RT-B: Symlink-README darf nichts von AUSSERHALB liefern."""
        r = baum("b_sym"); repo = r / "20_PROJEKTE/repo"; repo.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        (repo / "README.md").symlink_to("/etc/hostname")
        i = AD.beobachte(repo)
        self.assertIn("Symlink", i.get("hinweis", ""))
        self.assertNotIn("localhost", i["readme"])

    def test_106_adapter_ohne_memoryerror_bei_grossdatei(self):
        """RT-B: 3-GB-README darf den Adapterlauf nicht toeten."""
        r = baum("b_gross"); repo = r / "20_PROJEKTE/repo"; repo.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        big = repo / "README.md"; big.touch()
        os.truncate(big, 3_000_000_000)          # sparse, kein echter Platzverbrauch
        i = AD.beobachte(repo)
        self.assertIn("head", i)

    def test_107_check_all_verweigert_fremde_wurzel(self):
        """RT-B: --root ausserhalb der Sandbox darf dort NICHTS schreiben.

        Der Pruefer definiert seine Sandbox als den Ordner UEBER dem Baum. Liegt der Baum
        selbst in einem Temp-Ordner (etwa ein frischer Klon in TMPDIR), dann liegt der
        Temp-Ordner INNERHALB dieser Sandbox — dort darf der Pruefer laut eigener Regel
        schreiben, und der Test schluege falschen Alarm (gemessen 27.09.2026). Darum wird
        ein Ort gesucht, der wirklich ausserhalb liegt; findet sich keiner, wird die Regel
        als nicht pruefbar benannt statt sie faelschlich als bestanden zu verbuchen.
        """
        sandbox = Path(M).resolve().parent
        fremd = None
        for ort in (Path("/tmp"), Path("/var/tmp"), Path(tempfile.gettempdir())):
            if not ort.is_dir():
                continue
            kandidat = Path(tempfile.mkdtemp(prefix="fremd_", dir=str(ort))).resolve()
            if sandbox not in kandidat.parents:
                fremd = kandidat
                break
            shutil.rmtree(kandidat, ignore_errors=True)
        if fremd is None:
            self.skipTest("kein Temp-Ort ausserhalb der Sandbox verfuegbar — Regel nicht pruefbar")
        try:
            x = subprocess.run([sys.executable, str(M / "70_AUTOMATION/validation/check_all.py"),
                                "--root", str(fremd)], capture_output=True, text=True)
            self.assertEqual(x.returncode, 3)
            self.assertFalse((fremd / "60_RUNTIME").exists(), "Pruefer hat ausserhalb geschrieben!")
        finally:
            shutil.rmtree(fremd, ignore_errors=True)


class T_RT_C_Waechter(unittest.TestCase):
    def test_108_pruefer_stellt_keine_quittung_aus(self):
        """RT-C CRITICAL: die Quittung ist der Zustellnachweis des Menschen, nicht des Pruefers."""
        quelle = (M / "70_AUTOMATION/validation/check_all.py").read_text(encoding="utf-8")
        self.assertNotIn('(stt / "quittung")', quelle)
        self.assertIn('(stt / "status.json")', quelle)
        r = baum("c1")
        lauf(r)
        self.assertFalse((r / "60_RUNTIME/state/quittung").exists(), "Pruefer hat sich die Quittung selbst ausgestellt!")

    def test_109_alte_quittung_nach_lauf_bleibt_unbestaetigt(self):
        """RT-C CRITICAL: ein Prueferlauf darf die 7-Tage-Regel nicht umgehen."""
        import datetime
        r = baum("c2")
        status_sim.zustellen(r, "OK", True)
        alt = (datetime.datetime.now().astimezone() - datetime.timedelta(days=9)).isoformat(timespec="seconds")
        (r / "60_RUNTIME/state/quittung").write_text(f"{alt} OK quittiert zugestellt ok\n", encoding="utf-8")
        lauf(r)                                    # Pruefer laeuft FRISCH
        st, gruende = status_sim.waechter(r)
        self.assertEqual(st, "UNBESTAETIGT", gruende)

    def test_110_zustellfehler_ist_critical(self):
        """RT-C: 'zugestellt fehler' -> CRITICAL (§4.4), nicht OK."""
        r = baum("c3")
        lauf(r)
        status_sim.zustellen(r, "CRITICAL", True, zugestellt_ok=False)
        (r / "60_RUNTIME/state/waechter_herzschlag").write_text(
            status_sim.JETZT().isoformat(timespec="seconds"), encoding="utf-8")
        self.assertEqual(status_sim.waechter(r)[0], "CRITICAL")

    def test_111_sieben_tage_23_stunden_ist_zu_alt(self):
        """RT-C: '.days' schnitt ab — 7 d 23 h 59 m war faelschlich OK."""
        import datetime
        r = baum("c4")
        lauf(r)
        alt = (datetime.datetime.now().astimezone()
               - datetime.timedelta(days=7, hours=23, minutes=59)).isoformat(timespec="seconds")
        (r / "60_RUNTIME/state/quittung").write_text(f"{alt} OK quittiert zugestellt ok\n", encoding="utf-8")
        (r / "60_RUNTIME/state/waechter_herzschlag").write_text(
            status_sim.JETZT().isoformat(timespec="seconds"), encoding="utf-8")
        self.assertEqual(status_sim.waechter(r)[0], "UNBESTAETIGT")

    def test_112_beschaedigtes_protokoll_kein_absturz(self):
        """RT-C: abgeschnittene JSONL-Zeile darf den Waechter nicht toeten."""
        r = baum("c5")
        lauf(r)
        status_sim.zustellen(r, "OK", True)
        (r / "60_RUNTIME/state/zustellung_simuliert.jsonl").write_text('{"zeit": "2026", "st', encoding="utf-8")
        (r / "60_RUNTIME/state/waechter_herzschlag").write_text(
            status_sim.JETZT().isoformat(timespec="seconds"), encoding="utf-8")
        self.assertEqual(status_sim.waechter(r)[0], "UNBESTAETIGT")

    def test_113_herzschlag_nicht_schreibbar_ist_critical(self):
        """RT-C: nicht schreibbarer Herzschlag darf nicht als OK enden."""
        r = baum("c6")
        st = r / "60_RUNTIME/state"; st.mkdir(parents=True, exist_ok=True)
        os.chmod(st, 0o500)
        try:
            d, code = lauf(r)
            self.assertEqual(code, 3, d)
            self.assertEqual(d["status"], "CRITICAL")
            json.dumps(d)
        finally:
            os.chmod(st, 0o700)

    def test_114_redundanz_verlangt_archiv(self):
        """RT-C: ein leerer zweiter Ort ist NICHT 'vorhanden'."""
        import shutil as _sh
        leer = S / "tmp_unabh/redundanz_leer"
        if leer.exists(): _sh.rmtree(leer)          # idempotent: kein Rest aus vorigen Laeufen
        leer.mkdir(parents=True, exist_ok=True)
        self.assertFalse(CA._archiv_gefunden(leer))
        (leer / "notiz.txt").write_text("nur eine kleine Datei", encoding="utf-8")
        self.assertFalse(CA._archiv_gefunden(leer))
        (leer / "sicherung.tar.zst").write_bytes(b"x")
        self.assertTrue(CA._archiv_gefunden(leer))

    def test_115_herkunft_gegenproben(self):
        """RT-C: gefaelschte Herkunft (falscher SHA, erfundener Commit) muss auffallen."""
        r = baum("c7", dirs=["30_WISSEN/research/2026-09-21_w"])
        repo = r / "30_WISSEN/research/2026-09-21_w"
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        (repo / ".gitignore").write_text("", encoding="utf-8")
        (repo / "README.md").write_text("# w", encoding="utf-8")
        (repo / "ausgabe.md").write_text("inhalt", encoding="utf-8")
        (repo / "herkunft.md").write_text(
            "kopf:\n  ausgabe_sha256: " + "a" * 64 + "\n  ausgabe: ausgabe.md\n"
            "  quelle_commit: deadbee1234\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)   # K3 liest getrackte Dateien
        e = ('  - schema_version: 1\n    name: w\n    class: knowledge\n    status: active\n'
             '    owner: t\n    seit: "2026-09-21"\n    bereich: 30_WISSEN\n'
             '    pfad: 30_WISSEN/research/2026-09-21_w\n    git: true\n    review_am: "2027-09-21"\n'
             '    remote: "t/w"\n')
        (r / "00_SYSTEM/manifest/repos.yaml").write_text(
            (r / "00_SYSTEM/manifest/repos.yaml").read_text(encoding="utf-8") + e, encoding="utf-8")
        ctx = R.run_all(r, kat(r))
        meldungen = " | ".join(f["meldung"] for f in ctx.findings if f["regel"] == "K3")
        self.assertIn("passt NICHT zum Inhalt", meldungen)
        self.assertIn("existiert NICHT im Repository", meldungen)


if __name__ == "__main__":
    unittest.main(verbosity=2)

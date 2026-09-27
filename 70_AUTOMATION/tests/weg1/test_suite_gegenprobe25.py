#!/usr/bin/env python3
"""GEGENPROBE ETAPPE 2.5 — je Test ein BEFUND der unabhaengigen Runde 1 (RT-A/B/C).
Diese Datei sperrt die Korrekturen fest: faellt eine davon zurueck, faellt hier ein Test."""
from __future__ import annotations
import json, os, shutil, stat, subprocess, sys, unittest
from pathlib import Path

S = next(p for p in Path(__file__).resolve().parents if (p / "ordner.sh").is_file()).parent; M = next(p for p in Path(__file__).resolve().parents if (p / "ordner.sh").is_file())
M = next(p for p in Path(__file__).resolve().parents if (p / "ordner.sh").is_file())
for u in ("validation", "indexing", "maintenance", "cross-repo"):
    sys.path.insert(0, str(M / "70_AUTOMATION" / u))
import rules as R, indexer as IX, status_sim as SS
import adapter_readonly as AD
import budget as BU
import yaml

CHECK = M / "70_AUTOMATION/validation/check_all.py"
B = S / "tmp_gegen"


def baum(name, dirs=(), kat="schema_version: 1\nnotfallkontakt: \"x\"\npassphrase_ort: \"k\"\nrepos: []\n"):
    r = B / name
    if r.exists(): shutil.rmtree(r, ignore_errors=True)
    (r / "00_SYSTEM/manifest").mkdir(parents=True); (r / "00_SYSTEM/schemas").mkdir(parents=True)
    (r / "40_DATEN/pointers").mkdir(parents=True)
    shutil.copy(M / "00_SYSTEM/schemas/repos.schema.json", r / "00_SYSTEM/schemas/repos.schema.json")
    (r / "00_SYSTEM/manifest/repos.yaml").write_text(kat, encoding="utf-8")
    for d in dirs: (r / d).mkdir(parents=True, exist_ok=True)
    return r


def lauf(r, timeout=180):
    """Prueferlauf. Ein Haenger (FIFO) oder Traceback (Exit 1) ist ein Fehler."""
    try:
        x = subprocess.run([sys.executable, str(CHECK), "--root", str(r), "--json", "--no-selftest"],
                           capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"status": "HAENGER"}, -1
    if x.returncode == 1:                        # Traceback = Absturz
        return {"status": "ABSTURZ", "stderr": x.stderr[-300:]}, 1
    try: return json.loads(x.stdout), x.returncode
    except Exception: return {"status": "KEIN-STATUS", "stdout": x.stdout[-200:]}, x.returncode


def git(cwd, *a, env=None):
    return subprocess.run(["git", "-C", str(cwd), *a], capture_output=True, text=True,
                          env=env or {"PATH": "/usr/bin:/bin", "HOME": "/tmp"})


# ============ C1 — Eingaben, die den Pruefer getoetet haben ============
class T_C1_Absturz(unittest.TestCase):
    def _kein_absturz(self, r, name):
        d, code = lauf(r)
        self.assertNotIn(d.get("status"), ("ABSTURZ", "HAENGER", "KEIN-STATUS"), f"{name}: {d}")
        self.assertNotEqual(code, 1, f"{name}: Exit 1 (Traceback) statt Meldung")
        self.assertIn(d.get("status"), ("OK", "WARNING", "ERROR", "CRITICAL", "UNBESTAETIGT"), f"{name}: {d}")

    def test_200_katalog_skalar_liste_zahl(self):
        for i, kat in enumerate(["nurtext\n", "- a\n- b\n", "repos: 5\n", "repos: true\n", "a:\tb\n"]):
            r = baum(f"c1_{i}", kat=kat); self._kein_absturz(r, f"Katalog {kat[:12]!r}")

    def test_201_katalog_nicht_utf8(self):
        r = baum("c1_utf8"); (r / "00_SYSTEM/manifest/repos.yaml").write_bytes(b"repos: [\xff\xfe]\n")
        self._kein_absturz(r, "Katalog nicht UTF-8")

    def test_202_katalog_verzeichnis_und_fifo(self):
        r = baum("c1_dir"); (r / "00_SYSTEM/manifest/repos.yaml").unlink()
        (r / "00_SYSTEM/manifest/repos.yaml").mkdir(); self._kein_absturz(r, "Katalog als Verzeichnis")
        r = baum("c1_fifo"); (r / "00_SYSTEM/manifest/repos.yaml").unlink()
        os.mkfifo(r / "00_SYSTEM/manifest/repos.yaml"); self._kein_absturz(r, "Katalog als FIFO")

    def test_203_zeiger_fifo_und_typ(self):
        for i, art in enumerate(["fifo", "dir", "null", "liste", "zahl"]):
            r = baum(f"c1z_{i}"); z = r / "40_DATEN/pointers/z.yaml"
            if art == "fifo": os.mkfifo(z)
            elif art == "dir": z.mkdir()
            elif art == "null": z.write_text("null", encoding="utf-8")
            elif art == "liste": z.write_text("- a\n- b\n", encoding="utf-8")
            else: z.write_text("42", encoding="utf-8")
            self._kein_absturz(r, f"Zeiger {art}")

    def test_204_schema_kaputt(self):
        for i, roh in enumerate([b"{{{", b"\xff\xfe kaputt"]):
            r = baum(f"c1s_{i}")
            (r / "00_SYSTEM/schemas/repos.schema.json").write_bytes(roh)   # auch Nicht-UTF8
            self._kein_absturz(r, "Schema kaputt")


# ============ C2 — stille Secret-Blindstellen ============
class T_C2_Secret(unittest.TestCase):
    def test_210_nicht_utf8_dateiname_wird_geprueft(self):
        """Ein nicht-UTF8-Dateiname wurde durch errors=replace VERFAELSCHT -> still ungeprueft."""
        r = baum("c2_utf8", dirs=["20_PROJEKTE/p"]); repo = r / "20_PROJEKTE/p"
        git(r / "20_PROJEKTE", "init", "-q", str(repo))
        p = repo / os.fsdecode(b"datei_\xff.md")          # echter Nicht-UTF8-Name (Bytes)
        p.write_bytes(b"harmlos")
        git(repo, "add", "-A")
        dateien = R.git_ls_files(repo)
        self.assertIn(os.fsdecode(b"datei_\xff.md"), dateien, f"Nicht-UTF8-Name verfaelscht: {dateien}")
        self.assertTrue(p.exists(), "der erfasste Pfad muss existieren")
        self.assertGreater(R.run_all(r, {"repos": []}).geprueft, 0)

    def test_211_repo_unter_unlesbarem_ordner_wird_gemeldet(self):
        r = baum("c2_rechte", dirs=["20_PROJEKTE"]); repo = r / "20_PROJEKTE/p"
        repo.mkdir(); git(r / "20_PROJEKTE", "init", "-q", str(repo))
        os.chmod(repo, 0o000)
        try:
            b, u, g = R.entdecke_git(r)
            ctx = R.run_all(r, {"repos": []})
            ab = ctx.abdeckung
            gemeldet = bool(u) or ab.get("ungeprueft", 0) > 0 or any("nicht lesbar" in f["meldung"] for f in ctx.findings)
            self.assertTrue(gemeldet, "unlesbarer Ordner blieb still ungeprueft")
        finally:
            os.chmod(repo, 0o755)


# ============ C4/C5/C6 — Kollisionen, Herkunft, Budget ============
class T_C4_C5_C6(unittest.TestCase):
    def test_220_nfc_nfd_kollision(self):
        import unicodedata
        r = baum("c4", dirs=["30_WISSEN"])
        a = "Cafe\u0301.md"                       # NFD
        b = unicodedata.normalize("NFC", a)        # NFC
        (r / "30_WISSEN" / a).write_text("1", encoding="utf-8")
        (r / "30_WISSEN" / b).write_text("2", encoding="utf-8")
        ctx = R.run_all(r, {"repos": []})
        self.assertTrue([f for f in ctx.findings if "Kollision" in f["meldung"]],
                        "NFC/NFD-Kollision blieb unentdeckt")

    def test_221_herkunft_pflichtangaben(self):
        r = baum("c5", dirs=["30_WISSEN/w"]); repo = r / "30_WISSEN/w"
        git(r / "30_WISSEN", "init", "-q", str(repo))
        # Die Herkunfts-Gegenproben laufen NUR fuer katalogisierte Repositories.
        (r / "00_SYSTEM/manifest/repos.yaml").write_text(
            'schema_version: 1\nnotfallkontakt: "x"\npassphrase_ort: "k"\nrepos:\n'
            '  - schema_version: 1\n    name: w\n    class: knowledge\n    status: active\n'
            '    owner: t\n    seit: "2026-09-21"\n    bereich: 30_WISSEN\n'
            '    pfad: 30_WISSEN/w\n    git: true\n', encoding="utf-8")
        kat = yaml.safe_load((r / "00_SYSTEM/manifest/repos.yaml").read_text(encoding="utf-8"))
        (repo / "h.md").write_text("kopf:\n  ausgabe_sha256: " + "a" * 64 + "\n", encoding="utf-8")
        git(repo, "add", "-A")
        ctx = R.run_all(r, kat)
        self.assertIn("ohne Zieldatei", " ".join(f["meldung"] for f in ctx.findings))
        (repo / "h2.md").write_text("kopf:\n  quelle_commit: keinhash\n", encoding="utf-8")
        git(repo, "add", "-A")
        self.assertIn("kein Commit-Hash", " ".join(f["meldung"] for f in R.run_all(r, kat).findings))
        (repo / "h3.md").write_text("kopf:\n  Quelle-Commit: deadbee1234\n", encoding="utf-8")
        git(repo, "add", "-A")
        self.assertIn("existiert NICHT", " ".join(f["meldung"] for f in R.run_all(r, kat).findings))

    def test_222_budget_symlinkkette_und_datei(self):
        r = baum("c6", dirs=["30_WISSEN/ziel"])
        gross = r / "30_WISSEN/ziel/gross.bin"; gross.write_bytes(b"x" * (5 << 20))
        (r / "40_DATEN/pointers/verweis.dat").symlink_to(gross)
        w = BU.pruefe(r)
        self.assertEqual(w["status"], "FAIL", f"Symlink-Kette nicht gezaehlt: {w}")
        r2 = baum("c6b"); shutil.rmtree(r2 / "40_DATEN"); (r2 / "40_DATEN").write_bytes(b"x" * (5 << 20))
        w2 = BU.pruefe(r2)
        self.assertEqual(w2["status"], "FAIL", "40_DATEN als DATEI wurde als PASS gemeldet")


# ============ B — Sandkasten, Git-Fremdcode, Adapter, Fingerabdruck ============
class T_B_Isolation(unittest.TestCase):
    def test_230_geschwisterordner_wird_verweigert(self):
        """startswith(str(SANDBOX)) liess 'prototyp_git_ordner_SIBLING' durch."""
        sib = Path.home() / "prototyp_git_ordner_SIBLING"
        shutil.rmtree(sib, ignore_errors=True)
        self.assertFalse(R.ist_im_baum(sib, next(p for p in Path(__file__).resolve().parents if (p / "ordner.sh").is_file()).parent),
                         "Geschwisterordner gilt als Sandkasten!")
        sib.mkdir(); (sib / "00_SYSTEM/manifest").mkdir(parents=True)
        # FIXTURE (nicht Pruefgegenstand): der Geschwisterordner liegt AUSSERHALB der Sandbox und die
        # (korrekte!) fd-Boundary lehnt open() dort ab. Fixture daher per os-Primitiven —
        # der Pruefgegenstand (Scan/Write dort wird verweigert) bleibt unveraendert.
        _fd = os.open(str(sib / "00_SYSTEM/manifest/repos.yaml"),
                      os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o644)
        os.write(_fd, b"repos: []\n")
        os.close(_fd)
        try:
            x = subprocess.run([sys.executable, str(CHECK), "--root", str(sib), "--json", "--no-selftest"],
                               capture_output=True, text=True)
            self.assertEqual(x.returncode, 3, "Pruefer lief im Geschwisterordner!")
            self.assertFalse((sib / "60_RUNTIME/state").exists(), "Ausserhalb der Sandbox geschrieben!")
        finally:
            shutil.rmtree(sib, ignore_errors=True)

    def test_231_symlink_zustand_schreibt_nicht_nach_draussen(self):
        ziel = Path("/tmp/rt25_sym_aussen"); shutil.rmtree(ziel, ignore_errors=True); ziel.mkdir(parents=True)
        r = baum("b_sym"); (r / "60_RUNTIME").mkdir(parents=True)
        (r / "60_RUNTIME/state").symlink_to(ziel)
        erg = SS.zustellen(r, "OK", True)
        self.assertEqual(erg.get("zugestellt"), "verweigert", erg)
        self.assertEqual(SS.waechter(r)[0], "CRITICAL")
        self.assertEqual(list(ziel.iterdir()), [], "Es wurde AUSSERHALB geschrieben!")
        shutil.rmtree(ziel, ignore_errors=True)

    def test_232_repo_fremdcode_fsmonitor(self):
        """Ein Repo mit core.fsmonitor durfte beliebigen Code ausfuehren (CRITICAL der Runde 1)."""
        r = baum("b_fsmon", dirs=["20_PROJEKTE/p"]); repo = r / "20_PROJEKTE/p"
        git(r / "20_PROJEKTE", "init", "-q", str(repo))
        (repo / "a.txt").write_text("a", encoding="utf-8"); git(repo, "add", "-A")
        marker = B / "fsmon_marker"; marker.unlink(missing_ok=True)
        payload = B / "payload.sh"; payload.write_text(f"#!/bin/sh\ntouch {marker}\necho 0\n", encoding="utf-8")
        payload.chmod(0o755)
        git(repo, "config", "core.fsmonitor", str(payload))
        R.git_ls_files(repo); AD.git(repo, "ls-files")
        self.assertFalse(marker.exists(), "Fremdcode wurde ausgefuehrt!")
        lauf(r, timeout=120)
        self.assertFalse(marker.exists(), "Fremdcode wurde im vollen Prueferlauf ausgefuehrt!")

    def test_233_adapter_umgebung_und_allowlist(self):
        r = baum("b_env", dirs=["20_PROJEKTE/p"]); repo = r / "20_PROJEKTE/p"
        git(r / "20_PROJEKTE", "init", "-q", str(repo)); (repo / "a.txt").write_text("a", encoding="utf-8")
        trace = B / "git_trace.log"; trace.unlink(missing_ok=True)
        os.environ["GIT_TRACE"] = str(trace)
        try: AD.git(repo, "ls-files")
        finally: os.environ.pop("GIT_TRACE", None)
        self.assertFalse(trace.exists(), "GIT_TRACE wurde durchgereicht — git legte eine Datei an!")
        with self.assertRaises(AssertionError):
            AD.git(repo, "log", "--output=" + str(B / "boese.txt"), "-1")

    def test_234_fingerabdruck_sieht_inhalt(self):
        r = baum("b_fp", dirs=["20_PROJEKTE/p"]); repo = r / "20_PROJEKTE/p"
        git(r / "20_PROJEKTE", "init", "-q", str(repo))
        f = repo / "data.txt"; f.write_text("A", encoding="utf-8")
        vorher = AD.fingerabdruck(repo)["tree_hash"]
        m = f.stat().st_mtime_ns
        f.write_text("B", encoding="utf-8"); os.utime(f, ns=(m, m))     # mtime restauriert
        self.assertNotEqual(AD.fingerabdruck(repo)["tree_hash"], vorher,
                            "Fingerabdruck war BLIND fuer Inhalt bei gleicher mtime")

    def test_235_hardlink_wird_verweigert(self):
        r = baum("b_hl", dirs=["20_PROJEKTE/p"]); repo = r / "20_PROJEKTE/p"
        git(r / "20_PROJEKTE", "init", "-q", str(repo))
        aussen = B / "geheim.txt"; aussen.write_text("GEHEIM", encoding="utf-8")
        link = repo / "README.md"; os.link(aussen, link)
        self.assertFalse(AD.im_repo(link, repo), "Hardlink auf Datei ausserhalb wurde akzeptiert")

    def test_236_grosse_datei_unter_git_kein_memoryerror(self):
        r = baum("b_gross", dirs=["20_PROJEKTE/p"]); repo = r / "20_PROJEKTE/p"
        git(r / "20_PROJEKTE", "init", "-q", str(repo))
        gross = repo / ".git/gross.bin"
        with gross.open("wb") as fh: fh.truncate(1 << 30)          # sparse 1 GB
        fp = AD.fingerabdruck(repo)                                 # darf NICHT sterben
        self.assertIn("git_hash", fp)
        self.assertGreaterEqual(fp.get("git_grosse_dateien", 0), 1)


# ============ A — Waechter/Beweise ============
class T_A_Waechter(unittest.TestCase):
    def _r(self, name):
        r = baum(name); SS.lief(r); return r

    def test_240_statusdatei_fehlt_oder_unbekannt(self):
        for art in ("fehlt", "LAUFEND", "QUATSCH", "", "ok"):
            r = self._r("a_" + (art or "leer")); SS.zustellen(r, "OK", True); SS.waechter_lauf(r)
            sp = r / "60_RUNTIME/state/status.json"
            if art == "fehlt": sp.unlink()
            else: sp.write_text(json.dumps({"status": art}), encoding="utf-8")
            self.assertEqual(SS.waechter(r)[0], "UNBESTAETIGT", f"Status {art!r} ergab nicht UNBESTAETIGT")

    def test_241_statusdatei_kaputte_typen(self):
        for roh in ("null", "[]", "42", '{"status": null}'):
            r = self._r("a_typ"); SS.zustellen(r, "OK", True); SS.waechter_lauf(r)
            (r / "60_RUNTIME/state/status.json").write_text(roh, encoding="utf-8")
            self.assertEqual(SS.waechter(r)[0], "UNBESTAETIGT", f"{roh} ergab nicht UNBESTAETIGT")

    def test_242_beschaedigte_beweise_kein_absturz(self):
        r = self._r("a_besch"); SS.zustellen(r, "OK", True); SS.waechter_lauf(r)
        (r / "60_RUNTIME/state/quittung").write_bytes(b"\xff\xfe kaputt\x00")
        self.assertEqual(SS.waechter(r)[0], "UNBESTAETIGT")
        q = r / "60_RUNTIME/state/quittung"; q.unlink(); q.mkdir()
        self.assertEqual(SS.waechter(r)[0], "UNBESTAETIGT")
        zl = r / "60_RUNTIME/state/zustellung_simuliert.jsonl"; zl.unlink(missing_ok=True); zl.mkdir()
        self.assertEqual(SS.waechter(r)[0], "UNBESTAETIGT")

    def test_243_protokoll_ohne_leserecht(self):
        r = self._r("a_rechte"); SS.zustellen(r, "OK", True); SS.waechter_lauf(r)
        zl = r / "60_RUNTIME/state/zustellung_simuliert.jsonl"; os.chmod(zl, 0o000)
        try: self.assertEqual(SS.waechter(r)[0], "UNBESTAETIGT")
        finally: os.chmod(zl, 0o600)

    def test_244_pruefer_nicht_startbar_kein_traceback(self):
        alt = SS.CHECK
        SS.CHECK = Path("/gibt/es/nicht.py")
        try: self.assertEqual(SS.lief(B / "nirgends")["status"], "CRITICAL")
        finally: SS.CHECK = alt


# ============ Index — Frische, Symlink, WAL ============
class T_Index_25(unittest.TestCase):
    def _baum(self, name):
        r = baum(name, dirs=["20_PROJEKTE/p"])
        (r / "20_PROJEKTE/p/notiz.md").write_text("inhalt", encoding="utf-8")
        return r

    def test_250_frische_erkennt_inhalt_trotz_mtime(self):
        r = self._baum("i_frisch"); f = r / "20_PROJEKTE/p/notiz.md"
        IX.build(r, still=True)
        self.assertEqual(IX.status(r)["veraltet_gegenueber_quellen"], "nein")
        m = f.stat().st_mtime_ns; f.write_text("GEAENDERT", encoding="utf-8"); os.utime(f, ns=(m, m))
        self.assertEqual(IX.status(r)["veraltet_gegenueber_quellen"], "ja")
        IX.build(r, still=True)
        self.assertEqual(IX.status(r)["veraltet_gegenueber_quellen"], "nein")

    def test_251_zurueckdatierte_neue_datei(self):
        r = self._baum("i_zurueck"); IX.build(r, still=True)
        alt = (r / "20_PROJEKTE/p/notiz.md").stat().st_mtime_ns
        n = r / "20_PROJEKTE/p/zurueck.md"; n.write_text("z", encoding="utf-8")
        os.utime(n, ns=(alt - 10 ** 12, alt - 10 ** 12))
        self.assertEqual(IX.status(r)["veraltet_gegenueber_quellen"], "ja")

    def test_252_symlink_ziel_nicht_im_index(self):
        r = self._baum("i_sym")
        aussen = B / "geheim_i.txt"; aussen.write_text("GEHEIMER-INHALT-XYZ", encoding="utf-8")
        (r / "20_PROJEKTE/p/verweis.md").symlink_to(aussen)
        IX.build(r, still=True)
        treffer, _ = IX.search(r, "GEHEIMER")
        self.assertEqual(treffer, [], "Symlink-Ziel wurde in den Index kopiert!")

    def test_253_wal_index_lesbar_ohne_neue_dateien(self):
        import sqlite3
        r = self._baum("i_wal"); IX.build(r, still=True)
        d = IX.index_pfad(r).parent
        v = sqlite3.connect(str(IX.index_pfad(r))); v.execute("PRAGMA journal_mode=WAL"); v.close()
        os.chmod(d, 0o500)
        try:
            treffer, fehler = IX.search(r, "inhalt")
            self.assertTrue(treffer or fehler is None, f"Suche scheiterte: {fehler}")
            self.assertEqual(sorted(p.name for p in d.iterdir()), ["suche.db", "suche.db.lock"],
                             "search legte -wal/-shm an")
        finally:
            os.chmod(d, 0o700)


if __name__ == "__main__":
    unittest.main(verbosity=2)

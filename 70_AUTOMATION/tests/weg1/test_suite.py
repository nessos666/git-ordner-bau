#!/usr/bin/env python3
"""Testsuite des Prototyps (Etappe 1) — reproduzierbar, ohne Netz, nur im Sandkasten.
Aufruf: python3 test_suite.py     (oder: python3 -m unittest test_suite -v)
"""
from __future__ import annotations
import os, sys, shutil, subprocess, tempfile, unittest
from pathlib import Path
import yaml

S = next(p for p in Path(__file__).resolve().parents if (p / "ordner.sh").is_file()).parent; M = next(p for p in Path(__file__).resolve().parents if (p / "ordner.sh").is_file())
M = next(p for p in Path(__file__).resolve().parents if (p / "ordner.sh").is_file())
TMPROOT = S / "tmp_tests"
TMPROOT.mkdir(exist_ok=True)
sys.path.insert(0, str(M / "70_AUTOMATION/validation"))
import rules as R
import schema_check


SANDBOX = next(p for p in Path(__file__).resolve().parents if (p / "ordner.sh").is_file()).parent


def nur_sandkasten(p) -> Path:
    """Waechter: jede schreibende/loeschende Operation MUSS in der Sandbox liegen."""
    p = Path(p)
    if str(p).startswith(str(SANDBOX) + "/") or p == SANDBOX:
        return p
    raise AssertionError(f"AUSSERHALB DER SANDBOX — verweigert: {p}")

SCH = (M / "00_SYSTEM/schemas/repos.schema.json").read_text(encoding="utf-8")
GI = ".venv/\ncache/\n*.log\n"


def eintrag(name, **kw):
    d = {"schema_version": 1, "name": name, "class": "project", "status": "active",
         "owner": "t", "seit": "2026-09-21", "bereich": "20_PROJEKTE",
         "pfad": f"20_PROJEKTE/{name}", "git": False, "review_am": "2027-09-21"}
    if "klasse" in kw: d["class"] = kw.pop("klasse")
    d.update(kw)
    return d


class Basis(unittest.TestCase):
    def tree(self, eintraege, dirs=(), files=(), repos=(), katalog_text=None, create_paths=True):
        root = Path(tempfile.mkdtemp(dir=TMPROOT))
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        (root / "00_SYSTEM/manifest").mkdir(parents=True)
        (root / "00_SYSTEM/schemas").mkdir(parents=True)
        (root / "00_SYSTEM/schemas/repos.schema.json").write_text(SCH, encoding="utf-8")
        if katalog_text is None:
            katalog_text = yaml.safe_dump({"schema_version": 1, "notfallkontakt": "t", "passphrase_ort": "keine",
                                           "repos": eintraege}, allow_unicode=True, sort_keys=False)
        (root / "00_SYSTEM/manifest/repos.yaml").write_text(katalog_text, encoding="utf-8")
        for d in list(dirs) + (["40_DATEN/pointers"] if create_paths else []):
            (root / d).mkdir(parents=True, exist_ok=True)
        if create_paths:   # ein Katalogeintrag ohne existierenden Pfad ist ein K4-Fehler
            for e in eintraege:
                if isinstance(e, dict) and e.get("pfad") and not e["pfad"].endswith((".yaml", ".yml")):
                    (root / e["pfad"]).mkdir(parents=True, exist_ok=True)
        for f, c in files:
            p = root / f; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(c, encoding="utf-8")
        for r in repos:
            p = root / r; p.mkdir(parents=True, exist_ok=True)
            (p / "README.md").write_text("# r\n", encoding="utf-8")
            (p / ".gitignore").write_text(GI, encoding="utf-8")
            subprocess.run(["git", "init", "-q", "-b", "main"], cwd=p, capture_output=True)
            subprocess.run(["git", "config", "user.email", "t@l"], cwd=p, capture_output=True)
            subprocess.run(["git", "config", "user.name", "T"], cwd=p, capture_output=True)
            subprocess.run(["git", "add", "-A"], cwd=p, capture_output=True)
            subprocess.run(["git", "commit", "-q", "-m", "t"], cwd=p, capture_output=True)
        return root

    def regeln(self, root, kat=None):
        if kat is None:
            try:
                kat = yaml.safe_load((root / "00_SYSTEM/manifest/repos.yaml").read_text(encoding="utf-8")) or {}
            except Exception:
                kat = {}
        return R.run_all(root, kat)

    def hat(self, ctx, regel, schwere=None):
        return any(f["regel"] == regel and (schwere is None or f["schwere"] == schwere) for f in ctx.findings)


# ---------------------------------------------------------------- Katalog / Schema
class T_Katalog(Basis):
    def test_01_gueltiger_katalog(self):
        ctx = self.regeln(self.tree([eintrag("2026-09-21_a", pfad="20_PROJEKTE/2026-09-21_a")]))
        self.assertEqual([f for f in ctx.findings if f["regel"] != "SELFTEST"], [])

    def test_02_katalog_kaputt(self):
        r = self.tree([], katalog_text="schema_version: 1\nrepos: [{name: x}]\n")
        ctx = self.regeln(r)
        self.assertTrue(self.hat(ctx, "K5") or self.hat(ctx, "SCHEMA"))

    def test_03_schema_prueft_pflichtfelder(self):
        r = self.tree([{"schema_version": 1, "name": "x"}])
        fehler, backend = schema_check.pruefe(r)
        self.assertTrue(any("Pflichtfeld" in f or "required" in f for f in fehler))

    def test_04_doppelter_name(self):
        ctx = self.regeln(self.tree([eintrag("doppelt", pfad="20_PROJEKTE/a"), eintrag("doppelt", pfad="20_PROJEKTE/b")]))
        self.assertTrue(self.hat(ctx, "K5", "ERROR"))

    def test_05_doppelter_pfad(self):
        ctx = self.regeln(self.tree([eintrag("a", pfad="20_PROJEKTE/x"), eintrag("b", pfad="20_PROJEKTE/x")]))
        self.assertTrue(self.hat(ctx, "K5", "ERROR"))

    def test_06_falscher_status(self):
        ctx = self.regeln(self.tree([eintrag("a", status="aktiv", pfad="20_PROJEKTE/a")]))
        self.assertTrue(self.hat(ctx, "K5", "ERROR"))

    def test_07_schema_version_fehlt(self):
        e = eintrag("a", pfad="20_PROJEKTE/a"); del e["schema_version"]
        ctx = self.regeln(self.tree([e]))
        self.assertTrue(self.hat(ctx, "K5", "ERROR"))


# ---------------------------------------------------------------- K4 Realität
class T_Realitaet(Basis):
    def test_08_falsche_klasse_fuer_bereich(self):
        ctx = self.regeln(self.tree([eintrag("a", klasse="project", pfad="30_WISSEN/a", bereich="30_WISSEN")]))
        self.assertTrue(self.hat(ctx, "K4", "ERROR"))

    def test_09_fehlender_pfad_ist_critical(self):
        ctx = self.regeln(self.tree([eintrag("2026-09-21_a", pfad="20_PROJEKTE/gibtsnicht")], create_paths=False))
        self.assertTrue(self.hat(ctx, "K4", "CRITICAL"))

    def test_10_repo_ohne_katalogeintrag(self):
        ctx = self.regeln(self.tree([], repos=["20_PROJEKTE/waisenkind"]))
        self.assertTrue(self.hat(ctx, "K4", "ERROR"))

    def test_11_git_true_ohne_repo(self):
        ctx = self.regeln(self.tree([eintrag("a", git=True, remote="t/a", pfad="20_PROJEKTE/a", review_am="2027-09-21")],
                                    dirs=["20_PROJEKTE/a"]))
        self.assertTrue(self.hat(ctx, "K4", "ERROR"))

    def test_12_extern_ohne_pin(self):
        ctx = self.regeln(self.tree([eintrag("a", extern=True, git=False, pfad="20_PROJEKTE/a")]))
        self.assertTrue(self.hat(ctx, "K4", "ERROR"))

    def test_13_eigenes_repo_mit_unnuetzen_pin(self):
        ctx = self.regeln(self.tree([eintrag("a", pin="0" * 40, pfad="20_PROJEKTE/a")]))
        self.assertTrue(self.hat(ctx, "K4", "ERROR"))

    def test_14_bootstrap_provisional_ok(self):
        e = {"schema_version": 1, "name": "2026-09-21_neu", "class": "project", "status": "provisional",
             "owner": "t", "seit": "2026-09-21", "bereich": "20_PROJEKTE", "pfad": "20_PROJEKTE/2026-09-21_neu", "git": False}
        ctx = self.regeln(self.tree([e], dirs=["20_PROJEKTE/2026-09-21_neu"]))
        self.assertEqual([f for f in ctx.findings if f["regel"] != "SELFTEST"], [])

    def test_15_active_ohne_review(self):
        e = eintrag("2026-09-21_a"); e.pop("review_am")
        ctx = self.regeln(self.tree([e]))
        self.assertTrue(self.hat(ctx, "K5", "ERROR"))


# ---------------------------------------------------------------- K1/K2/K3
class T_Inhalt(Basis):
    def test_16_grosse_datei_im_repo(self):
        r = self.tree([eintrag("a", git=True, remote="t/a", pfad="20_PROJEKTE/a", review_am="2027-09-21")],
                      repos=["20_PROJEKTE/a"])
        with open(r / "20_PROJEKTE/a/gross.bin", "wb") as fh: fh.truncate(12 * 1024 * 1024)
        subprocess.run(["git", "add", "-A"], cwd=r / "20_PROJEKTE/a", capture_output=True)
        subprocess.run(["git", "commit", "-q", "-m", "gross"], cwd=r / "20_PROJEKTE/a", capture_output=True)
        ctx = self.regeln(r)
        self.assertTrue(self.hat(ctx, "K1", "ERROR"))

    def test_17_cache_im_repo(self):
        r = self.tree([], repos=["20_PROJEKTE/a"], dirs=["20_PROJEKTE/a/cache"],
                      files=[("20_PROJEKTE/a/cache/x.txt", "c")])
        subprocess.run(["git", "add", "-f", "-A"], cwd=r / "20_PROJEKTE/a", capture_output=True)
        subprocess.run(["git", "commit", "-q", "-m", "c"], cwd=r / "20_PROJEKTE/a", capture_output=True)
        ctx = self.regeln(r)
        self.assertTrue(self.hat(ctx, "K1"))

    def test_18_secret_ist_critical_mit_reaktionskette(self):
        r = self.tree([], repos=["20_PROJEKTE/a"])
        (r / "20_PROJEKTE/a/config.md").write_text("api_key = " + "sk-" + "ABCDEFGHIJKLMNOPQRSTUVWX1234" + "\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=r / "20_PROJEKTE/a", capture_output=True)
        subprocess.run(["git", "commit", "-q", "-m", "s"], cwd=r / "20_PROJEKTE/a", capture_output=True)
        ctx = self.regeln(r)
        self.assertTrue(self.hat(ctx, "K2", "CRITICAL"))
        self.assertIn("rotieren", " ".join(f["meldung"] for f in ctx.findings if f["regel"] == "K2"))

    def test_19_harmloser_inhalt(self):
        r = self.tree([], repos=["20_PROJEKTE/a"], files=[("20_PROJEKTE/a/notiz.md", "harmlos, kein Schluessel\n")])
        subprocess.run(["git", "add", "-A"], cwd=r / "20_PROJEKTE/a", capture_output=True)
        subprocess.run(["git", "commit", "-q", "-m", "h"], cwd=r / "20_PROJEKTE/a", capture_output=True)
        self.assertFalse(self.hat(self.regeln(r), "K2"))

    def test_20_repo_ohne_gitignore(self):
        r = self.tree([eintrag("a", git=True, remote="t/a", pfad="20_PROJEKTE/a", review_am="2027-09-21")],
                      repos=["20_PROJEKTE/a"])
        (nur_sandkasten(r / "20_PROJEKTE/a/.gitignore")).unlink()
        subprocess.run(["git", "add", "-A"], cwd=r / "20_PROJEKTE/a", capture_output=True)
        subprocess.run(["git", "commit", "-q", "-m", "x"], cwd=r / "20_PROJEKTE/a", capture_output=True)
        self.assertTrue(self.hat(self.regeln(r), "K3"))

    def test_21_aktives_projekt_ohne_status(self):
        r = self.tree([eintrag("a", git=True, remote="t/a", pfad="20_PROJEKTE/a", review_am="2027-09-21")],
                      repos=["20_PROJEKTE/a"])
        self.assertTrue(self.hat(self.regeln(r), "K3"))

    def test_22_wissensartefakt_ohne_herkunft(self):
        e = eintrag("a", klasse="knowledge", bereich="30_WISSEN", pfad="30_WISSEN/a",
                    git=True, remote="t/a", review_am="2027-09-21")
        r = self.tree([e], repos=["30_WISSEN/a"])
        ctx = self.regeln(r)
        self.assertTrue(any(f["regel"] == "K3" and "Herkunft" in f["meldung"] for f in ctx.findings))


# ---------------------------------------------------------------- K6/K7
class T_Topologie(Basis):
    def test_23_tiefe_6_ist_verstoss(self):
        r = self.tree([], dirs=["20_PROJEKTE/domains/thema/projekt/01_input/details"])
        self.assertTrue(self.hat(self.regeln(r), "K7", "ERROR"))

    def test_24_tiefe_5_ist_erlaubt(self):
        r = self.tree([], dirs=["20_PROJEKTE/domains/thema/projekt/01_input"])
        self.assertFalse(self.hat(self.regeln(r), "K7", "ERROR"))

    def test_25_breite_21_ist_verstoss(self):
        r = self.tree([], dirs=[f"20_PROJEKTE/p{i:02d}" for i in range(21)])
        self.assertTrue(self.hat(self.regeln(r), "K7", "ERROR"))

    def test_26_nodes_darf_breit_sein(self):
        r = self.tree([], dirs=[f"50_INFRA/nodes/gruppe/{i:03d}" for i in range(30)])
        self.assertFalse(self.hat(self.regeln(r), "K7", "ERROR"))

    def test_27_namensgleicher_nodes_ordner_ist_keine_ausnahme(self):
        r = self.tree([], dirs=[f"20_PROJEKTE/nodes/{i:03d}" for i in range(25)])
        self.assertTrue(self.hat(self.regeln(r), "K7", "ERROR"))

    def test_28_case_kollision(self):
        r = self.tree([], dirs=["20_PROJEKTE/Projekt", "20_PROJEKTE/projekt"])
        self.assertTrue(self.hat(self.regeln(r), "K6", "ERROR"))

    def test_29_pfad_zu_lang(self):
        lang = "20_PROJEKTE/" + "x" * 260
        ctx = self.regeln(self.tree([eintrag("2026-09-21_a", pfad=lang)], create_paths=False))
        self.assertTrue(self.hat(ctx, "K6", "ERROR"))

    def test_30_versteckte_ordner_zaehlen_mit(self):
        r = self.tree([], dirs=["20_PROJEKTE/domains/thema/projekt/.versteckt/tiefer"])
        self.assertTrue(self.hat(self.regeln(r), "K7", "ERROR"))


# ---------------------------------------------------------------- K8
class T_Daten(Basis):
    def test_31_objekt_unter_10mb_ohne_pruefsumme_ok(self):
        # Ziel muss EXISTIEREN, sonst misst der Test die neue Zeiger-Pruefung (A) statt der 10-MB-Regel.
        r = self.tree([], files=[("40_DATEN/ziel.bin", "x" * 100)])
        (r / "40_DATEN/pointers/p.yaml").write_text(
            "schema_version: 1\nzeiger:\n  - typ: objekt\n    name: k\n"
            f"    ziel: {r}/40_DATEN/ziel.bin\n    groesse: 100\n    sha256: ''\n"
            "    datum: 2026-09-21\n    rekonstruktion: r\n", encoding="utf-8")
        self.assertFalse([f for f in self.regeln(r).findings if f["regel"] == "K8"])

    def test_32_objekt_ueber_10mb_ohne_sha(self):
        # Ein echtes 20-MB-Objekt (duenn belegt), damit GENAU die 10-MB-Regel greift:
        r = self.tree([], files=[("40_DATEN/gross.bin", "x")])
        with open(r / "40_DATEN/gross.bin", "r+b") as fh: fh.truncate(20 * 1024 * 1024)
        (r / "40_DATEN/pointers/p.yaml").write_text(
            "schema_version: 1\nzeiger:\n  - typ: objekt\n    name: g\n"
            f"    ziel: {r}/40_DATEN/gross.bin\n    groesse: 20000000\n    sha256: ''\n"
            "    datum: 2026-09-21\n    rekonstruktion: r\n", encoding="utf-8")
        self.assertTrue(self.hat(self.regeln(r), "K8", "ERROR"))

    def test_33_aggregation_datensatz_mit_manifest_ok(self):
        import tempfile
        ds = Path(tempfile.mkdtemp(dir=TMPROOT)); self.addCleanup(shutil.rmtree, ds, ignore_errors=True)
        (ds / "manifest.yaml").write_text("datensatz: ds\n", encoding="utf-8")
        r = self.tree([], files=[("40_DATEN/pointers/p.yaml",
            "schema_version: 1\nzeiger:\n  - typ: datensatz\n    name: ds\n    ziel: %s\n    manifest: manifest.yaml\n    groesse: 20000000\n    sha256: '%s'\n    datum: 2026-09-21\n    rekonstruktion: r\n" % (str(ds), "a" * 64))])
        self.assertFalse([f for f in self.regeln(r).findings if f["regel"] == "K8"])

    def test_34_datensatz_ohne_manifest(self):
        r = self.tree([], files=[("40_DATEN/pointers/p.yaml",
            "schema_version: 1\nzeiger:\n  - typ: datensatz\n    name: ds\n    ziel: /gibtsnicht\n    manifest: manifest.yaml\n    groesse: 5\n    sha256: '%s'\n    datum: 2026-09-21\n    rekonstruktion: r\n" % ("b" * 64))])
        self.assertTrue(self.hat(self.regeln(r), "K8", "ERROR"))

    def test_35_40_daten_zu_gross(self):
        r = self.tree([], files=[("40_DATEN/ballast.bin", "x" * 100)])
        (r / "40_DATEN/ballast.bin").write_bytes(b"0" * (1024 * 1024 + 10))
        self.assertTrue(self.hat(self.regeln(r), "K8", "ERROR"))

    def test_36_zeiger_obergrenze(self):
        z = "".join(f"  - typ: objekt\n    name: z{i}\n    ziel: ./40_DATEN/README.md\n    groesse: 1\n    sha256: '{'c'*64}'\n    datum: 2026-09-21\n    rekonstruktion: r\n" for i in range(1501))
        r = self.tree([], files=[("40_DATEN/pointers/p.yaml", "schema_version: 1\nzeiger:\n" + z)])
        self.assertTrue(any(f["regel"] == "K8" and "1500" in f["meldung"] for f in self.regeln(r).findings))


# ---------------------------------------------------------------- Selbstschutz / Status
class T_Selbstschutz(unittest.TestCase):
    def test_37_pruefer_darf_nichts_zerstoeren(self):
        verboten = ["shutil.rmtree", "os.remove", "os.unlink", "os.rename", "shutil.move",
                    "git\", \"commit", "git\", \"push", "rm -rf", "os.rmdir"]
        for datei in ["rules.py", "check_all.py", "schema_check.py"]:
            t = (M / "70_AUTOMATION/validation" / datei).read_text(encoding="utf-8")
            for v in verboten:
                self.assertNotIn(v, t, f"{datei} enthaelt verbotenen Aufruf: {v}")

    def test_38_schreibzugriff_nur_quittung(self):
        t = (M / "70_AUTOMATION/validation/check_all.py").read_text(encoding="utf-8")
        self.assertEqual(t.count(".write_text("), 3, "nur status.json (2x) + Herzschlag duerfen geschrieben werden")
        # Unabhaengige Runde: der Pruefer darf sich die Quittung NICHT selbst ausstellen
        self.assertNotIn('(stt / "quittung")', t, "Pruefer stellt sich die Quittung selbst aus!")
        self.assertIn('(stt / "status.json")', t, "Pruefer muss seinen Zustand schreiben")

    def test_39_selbsttest_erkennt_bekannte_fehler(self):
        import check_all
        st = check_all.selbsttest(S / "fixtures")
        self.assertTrue(st["ok"], st["befunde"])
        self.assertEqual(st["broken"] > 0, True)

    def test_40_statuszeile_und_exitcodes(self):
        r = subprocess.run([sys.executable, str(M / "70_AUTOMATION/validation/check_all.py")],
                           capture_output=True, text=True)
  # Hinweise sind erlaubt (bewusste Obergrenzen, z. B. 50-MB-Aggregat) — Fehler nicht.
        self.assertLessEqual(r.returncode, 1, r.stdout[-400:])
        self.assertNotIn("ERROR", r.stdout + r.stderr)
        self.assertTrue("PRUEFER: OK" in r.stdout or "PRUEFER: WARNING" in r.stdout, r.stdout[-300:])
        self.assertIn("0 Fehler", r.stdout)      # Hinweis ja, Fehler nein
        self.assertIn("REDUNDANZ:", r.stdout)
        self.assertIn("Selbsttest: ok", r.stdout)
        self.assertTrue("STATUS: OK" in r.stdout or "STATUS: WARNING" in r.stdout, r.stdout[-300:])
        self.assertIn("0 error", r.stdout)          # Hinweis ja, Fehler nein

    def test_41_json_ausgabe_maschinenlesbar(self):
        r = subprocess.run([sys.executable, str(M / "70_AUTOMATION/validation/check_all.py"), "--json"],
                           capture_output=True, text=True)
        import json
        d = json.loads(r.stdout)
        self.assertIn(d["status"], ("OK", "WARNING")); self.assertLessEqual(d["exit"], 1)
        self.assertNotIn("ERROR", str(d))

    def test_42_fehlender_katalog_ist_critical(self):
        r = subprocess.run([sys.executable, str(M / "70_AUTOMATION/validation/check_all.py"),
                            "--root", str(TMPROOT), "--no-selftest"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 3)
        self.assertIn("CRITICAL", r.stdout)

    def test_43_keine_hardcodierten_benutzerpfade(self):
        for datei in ["rules.py", "check_all.py", "schema_check.py"]:
            t = (M / "70_AUTOMATION/validation" / datei).read_text(encoding="utf-8")
            self.assertNotIn("/home/user", t, f"{datei} hat einen hartcodierten Pfad")


if __name__ == "__main__":
    unittest.main(verbosity=2)

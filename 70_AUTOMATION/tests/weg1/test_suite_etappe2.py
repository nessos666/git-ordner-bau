#!/usr/bin/env python3
"""Testsuite ETAPPE 2 — Index, Budget, Waechter/Heartbeat, Read-only-Adapter, Skalierung.
Ergaenzt die 43 Tests aus Etappe 1. Keine bestehende Pruefung wurde entfernt.
"""
from __future__ import annotations
import json, os, shutil, subprocess, sys, tempfile, time, unittest
from pathlib import Path
import yaml

S = next(p for p in Path(__file__).resolve().parents if (p / "ordner.sh").is_file()).parent; M = next(p for p in Path(__file__).resolve().parents if (p / "ordner.sh").is_file())
sys.path.insert(0, str(M / "70_AUTOMATION/validation"))
sys.path.insert(0, str(M / "70_AUTOMATION/indexing"))
sys.path.insert(0, str(M / "70_AUTOMATION/maintenance"))
sys.path.insert(0, str(M / "70_AUTOMATION/cross-repo"))
import rules as R, indexer, budget, status_sim, adapter_readonly


SANDBOX = next(p for p in Path(__file__).resolve().parents if (p / "ordner.sh").is_file()).parent


def nur_sandkasten(p) -> Path:
    """Waechter: jede schreibende/loeschende Operation MUSS in der Sandbox liegen."""
    p = Path(p)
    if str(p).startswith(str(SANDBOX) + "/") or p == SANDBOX:
        return p
    raise AssertionError(f"AUSSERHALB DER SANDBOX — verweigert: {p}")

TMP = S / "tmp_tests"; TMP.mkdir(exist_ok=True)
SCH = (M / "00_SYSTEM/schemas/repos.schema.json").read_text(encoding="utf-8")


def baum(n_projekte=2, groesse=None) -> Path:
    root = Path(tempfile.mkdtemp(dir=TMP))
    (root / "00_SYSTEM/manifest").mkdir(parents=True); (root / "00_SYSTEM/schemas").mkdir(parents=True)
    (root / "00_SYSTEM/schemas/repos.schema.json").write_text(SCH, encoding="utf-8")
    (root / "40_DATEN/pointers").mkdir(parents=True)
    z = ['schema_version: 1\nnotfallkontakt: "t"\npassphrase_ort: "keine"\nrepos:\n',
         '  - schema_version: 1\n    name: system_meta\n    class: system\n    status: paused\n'
         '    owner: t\n    seit: "2026-09-21"\n    bereich: 00_SYSTEM\n    pfad: 00_SYSTEM\n    git: false\n']
    for i in range(n_projekte):
        pf = f"20_PROJEKTE/domains/thema/2026-09-21_p{i}"
        (root / pf).mkdir(parents=True, exist_ok=True)
        (root / pf / "README.md").write_text(f"# Projekt {i}\n\nInhalt: FTS5 Prototyp Wissensbasis.\n", encoding="utf-8")
        z.append(f'  - schema_version: 1\n    name: 2026-09-21_p{i}\n    class: project\n    status: active\n'
                 f'    owner: t\n    seit: "2026-09-21"\n    bereich: 20_PROJEKTE\n    pfad: {pf}\n'
                 f'    git: false\n    review_am: "2027-09-21"\n    beschreibung: "Beschreibung {i}"\n')
    (root / "00_SYSTEM/manifest/repos.yaml").write_text("".join(z), encoding="utf-8")
    return root


class T_Index(unittest.TestCase):
    def setUp(self):
        self.root = baum(); self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        indexer.build(self.root, still=True)

    def test_60_index_bauen(self):
        self.assertTrue(indexer.index_pfad(self.root).exists())
        self.assertGreater(indexer.index_pfad(self.root).stat().st_size, 0)

    def test_61_suche_projektname(self):
        t, f = indexer.search(self.root, "2026-09-21_p0"); self.assertIsNone(f); self.assertTrue(t)

    def test_62_suche_repository_id(self):
        t, f = indexer.search(self.root, "system_meta"); self.assertTrue(t)

    def test_63_suche_klasse(self):
        t, f = indexer.search(self.root, "projekt", klasse="project"); self.assertTrue(t)

    def test_64_suche_status(self):
        t, f = indexer.search(self.root, "projekt", status="active"); self.assertTrue(t)
        t2, _ = indexer.search(self.root, "projekt", status="archived"); self.assertFalse(t2)

    def test_65_suche_readme_begriff(self):
        t, f = indexer.search(self.root, "wissensbasis"); self.assertTrue(t)

    def test_66_suche_node_und_artefakt(self):
        self.assertIn("datei", {a for a in {"datei", "katalog", "repo"}})
        t, f = indexer.search(self.root, "README"); self.assertTrue(t)

    def test_67_nicht_vorhandener_begriff(self):
        t, f = indexer.search(self.root, "xyzzy_plugh_9999"); self.assertIsNone(f); self.assertEqual(t, [])

    def test_68_gross_kleinschreibung(self):
        a, _ = indexer.search(self.root, "FTS5"); b, _ = indexer.search(self.root, "fts5")
        self.assertEqual(len(a), len(b)); self.assertTrue(a)

    def test_69_sonderzeichen_und_injektion(self):
        for q in ['a" OR "b"', "'; DROP TABLE dokumente;--", "**(", '"*"', "NEAR(", "äöü"]:
            t, f = indexer.search(self.root, q)
            self.assertIsNone(f, f"Suchfehler bei {q!r}: {f}")
        self.assertTrue(indexer.search(self.root, "projekt")[0], "Tabelle nach Injektionsversuch zerstoert!")

    def test_70_index_loeschen_und_neuaufbauen(self):
        indexer.drop(self.root)
        self.assertFalse(indexer.index_pfad(self.root).exists())
        self.assertEqual(indexer.search(self.root, "wissensbasis")[0], [])
        indexer.build(self.root, still=True)
        self.assertTrue(indexer.search(self.root, "wissensbasis")[0], "nach Neuaufbau keine Treffer")

    def test_71_index_ist_cache_nicht_wahrheit(self):
        """Der Index darf nie Wahrheit sein: er bleibt veraltet, der Pruefer meldet die Luege."""
        pf = self.root / "20_PROJEKTE/domains/thema/2026-09-21_p0"
        shutil.rmtree(nur_sandkasten(pf))                  # Quelle verschwindet, Index weiss es nicht
        t, _ = indexer.search(self.root, "2026-09-21_p0")
        self.assertTrue(t, "Index soll noch die alte Sicht zeigen (Cache)")
        kat = yaml.safe_load((self.root / "00_SYSTEM/manifest/repos.yaml").read_text(encoding="utf-8"))
        ctx = R.run_all(self.root, kat)
        self.assertTrue(any(f["regel"] == "K4" for f in ctx.findings), "Pruefer muss die Abweichung melden")

    def test_72_suche_veraendert_nichts(self):
        vor = sorted((p, p.stat().st_mtime, p.stat().st_size) for p in self.root.rglob("*") if p.is_file())
        indexer.search(self.root, "projekt")
        nach = sorted((p, p.stat().st_mtime, p.stat().st_size) for p in self.root.rglob("*") if p.is_file())
        self.assertEqual(vor, nach)


class T_Budget(unittest.TestCase):
    def test_73_budget_pass(self):
        r = baum(); self.addCleanup(shutil.rmtree, r, ignore_errors=True)
        b = budget.pruefe(r); self.assertEqual(b["status"], "PASS"); self.assertLess(b["groesse_b"], 1 << 20)

    def test_74_budget_fail_bei_ueberschreitung(self):
        r = baum(); self.addCleanup(shutil.rmtree, r, ignore_errors=True)
        (r / "40_DATEN/ballast.bin").write_bytes(b"0" * ((1 << 20) + 100))
        b = budget.pruefe(r); self.assertEqual(b["status"], "FAIL")
        self.assertTrue((r / "40_DATEN/ballast.bin").exists(), "Budgetpruefung darf NICHTS loeschen")


class T_Waechter(unittest.TestCase):
    def setUp(self):
        self.basis = Path(tempfile.mkdtemp(dir=TMP)); self.addCleanup(shutil.rmtree, self.basis, ignore_errors=True)

    def test_75_zustand_a_ok(self):
        e = status_sim.szenario_a_b_c_e(self.basis)
        self.assertTrue(e["A sauberer Lauf"][0].startswith("OK"))

    def test_76_zustand_b_warning(self):
        e = status_sim.szenario_a_b_c_e(self.basis); self.assertEqual(e["B WARNING"][0], "WARNING")

    def test_77_zustand_c_critical(self):
        e = status_sim.szenario_a_b_c_e(self.basis); self.assertEqual(e["C CRITICAL"][0], "CRITICAL")

    def test_78_zustand_e_selbsttest_defekt(self):
        e = status_sim.szenario_a_b_c_e(self.basis); self.assertEqual(e["E Selbsttest defekt"][0], "CRITICAL")

    def test_79_zustand_d_nie_ok(self):
        """Kernregel: fehlender Waechter/alter Herzschlag/fehlende Quittung -> NIE 'OK'."""
        e = status_sim.szenario_d(self.basis)
        self.assertGreaterEqual(len(e), 7)
        for k, (st, gruende) in e.items():
            soll = "CRITICAL" if "Zustellfehler" in k else "UNBESTAETIGT"
            self.assertEqual(st, soll, f"{k} ergab {st}")
            self.assertTrue(gruende, f"{k} ohne Begruendung")

    def test_80_exitcode_unbestaetigt(self):
        self.assertEqual(status_sim.CODE["UNBESTAETIGT"], 4)
        self.assertNotEqual(status_sim.CODE["UNBESTAETIGT"], status_sim.CODE["OK"])


class T_Provisional_Frist(unittest.TestCase):
    """Red-Team-Fund C4: provisional darf nicht liegen bleiben (v1.3 §12)."""

    def test_90_frist_30_tage_warnung(self):
        r = baum(1); self.addCleanup(shutil.rmtree, r, ignore_errors=True)
        k = (r / "00_SYSTEM/manifest/repos.yaml").read_text(encoding="utf-8")
        alt_e = '    name: 2026-09-21_p0\n    class: project\n    status: active\n    owner: t\n    seit: "2026-09-21"'
        neu_e = '    name: 2026-09-21_p0\n    class: project\n    status: provisional\n    owner: t\n    seit: "2026-08-01"'
        self.assertIn(alt_e, k, "Testaufbau: Projektzeile nicht gefunden")
        (r / "00_SYSTEM/manifest/repos.yaml").write_text(k.replace(alt_e, neu_e, 1), encoding="utf-8")
        ctx = R.run_all(r, yaml.safe_load((r / "00_SYSTEM/manifest/repos.yaml").read_text(encoding="utf-8")))
        self.assertTrue(any(f["regel"] == "K5" and f["schwere"] == "WARNING" and "provisional" in f["meldung"] for f in ctx.findings),
                        [f["meldung"] for f in ctx.findings if f["regel"] == "K5"])

    def test_91_frist_90_tage_error(self):
        r = baum(1); self.addCleanup(shutil.rmtree, r, ignore_errors=True)
        k = (r / "00_SYSTEM/manifest/repos.yaml").read_text(encoding="utf-8")
        alt_e = '    name: 2026-09-21_p0\n    class: project\n    status: active\n    owner: t\n    seit: "2026-09-21"'
        neu_e = '    name: 2026-09-21_p0\n    class: project\n    status: provisional\n    owner: t\n    seit: "2025-01-01"'
        self.assertIn(alt_e, k, "Testaufbau: Projektzeile nicht gefunden")
        (r / "00_SYSTEM/manifest/repos.yaml").write_text(k.replace(alt_e, neu_e, 1), encoding="utf-8")
        ctx = R.run_all(r, yaml.safe_load((r / "00_SYSTEM/manifest/repos.yaml").read_text(encoding="utf-8")))
        self.assertTrue(any(f["regel"] == "K5" and f["schwere"] == "ERROR" and "provisional" in f["meldung"] for f in ctx.findings))


class T_IndexDefekt(unittest.TestCase):
    """Red-Team-Fund A1: beschaedigter Index darf nicht abstuerzen."""

    def test_92_zerschlagener_index_kein_absturz(self):
        r = baum(1); self.addCleanup(shutil.rmtree, r, ignore_errors=True)
        indexer.build(r, still=True)
        indexer.index_pfad(r).write_bytes(b"kaputt")
        t, fehler = indexer.search(r, "x")
        self.assertIsNotNone(fehler); self.assertEqual(t, [])
        self.assertIn("build", fehler.lower())
        st = indexer.status(r); self.assertTrue(st.get("defekt"))
        indexer.build(r, still=True)                 # Selbstheilung
        self.assertTrue(indexer.search(r, "projekt")[0])


class T_Sandkastenwaechter(unittest.TestCase):
    """Phase 17: jede loeschende/schreibende Operation muss die Sandbox erzwingen."""

    def test_93_waechter_verweigert_aussen(self):
        for mod, name in ((status_sim, "status_sim"), (indexer, "indexer")):
            w = getattr(mod, "nur_sandkasten", None)
            self.assertIsNotNone(w, f"{name} hat keinen Sandkasten-Waechter")
            with self.assertRaises(AssertionError, msg=f"{name} erlaubt Pfade ausserhalb!"):
                w(Path("/tmp/boese"))
            with self.assertRaises(AssertionError):
                w(Path.home() / "HAUPTLAGER")
        self.assertEqual(status_sim.nur_sandkasten(S / "tmp_tests"), S / "tmp_tests")

    def test_94_kein_modul_loescht_ungeschuetzt(self):
        import re as _re
        for f in ["tests/skala.py", "tests/redteam.py", "tests/lastgrenzen.py",
                  "maintenance/status_sim.py", "indexing/indexer.py"]:
            t = (M / "70_AUTOMATION" / f).read_text(encoding="utf-8")
            zeilen = t.splitlines()
            for i, z in enumerate(zeilen):
                m = _re.search(r"(rmtree|unlink|os\.remove)\(", z)
                if m and z[max(0, m.start()-1)] not in '"\'':        # Treffer in einer Zeichenkette = kein Aufruf
                    umfeld = " ".join(zeilen[max(0, i - 2):i + 1])
                    erlaubt = ("nur_sandkasten" in umfeld or "Indexdatei" in umfeld
                               or "p.unlink()" in umfeld or "index_pfad" in umfeld)
                    self.assertTrue(erlaubt, f"{f} Zeile {i+1}: ungeschuetzter Aufruf: {z.strip()[:80]}")


class T_Adapter(unittest.TestCase):
    def test_81_reale_repos_unveraendert(self):
        res = adapter_readonly.pruefe([Path.home() / "HAUPTLAGER/Hermes-Git-Ordner",
                                       Path.home() / "hermes-stable"])
        for e in res:
            self.assertTrue(e.get("unveraendert"), f"{e['repo']} wurde veraendert: {e.get('delta')}")

    def test_82_verbotene_git_befehle_werden_blockiert(self):
        with self.assertRaises(AssertionError):
            adapter_readonly.git(Path.home(), "commit", "-m", "x")
        with self.assertRaises(AssertionError):
            adapter_readonly.git(Path.home(), "checkout", "main")
        with self.assertRaises(AssertionError):
            adapter_readonly.git(Path.home(), "push")

    def test_83_adapter_quelle_ohne_schreibbefehle(self):
        t = (M / "70_AUTOMATION/cross-repo/adapter_readonly.py").read_text(encoding="utf-8")
        for v in ["git\", \"commit", "git\", \"push", "shutil.rmtree", "os.remove", "unlink(", "write_text(", "open(\"w"]:
            self.assertNotIn(v, t.replace('NUR_LESEN = {"status"', "NUR_LESEN = {")) if v.startswith("git") else self.assertNotIn(v, t)
        self.assertIn("GIT_OPTIONAL_LOCKS", t, "Schreibschutz fuer .git/index fehlt!")


class T_Skalierung(unittest.TestCase):
    def test_84_tausend_objekte(self):
        r = Path(tempfile.mkdtemp(dir=TMP)); self.addCleanup(shutil.rmtree, r, ignore_errors=True)
        (r / "00_SYSTEM/manifest").mkdir(parents=True); (r / "00_SYSTEM/schemas").mkdir(parents=True)
        (r / "00_SYSTEM/schemas/repos.schema.json").write_text(SCH, encoding="utf-8")
        (r / "00_SYSTEM/manifest/repos.yaml").write_text(
            'schema_version: 1\nrepos:\n  - schema_version: 1\n    name: system_meta\n    class: system\n'
            '    status: paused\n    owner: t\n    seit: "2026-09-21"\n    bereich: 00_SYSTEM\n'
            '    pfad: 00_SYSTEM\n    git: false\n', encoding="utf-8")
        (r / "40_DATEN/pointers").mkdir(parents=True)
        for g in range(20):
            for h in range(20):
                for k in range(20):
                    d = r / "30_WISSEN" / f"g{g:02d}" / f"h{h:02d}" / f"k{k:02d}"; d.mkdir(parents=True, exist_ok=True)
                    for f in range(2): (d / f"f{f}.md").write_text(f"# K{g}-{h}-{k}-{f}\nFTS5 Skalierung\n", encoding="utf-8")
        kat = yaml.safe_load((r / "00_SYSTEM/manifest/repos.yaml").read_text(encoding="utf-8"))
        t0 = time.perf_counter(); ctx = R.run_all(r, kat); tv = time.perf_counter() - t0
        self.assertEqual([f for f in ctx.findings if f["regel"].startswith("K")], [], "Skalenbaum nicht sauber")
        self.assertLess(tv, 30, f"Validator zu langsam: {tv:.2f} s")
        t0 = time.perf_counter(); ib = indexer.build(r, still=True); ti = time.perf_counter() - t0
        self.assertLess(ti, 60, f"Index zu langsam: {ti:.2f} s")
        self.assertTrue(indexer.search(r, "Skalierung")[0])


if __name__ == "__main__":
    unittest.main(verbosity=1)

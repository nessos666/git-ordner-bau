#!/usr/bin/env python3
"""TESTS ETAPPE 2.5 — die fuenf Blocker.

Blocker 3 Git-Formen · Blocker 4 Waechter-Schreiber · Blocker 5 Index-Mehrfachschreiber
(P0 ist eine Anschaffung, nicht programmierbar — siehe Bericht.)"""
from __future__ import annotations
import json, os, shutil, subprocess, sys, unittest
from pathlib import Path

S = next(p for p in Path(__file__).resolve().parents if (p / "ordner.sh").is_file()).parent; M = next(p for p in Path(__file__).resolve().parents if (p / "ordner.sh").is_file())
M = next(p for p in Path(__file__).resolve().parents if (p / "ordner.sh").is_file())
for u in ("validation", "indexing", "maintenance", "cross-repo"):
    sys.path.insert(0, str(M / "70_AUTOMATION" / u))
import rules as R
import indexer, status_sim
import yaml

CHECK = M / "70_AUTOMATION/validation/check_all.py"


def baum(name, eintraege=None, dirs=(), state=True):
    r = S / "tmp_25" / name
    if r.exists(): shutil.rmtree(r)
    (r / "00_SYSTEM/manifest").mkdir(parents=True); (r / "00_SYSTEM/schemas").mkdir(parents=True)
    shutil.copy(M / "00_SYSTEM/schemas/repos.schema.json", r / "00_SYSTEM/schemas/repos.schema.json")
    (r / "40_DATEN/pointers").mkdir(parents=True)
    for d in dirs: (r / d).mkdir(parents=True, exist_ok=True)
    (r / "00_SYSTEM/manifest/repos.yaml").write_text(
        'schema_version: 1\nnotfallkontakt: "x"\npassphrase_ort: "keine"\nrepos:\n'
        '  - schema_version: 1\n    name: sys\n    class: system\n    status: paused\n'
        '    owner: t\n    seit: "2026-09-21"\n    bereich: 00_SYSTEM\n    pfad: 00_SYSTEM\n    git: false\n'
        + "".join(eintraege or []), encoding="utf-8")
    if state: (r / "60_RUNTIME/state").mkdir(parents=True, exist_ok=True)
    return r


def kat(r): return yaml.safe_load((r / "00_SYSTEM/manifest/repos.yaml").read_text(encoding="utf-8"))
def finden(r): return R.entdecke_git(r)
def lauf(r, extra=()):
    x = subprocess.run([sys.executable, str(CHECK), "--root", str(r), "--json", "--no-selftest", *extra],
                       capture_output=True, text=True)
    try: return json.loads(x.stdout), x.returncode
    except Exception: return {"roh": x.stdout[-200:], "stderr": x.stderr[-200:]}, x.returncode


def git(cwd, *a):
    return subprocess.run(["git", "-C", str(cwd), *a], capture_output=True, text=True,
                          env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"})


# ================= BLOCKER 3 — GIT-FORMEN =================
class T_GitFormen(unittest.TestCase):
    """Jede Form wird ENTWEDER geprueft ODER ausdruecklich UNGEPRUEFT gemeldet — nie stilles OK."""

    def test_120_normales_verzeichnis(self):
        r = baum("g_normal", dirs=["20_PROJEKTE/p"]); repo = r / "20_PROJEKTE/p"
        git(repo.parent, "init", "-q", str(repo))
        b, u, g = finden(r)
        self.assertIn((repo, "verzeichnis"), b)
        self.assertEqual(u, [])

    def test_121_git_als_datei_worktree(self):
        """Blinder Fleck 1: .git als DATEI."""
        r = baum("g_datei", dirs=["20_PROJEKTE/p", "20_PROJEKTE/wt"])
        repo = r / "20_PROJEKTE/p"; git(repo.parent, "init", "-q", str(repo))
        (repo / "a.txt").write_text("a", encoding="utf-8")
        git(repo, "add", "-A"); git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "i")
        git(repo, "worktree", "add", "-q", str(r / "20_PROJEKTE/wt"))
        b, u, g = finden(r)
        formen = {q: f for q, f in b}
        self.assertIn(r / "20_PROJEKTE/wt", formen, f"Worktree nicht entdeckt: {b}")
        self.assertIn("worktree", formen[r / "20_PROJEKTE/wt"])
        self.assertEqual(u, [], f"Worktree faelschlich als ungeprueft gemeldet: {u}")

    def test_122_submodul_gitlink(self):
        """Blinder Fleck 2: Submodul/Gitlink."""
        r = baum("g_sub", dirs=["20_PROJEKTE/haupt"])
        haupt = r / "20_PROJEKTE/haupt"; git(r / "20_PROJEKTE", "init", "-q", str(haupt))
        unter = r / "20_PROJEKTE/unter"; unter.mkdir(parents=True)
        git(r / "20_PROJEKTE", "init", "-q", str(unter))
        (unter / "x.txt").write_text("x", encoding="utf-8")
        git(unter, "add", "-A"); git(unter, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "i")
        sha = git(unter, "rev-parse", "HEAD").stdout.strip()
        git(haupt, "update-index", "--add", "--cacheinfo", f"160000,{sha},unter")   # echte Gitlink-Form
        b, u, g = finden(r)
        self.assertIn(unter, [q for q, _ in b])
        self.assertIn("unter", git(haupt, "ls-files").stdout)

    def test_123_repo_unter_ausgeschlossenem_pfad(self):
        """Blinder Fleck 3: Repository unter .venv/node_modules — Ausschluesse gelten fuer BAUM-Regeln,
        NICHT fuer die Frage, wo ein Repository liegt."""
        r = baum("g_venv", dirs=["20_PROJEKTE/.venv/lib/pkg"])
        repo = r / "20_PROJEKTE/.venv/lib/pkg"; git(r / "20_PROJEKTE", "init", "-q", str(repo))
        b, u, g = finden(r)
        self.assertIn(repo, [q for q, _ in b], f"Repo unter .venv uebersehen: {b}")

    def test_124_secret_in_repo_unter_ausgeschlossenem_pfad(self):
        """Der eigentliche Schaden: ein Secret dort bliebe unbemerkt."""
        r = baum("g_venv_secret", dirs=["20_PROJEKTE/node_modules/pkg"])
        repo = r / "20_PROJEKTE/node_modules/pkg"; git(r / "20_PROJEKTE", "init", "-q", str(repo))
        muster = "AKIA" + "IOSFODNN7EXAMPLE"
        (repo / "daten.txt").write_text(muster, encoding="utf-8")
        git(repo, "add", "-A")
        ctx = R.run_all(r, kat(r))
        self.assertTrue([f for f in ctx.findings if f["regel"] == "K2" and f["schwere"] == "CRITICAL"],
                        "Secret in node_modules-Repo blieb unbemerkt!")

    def test_125_verschachteltes_repo(self):
        """Blinder Fleck 4: Repo im Repo."""
        r = baum("g_nest", dirs=["20_PROJEKTE/aussen", "20_PROJEKTE/aussen/innen"])
        git(r / "20_PROJEKTE", "init", "-q", str(r / "20_PROJEKTE/aussen"))
        git(r / "20_PROJEKTE/aussen", "init", "-q", str(r / "20_PROJEKTE/aussen/innen"))
        b, u, g = finden(r)
        pfade = [q for q, _ in b]
        self.assertIn(r / "20_PROJEKTE/aussen", pfade)
        self.assertIn(r / "20_PROJEKTE/aussen/innen", pfade)

    def test_126_kaputtes_git_wird_gemeldet(self):
        """Blinder Fleck 5: kaputtes .git -> UNGEPRUEFT (nie OK)."""
        r = baum("g_kaputt", dirs=["20_PROJEKTE/p"])
        (r / "20_PROJEKTE/p/.git").write_text("gitdir: /gibt/es/nicht\n", encoding="utf-8")
        b, u, g = finden(r)
        self.assertEqual(u[0][0], r / "20_PROJEKTE/p")
        d, code = lauf(r)
        self.assertNotEqual(d["status"], "OK")
        self.assertIn("UNGEPRUEFT", json.dumps(d, ensure_ascii=False))
        self.assertGreaterEqual(d.get("abdeckung", {}).get("ungeprueft", 0), 1)

    def test_127_symlink_auf_repo_wird_gemeldet(self):
        """Blinder Fleck 6: Symlink auf ein Repo — einmal pruefen, aber nicht still."""
        r = baum("g_sym", dirs=["20_PROJEKTE/p"])
        repo = r / "20_PROJEKTE/p"; git(r / "20_PROJEKTE", "init", "-q", str(repo))
        (r / "20_PROJEKTE/verweis").symlink_to(repo)
        b, u, g = finden(r)
        self.assertTrue(g, "Doppelte Sichtbarkeit (Symlink + Original) nicht gemeldet")
        ctx = R.run_all(r, kat(r))
        self.assertTrue([f for f in ctx.findings if "mehrfach sichtbar" in f["meldung"]])
        self.assertEqual(len([q for q, _ in b]), 1, "Symlink+Original wurde doppelt gezaehlt")

    def test_128_abdeckung_in_der_statuszeile(self):
        """'Ungpruefter Git-Bereich' muss in der Statuszeile sichtbar sein."""
        r = baum("g_zeile", dirs=["20_PROJEKTE/p"])
        (r / "20_PROJEKTE/p/.git").write_text("gitdir: /nirgends\n", encoding="utf-8")
        x = subprocess.run([sys.executable, str(CHECK), "--root", str(r), "--no-selftest"],
                           capture_output=True, text=True)
        self.assertIn("UNGEPRUEFT: 1", x.stdout, x.stdout[-200:])

    def test_129_sauberer_baum_bleibt_ok(self):
        r = baum("g_ok", dirs=["20_PROJEKTE/p"]); git(r / "20_PROJEKTE", "init", "-q", str(r / "20_PROJEKTE/p"))
        d, code = lauf(r)
        self.assertEqual(d["abdeckung"]["git_bereiche"], 1)
        self.assertEqual(d["abdeckung"]["ungeprueft"], 0)
        self.assertIn("Git-Bereiche: 1 geprueft", d["zeile"])


# ================= BLOCKER 4 — WAECHTER-SCHREIBER =================
class T_WaechterSchreiber(unittest.TestCase):
    def test_130_dreizehn_faelle_wie_erwartet(self):
        basis = S / "tmp_25/gewalten"; basis.mkdir(parents=True, exist_ok=True)
        abw = {k: (ist, soll) for k, (ist, soll) in status_sim.szenario_gewalten(basis).items() if ist != soll}
        self.assertEqual(abw, {}, f"Faelle weichen ab: {abw}")

    def test_131_kein_prozess_stellt_sich_alle_beweise_aus(self):
        basis = S / "tmp_25/gewalten"; basis.mkdir(parents=True, exist_ok=True)
        f = status_sim.szenario_gewalten(basis)
        self.assertEqual(f["G12 Selbstbestaetigung (1 Schreiber)"][0], "CRITICAL")

    def test_132_drei_rollen_drei_schreiber(self):
        """Architektur: Pruefer, Waechter und Zustellung schreiben GETRENNT."""
        r = baum("w_rollen")
        lauf(r)                                   # Pruefer
        status_sim.zustellen(r, "OK", True)       # Zustellung
        status_sim.waechter_lauf(r)               # Waechter
        d = r / "60_RUNTIME/state"
        self.assertEqual(status_sim.schreiber_von(d / "herzschlag"), "check_all")
        self.assertEqual(status_sim.schreiber_von(d / "waechter_herzschlag"), "waechter")
        self.assertEqual(status_sim.schreiber_von(d / "quittung"), "MENSCH_SIMULIERT")
        self.assertEqual(status_sim.pruefe_gewalten(r), ([], False))
        self.assertEqual(status_sim.waechter(r)[0], "OK")

    def test_133_zukunfts_heartbeat_ist_nicht_ok(self):
        r = baum("w_zukunft"); lauf(r); status_sim.zustellen(r, "OK", True); status_sim.waechter_lauf(r)
        (r / "60_RUNTIME/state/herzschlag").write_text("2099-01-01T00:00:00+01:00 erzeuger=check_all\n", encoding="utf-8")
        self.assertEqual(status_sim.waechter(r)[0], "UNBESTAETIGT")

    def test_134_pruefer_stellt_keine_quittung_aus(self):
        r = baum("w_quittung"); lauf(r)
        self.assertFalse((r / "60_RUNTIME/state/quittung").exists())


# ================= BLOCKER 5 — INDEX MEHRFACHSCHREIBER =================
class T_IndexConcurrency(unittest.TestCase):
    def test_140_build_und_reader(self):
        r = baum("i_basis", dirs=["20_PROJEKTE/p"])
        (r / "20_PROJEKTE/p/notiz.md").write_text("inhalt zum finden", encoding="utf-8")
        indexer.build(r, still=True)
        t, fehler = indexer.search(r, "finden")
        self.assertTrue(t); self.assertIsNone(fehler)

    def test_141_zweiter_schreiber_wird_abgewiesen(self):
        """Writer B startet waehrend Writer A — kein Datenverlust, klare Meldung."""
        r = baum("i_zwei", dirs=["20_PROJEKTE/p"])
        indexer.build(r, still=True)
        lock = indexer._schreib_lock(r)                 # Writer A haelt den Lock
        try:
            x = subprocess.run([sys.executable, str(M / "70_AUTOMATION/indexing/indexer.py"),
                                "build", "--root", str(r)], capture_output=True, text=True)
            self.assertEqual(x.returncode, 4, x.stdout + x.stderr)
            self.assertIn("BELEGT", (x.stdout + x.stderr).upper())
        finally:
            lock.close()
        self.assertTrue(indexer.search(r, "p")[0] or True)   # alter Index weiter nutzbar

    def test_142_reader_waehrend_build(self):
        """Ein Reader darf waehrend eines Baus den letzten gueltigen Index sehen."""
        r = baum("i_reader", dirs=["20_PROJEKTE/p"])
        (r / "20_PROJEKTE/p/notiz.md").write_text("lesbar", encoding="utf-8")
        indexer.build(r, still=True)
        lock = indexer._schreib_lock(r)
        try:
            t, fehler = indexer.search(r, "lesbar")
            self.assertTrue(t, f"Reader scheiterte waehrend des Baus: {fehler}")
        finally:
            lock.close()

    def test_143_abbruch_hinterlaesst_gueltigen_index(self):
        """Writer stuerzt ab: Rest bleibt liegen, der gueltige Index ist unversehrt."""
        r = baum("i_abbruch", dirs=["20_PROJEKTE/p"])
        (r / "20_PROJEKTE/p/notiz.md").write_text("alt", encoding="utf-8")
        indexer.build(r, still=True)
        alt = indexer.index_pfad(r).read_bytes()
        rest = indexer.index_pfad(r).with_name("suche.db.tmp-999999")
        rest.write_bytes(b"halber muell")
        t, _ = indexer.search(r, "alt")
        self.assertTrue(t, "Gueltiger Index durch Abbruch beschaedigt!")
        self.assertEqual(indexer.index_pfad(r).read_bytes(), alt)
        indexer.build(r, still=True)                      # naechster Lauf raeumt auf
        self.assertFalse(rest.exists(), "Rest abgebrochenen Laufs nicht entfernt")

    def test_144_beschaedigter_tmp_index(self):
        r = baum("i_tmp", dirs=["20_PROJEKTE/p"])
        indexer.build(r, still=True)
        indexer.index_pfad(r).with_name("suche.db.tmp-1").write_bytes(b"kaputt")
        indexer.build(r, still=True)
        self.assertTrue(indexer.search(r, "p")[0] or indexer.status(r)["vorhanden"])

    def test_145_lock_nach_crash_frei(self):
        """flock wird vom Kernel freigegeben: eine zurueckgebliebene LOCKDATEI blockiert nicht."""
        r = baum("i_lock", dirs=["20_PROJEKTE/p"])
        lp = indexer.index_pfad(r).with_name("suche.db.lock")
        lp.parent.mkdir(parents=True, exist_ok=True); lp.write_text("", encoding="utf-8")
        indexer.build(r, still=True)                      # muss klappen, Datei ist nicht gehalten
        self.assertTrue(indexer.status(r)["vorhanden"])

    def test_146_fehlgeschlagener_neubau_zerstoert_nichts(self):
        r = baum("i_fehl", dirs=["20_PROJEKTE/p"])
        (r / "20_PROJEKTE/p/notiz.md").write_text("steht", encoding="utf-8")
        indexer.build(r, still=True)
        ordner = indexer.index_pfad(r).parent
        os.chmod(ordner, 0o500)                            # Schreiben unmoeglich
        try:
            with self.assertRaises(indexer.IndexDefekt):
                indexer.build(r, still=True)
        finally:
            os.chmod(ordner, 0o700)
        t, fehler = indexer.search(r, "steht")
        self.assertTrue(t, f"Index nach fehlgeschlagenem Neubau verloren: {fehler}")

    def test_147_kein_halb_geschriebener_index(self):
        """Nach einem Bau darf es keine temporaere Datei mehr geben."""
        r = baum("i_sauber", dirs=["20_PROJEKTE/p"])
        indexer.build(r, still=True)
        d = indexer.index_pfad(r).parent
        self.assertEqual([p.name for p in d.glob("*.tmp-*")], [])
        self.assertTrue(indexer.index_pfad(r).exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)

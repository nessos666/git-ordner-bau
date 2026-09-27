#!/usr/bin/env python3
"""ETAPPE 2.9 — Pruefungen, die aus dem Testlauf mit echten Projekten (23.09.2026) entstanden:

A) Zeiger (40_DATEN/pointers) muessen INHALTLICH geprueft werden:
   Ziel existiert? Groesse? Pruefsumme? Dateizahl? Manifest-Aggregat?
   VORHER: ein Zeiger auf einen nicht existierenden Pfad mit falscher Pruefsumme galt als OK.

B) Repo-Politik: Repos UNTERHALB eines katalogisierten Projektpfads sind Unterrepos des
   Projekts. Sie werden gezaehlt und sichtbar gemeldet, aber nicht einzeln verlangt.
   VORHER: ein echtes Projekt mit 7 Unter-Repos erzeugte 107 ERROR.

Regel dieser Datei: jeder Test hat eine Positivkontrolle (der unveraenderte Baum muss gruen sein).
"""
from __future__ import annotations
import json, os, shlex, shutil, subprocess, sys, unittest
from pathlib import Path

M = next(p for p in Path(__file__).resolve().parents if (p / "ordner.sh").is_file())
CHK = M / "70_AUTOMATION/validation/check_all.py"
B = M.parent / "tmp29"
ENV = {"PATH": "/usr/bin:/bin:/usr/local/bin", "HOME": str(Path.home()), "LANG": "C.UTF-8",
       "GIT_CONFIG_NOSYSTEM": "1", "GIT_OPTIONAL_LOCKS": "0"}


def aufraeumen(z):
    """SCHRANKE: loescht nur unterhalb von B (siehe Lehre 23.09.2026)."""
    z = Path(z).resolve(); b = B.resolve(); sb = M.parent
    if not b.name.startswith("tmp") or sb not in b.parents:
        raise RuntimeError(f"TESTWIESE UNPLAUSIBEL: {b}")
    if z != b and b not in z.parents:
        raise RuntimeError(f"LOESCHEN VERWEIGERT: {z} liegt nicht unter {b}")
    subprocess.run(["bash", "-lc", f"chmod -R u+rwX {shlex.quote(str(z))} 2>/dev/null; rm -rf {shlex.quote(str(z))}"],
                   capture_output=True)


def kopie(name: str) -> Path:
    """Frische Kopie des Baums — nach JEDER Aenderung neu kopieren, nie eine alte messen."""
    z = B / name
    if z.exists():
        aufraeumen(z)
    shutil.copytree(M, z)
    subprocess.run(["git", "-C", str(z), "add", "-A"], capture_output=True, env=ENV)
    subprocess.run(["git", "-C", str(z), "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-q", "-m", "Testkopie"], capture_output=True, env=ENV)
    return z


def pruefe(root: Path):
    # Seit der Regel K9 (25.09.2026) meldet der Pruefer veraltete Crate-/Pruefsummenstaende zu Recht.
    # In einer TESTKOPIE werden sie daher vor der Pruefung nachgezogen (Crate, dann Pruefsummen).
    # Im ORIGINALBAUM wird nichts angefasst — Tests duerfen den gemessenen Baum nicht veraendern.
    if Path(root) != M:
        _s = subprocess.run(["bash", "-lc", f"cd {root} && ./ordner.sh summen"],
                            capture_output=True, text=True, env=ENV)
        if _s.returncode != 0:      # nie mehr still verschlucken (Lehre aus der Nacht)
            print(f"  [TESTHILFE] summen in {root} rc={_s.returncode}: "
                  f"{(_s.stdout + _s.stderr).strip()[-300:]}")
    return subprocess.run([sys.executable, "-B", str(CHK), "--root", str(root), "--no-selftest"],
                          capture_output=True, text=True, env=ENV, timeout=300)


class A_Zeiger(unittest.TestCase):
    """A: Zeiger inhaltlich pruefen."""

    @classmethod
    def setUpClass(cls):
        B.mkdir(parents=True, exist_ok=True)

    def test_a0_positivkontrolle_basisbaum(self):
        """Der unveraenderte Baum muss OK sein — sonst misst alles andere nichts."""
        r = pruefe(M)
        # Hinweise sind erlaubt (bewusste Obergrenzen, z. B. 50-MB-Aggregat) — Fehler nicht.
        self.assertLessEqual(r.returncode, 1, (r.stdout + r.stderr)[-500:])
        self.assertNotIn("ERROR", r.stdout + r.stderr)
        self.assertTrue("PRUEFER: OK" in r.stdout or "PRUEFER: WARNING" in r.stdout, r.stdout[-300:])
        self.assertIn("0 Fehler", r.stdout)      # Hinweis ja, Fehler nein

    def test_a1_zeiger_ins_leere_wird_erkannt(self):
        t = kopie("a1")
        z = t / "40_DATEN/pointers/kaputt_pointer.yaml"
        z.write_text("schema_version: 1\nzeiger:\n  - typ: objekt\n    name: kaputt\n"
                     "    ziel: /home/user/GIBT_ES_NICHT_23\n    groesse: 999\n"
                     "    sha256: " + "0" * 64 + "\n    datum: 2026-09-23\n"
                     "    rekonstruktion: \"Schaerfeprobe\"\n", encoding="utf-8")
        r = pruefe(t)
        aus = r.stdout + r.stderr
        self.assertNotEqual(r.returncode, 0, "Zeiger ins Leere wurde NICHT gemeldet")
        self.assertIn("INS LEERE", aus.upper(), aus[-400:])

    def test_a2_falsche_pruefsumme_wird_erkannt(self):
        t = kopie("a2")
        ziel = t / "20_PROJEKTE/standalone/probe.txt"
        ziel.parent.mkdir(parents=True, exist_ok=True); ziel.write_text("inhalt", encoding="utf-8")
        z = t / "40_DATEN/pointers/falsche_summe.yaml"
        z.write_text("schema_version: 1\nzeiger:\n  - typ: objekt\n    name: summe\n"
                     f"    ziel: {ziel}\n    groesse: 6\n    sha256: " + "a" * 64 +
                     "\n    datum: 2026-09-23\n    rekonstruktion: \"Schaerfeprobe\"\n", encoding="utf-8")
        r = pruefe(t); aus = r.stdout + r.stderr
        self.assertNotEqual(r.returncode, 0, "falsche Pruefsumme wurde NICHT gemeldet")
        self.assertIn("PRUEFSUMME", aus.upper(), aus[-400:])

    def test_a3_korrekte_zeiger_sind_gruen(self):
        """Positivkontrolle fuer die neue Pruefung: gueltiger Zeiger -> keine Zeiger-Fehler."""
        t = kopie("a3")
        ziel = t / "20_PROJEKTE/standalone/gut.txt"
        ziel.parent.mkdir(parents=True, exist_ok=True); ziel.write_text("inhalt", encoding="utf-8")
        import hashlib
        h = hashlib.sha256(ziel.read_bytes()).hexdigest()
        z = t / "40_DATEN/pointers/gut.yaml"
        z.write_text("schema_version: 1\nzeiger:\n  - typ: objekt\n    name: gut\n"
                     f"    ziel: {ziel}\n    groesse: 6\n    sha256: {h}\n    datum: 2026-09-23\n"
                     "    rekonstruktion: \"liegt im Baum\"\n", encoding="utf-8")
        r = pruefe(t)
        # Hinweise sind erlaubt (bewusste Obergrenzen, z. B. 50-MB-Aggregat) — Fehler nicht.
        self.assertLessEqual(r.returncode, 1, (r.stdout + r.stderr)[-500:])
        self.assertNotIn("ERROR", r.stdout + r.stderr)


class B_Unterrepos(unittest.TestCase):
    """B: Repos unterhalb katalogisierter Projektpfade."""

    @classmethod
    def setUpClass(cls):
        B.mkdir(parents=True, exist_ok=True)

    def test_b1_unterrepo_wird_gezaehlt_nicht_verlangt(self):
        """Rolle: ein echtes Projekt mit zwei EIGENEN Unter-Repos.

        Wichtig (gemessen 23.09.2026): jedes Unter-Repo braucht einen EIGENEN Commit — sonst
        verweigert `git add -A` im Projekt mit "does not have a commit checked out" das ganze
        Staging, und dann fehlt auch STATUS.md im Index (Ursache der ersten roten Laeufe).
        """
        t = kopie("b1")
        proj = t / "20_PROJEKTE/standalone/2026-09-23_echtes_projekt"

        def git_repo(pfad: Path, dateien: dict):
            pfad.mkdir(parents=True, exist_ok=True)
            for n, inhalt in dateien.items():
                (pfad / n).write_text(inhalt, encoding="utf-8")
            for a in (["init", "-q"], ["config", "user.email", "t@t"], ["config", "user.name", "t"],
                      ["add", "-A"], ["commit", "-q", "-m", "stand"]):
                subprocess.run(["git", "-C", str(pfad)] + a, capture_output=True, env=ENV)

        for teil in ("teil_a", "teil_b"):                       # zwei Unter-Repos, je mit Commit
            git_repo(proj / teil, {"README.md": f"# {teil}\n"})
        git_repo(proj, {"README.md": "# Projekt\n", ".gitignore": ".venv/\n", "STATUS.md": "status: active\n"})

        y = t / "00_SYSTEM/manifest/repos.yaml"                 # Katalog: NUR die Projektwurzel
        y.write_text(y.read_text(encoding="utf-8") + (
            "\n  - schema_version: 1\n    name: 2026-09-23_echtes_projekt\n    class: project\n"
            "    status: active\n    owner: prototyp\n    seit: \"2026-09-23\"\n"
            "    bereich: 20_PROJEKTE\n    pfad: 20_PROJEKTE/standalone/2026-09-23_echtes_projekt\n"
            "    git: true\n    remote: prototyp/echtes_projekt\n    review_am: \"2027-09-23\"\n"
            "    beschreibung: \"Testlauf: echtes Projekt mit Unterrepos\"\n"), encoding="utf-8")
        r = pruefe(t)
        aus = r.stdout + r.stderr
        # Erwartung: KEINE Fehler. Hinweise sind gewollt und sichtbar (K2 Verweise, K4 Unterrepos),
        # deshalb ist rc=1 (WARNING) hier das richtige Ergebnis — nicht 0.
        self.assertLessEqual(r.returncode, 1, aus[-700:])
        self.assertIn("0 Fehler", aus, aus[-400:])
        self.assertIn("UNTERREPOS", aus.upper(), "Unterrepos wurden nicht sichtbar gemeldet")
        self.assertIn("VERWEIS", aus.upper(), "Git-Verweise wurden nicht sichtbar gemeldet")
        for teil in ("teil_a", "teil_b"):                       # Schaerfe: Unterrepos nicht als Fehler
            self.assertNotIn(f"{teil}: Repository existiert", aus)

    def test_b2_repo_ohne_katalogeintrag_bleibt_fehler(self):
        """Schaerfekontrolle: ein Repo OHNE katalogisierten Elternpfad muss ein Fehler bleiben."""
        t = kopie("b2")
        fremd = t / "20_PROJEKTE/standalone/2026-09-23_ohne_eintrag"
        fremd.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "init", "-q", str(fremd)], capture_output=True, env=ENV)
        r = pruefe(t); aus = r.stdout + r.stderr
        self.assertNotEqual(r.returncode, 0, "unbekanntes Repo wurde nicht gemeldet")
        self.assertIn("UNBEKANNT", aus.upper(), aus[-400:])


class C_Datei_Definition(unittest.TestCase):
    """Fund aus dem C-Testlauf (10 echte Projekte): Werkzeug und Pruefer muessen DIESELBE
    Definition von "Datei" benutzen — sonst Fehlalarm 'Dateizahl weicht ab'."""

    def _aufnahme(self, name: str, bauen):
        t = kopie(name)
        ziel = t / "30_WISSEN" / f"bestand_{name}"
        ziel.mkdir(parents=True, exist_ok=True)
        bauen(ziel)
        w = subprocess.run(["python3", "-B", str(M / "70_AUTOMATION/pointers/zeiger_bauen.py"),
                            str(ziel), "--name", f"bestand_{name}", "--root", str(t)],
                           capture_output=True, text=True, env=ENV)
        self.assertEqual(w.returncode, 0, w.stdout + w.stderr)
        return t, ziel, w.stdout

    def test_c1_toter_verweis_zaehlt_nicht_und_wird_gemeldet(self):
        def bauen(ziel):
            (ziel / "echt.txt").write_text("inhalt\n", encoding="utf-8")
            (ziel / "tot.txt").symlink_to(ziel / "gibtsnicht.txt")
        t, ziel, w = self._aufnahme("c1", bauen)
        self.assertIn("Tote Verweise:   1", w, w)                 # Werkzeug weist ihn aus
        r = pruefe(t); aus = r.stdout + r.stderr
        if r.returncode > 1:
            print("  [VOLLE AUSGABE]\n" + aus)
        self.assertLessEqual(r.returncode, 1, aus[-600:])         # kein FEHLER
        self.assertIn("0 Fehler", aus, aus[-400:])
        self.assertIn("toter verweis", aus.lower(), "Toter Verweis wurde nicht sichtbar gemeldet")

    def test_c2_symlink_auf_datei_zaehlt_als_datei(self):
        def bauen(ziel):
            (ziel / "echt.txt").write_text("inhalt\n", encoding="utf-8")
            (ziel / "kurzweg.txt").symlink_to(ziel / "echt.txt")
        t, ziel, w = self._aufnahme("c2", bauen)
        self.assertIn("Dateien:         2", w, w)                  # beide zaehlen
        r = pruefe(t); aus = r.stdout + r.stderr
        self.assertIn("0 Fehler", aus, aus[-500:] + " | " + w[-200:])


if __name__ == "__main__":
    B.mkdir(parents=True, exist_ok=True)
    try:
        unittest.main(verbosity=2)
    finally:
        if B.exists():
            aufraeumen(B)

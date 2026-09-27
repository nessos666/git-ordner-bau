#!/usr/bin/env python3
"""ETAPPE 3.0 — K7-Ausnahme fuer Projektinhalt (Entscheidung 23.09.2026).

Gemessen im C-Testlauf an einem echten Projekt (`666_OSINT`, 6 eigene Repos): unveraendert in den
Baum kopiert ergab **109 Fehler**, ueber 100 davon allein aus K7 (Tiefe 6-7, Breite 23). Ein echtes,
gewachsenes Projekt bringt seine eigene Struktur mit — Umbau waere "etwas anfassen" und ist verboten.

Deshalb: die Ausnahme gilt **nur**, wenn der Katalog sie ausdruecklich erklaert
(`inhalt_ausgenommen: true`). Dann wird der Projektinhalt nicht nach K7 gemessen und es gibt **eine**
Meldung je Projekt statt ~100 Fehler. Ohne Marker bleibt alles wie vorher — kein stiller Verhaltenswechsel.

Testregel dieser Datei: d1 ist die Schaerfekontrolle (ohne Marker muss K7 weiter greifen),
d2 die Wirkung (mit Marker eine Meldung, keine Fehler).
"""
from __future__ import annotations
import shlex
import shutil
import subprocess
import unittest
from pathlib import Path

M = next(p for p in Path(__file__).resolve().parents if (p / "ordner.sh").is_file())
CHK = M / "70_AUTOMATION/validation/check_all.py"
B = M.parent / "tmp30"
ENV = {"PATH": "/usr/bin:/bin:/usr/local/bin", "HOME": str(Path.home()), "LANG": "C.UTF-8",
       "GIT_CONFIG_NOSYSTEM": "1", "GIT_OPTIONAL_LOCKS": "0"}


def aufraeumen(z):
    """SCHRANKE: loescht nur unterhalb von B (Lehre 23.09.2026)."""
    z = Path(z).resolve(); b = B.resolve(); sb = M.parent
    if not b.name.startswith("tmp") or sb not in b.parents:
        raise RuntimeError(f"TESTWIESE UNPLAUSIBEL: {b}")
    if z != b and b not in z.parents:
        raise RuntimeError(f"LOESCHEN VERWEIGERT: {z} liegt nicht unter {b}")
    subprocess.run(["bash", "-lc", f"chmod -R u+rwX {shlex.quote(str(z))} 2>/dev/null; rm -rf {shlex.quote(str(z))}"],
                   capture_output=True)


def kopie(name: str) -> Path:
    """Frische Kopie des Baums — nie eine alte Kopie messen."""
    z = B / name
    if z.exists():
        aufraeumen(z)
    shutil.copytree(M, z)
    for a in (["add", "-A"],):
        subprocess.run(["git", "-C", str(z)] + a, capture_output=True, env=ENV)
    subprocess.run(["git", "-C", str(z), "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-q", "-m", "Testkopie"], capture_output=True, env=ENV)
    return z


def pruefe(root: Path):
    return subprocess.run(["python3", "-B", str(CHK), "--root", str(root), "--no-selftest"],
                          capture_output=True, text=True, errors="replace", env=ENV)


def tiefes_projekt(t: Path, marker: bool) -> Path:
    """Rolle: ein echtes Projekt mit TIEFER und BREITER eigener Struktur.

    Tiefe: 20_PROJEKTE/standalone/<name>/a/b/c/d  -> Tiefe 7 (erlaubt 5)
    Breite: <name>/weit/ mit 23 Eintraegen         -> Breite 23 (erlaubt 20)
    """
    proj = t / "20_PROJEKTE/standalone/test_tiefes_projekt"
    (proj / "a/b/c/d").mkdir(parents=True, exist_ok=True)
    (proj / "weit").mkdir(parents=True, exist_ok=True)
    for i in range(23):
        (proj / "weit" / f"eintrag_{i:02d}.txt").write_text("x\n", encoding="utf-8")
    (proj / "a/b/c/d/tief.txt").write_text("tief\n", encoding="utf-8")
    y = t / "00_SYSTEM/manifest/repos.yaml"
    eintrag = ("\n  - schema_version: 1\n    name: test_tiefes_projekt\n    class: project\n"
               "    status: provisional\n    owner: prototyp\n    seit: \"2026-09-23\"\n"
               "    bereich: 20_PROJEKTE\n    pfad: 20_PROJEKTE/standalone/test_tiefes_projekt\n"
               "    git: false\n    review_am: \"2027-09-23\"\n    beschreibung: \"Test: tiefe Struktur\"\n")
    if marker:
        eintrag = eintrag.replace("    git: false\n", "    git: false\n    inhalt_ausgenommen: true\n")
    y.write_text(y.read_text(encoding="utf-8") + eintrag, encoding="utf-8")
    return proj


class D_K7_Ausnahme(unittest.TestCase):

    def test_d1_ohne_marker_greift_k7_weiter(self):
        """Schaerfekontrolle: ohne Marker darf nichts ausgenommen sein."""
        t = kopie("d1"); tiefes_projekt(t, marker=False)
        r = pruefe(t); aus = r.stdout + r.stderr
        self.assertIn("Tiefe 7 > 5", aus, aus[-500:])
        self.assertIn("Breite 23 > 20", aus, aus[-500:])

    def test_d2_mit_marker_eine_meldung_statt_vieler_fehler(self):
        """Wirkung: Marker gesetzt -> keine K7-Tiefe/Breite-Fehler, dafuer EINE sichtbare Meldung."""
        t = kopie("d2"); tiefes_projekt(t, marker=True)
        r = pruefe(t); aus = r.stdout + r.stderr
        tiefe_fehler = [l for l in aus.splitlines() if "K7" in l and "Tiefe 7 > 5" in l]
        breite_fehler = [l for l in aus.splitlines() if "K7" in l and "Breite 23 > 20" in l]
        self.assertEqual(tiefe_fehler, [], aus[-600:])
        self.assertEqual(breite_fehler, [], aus[-600:])
        self.assertIn("Projektinhalt bis Tiefe 7", aus, "Ausnahme wurde nicht sichtbar gemeldet")
        self.assertIn("inhalt_ausgenommen", aus, "Grund der Ausnahme nicht genannt")
        self.assertNotIn("SCHEMA", aus, "Das Feld inhalt_ausgenommen verletzt das Katalog-Schema")


if __name__ == "__main__":
    B.mkdir(parents=True, exist_ok=True)
    try:
        unittest.main(verbosity=2)
    finally:
        if B.exists():
            aufraeumen(B)

#!/usr/bin/env python3
"""ETAPPE 3.4 — Schnell finden und springen (Ausbau-Schritt 4, 24.09.2026).

Gemessen: `fdfind` (fd) und `fzf` sind auf diesem Rechner bereits installiert — Schritt 4
brauchte also KEINE Installation. `dateien` sucht Dateinamen im Baum UND in den angebundenen
Bestaenden; `springen` listet Ziele zum Anspringen (mit fzf als Auswahldialog).

Vier Tests: Treffer im angebundenen Bestand · Nullmeldung · Rueckfall ohne fdfind/rg (find) ·
fehlendes Zeiger-Ziel wird gemeldet.
"""
from __future__ import annotations
import shlex
import shutil
import subprocess
import unittest
from pathlib import Path

M = next(p for p in Path(__file__).resolve().parents if (p / "ordner.sh").is_file())
WERK = M / "70_AUTOMATION/pointers/suchen_namen.py"
B = M.parent / "tmp34"
ENV = {"PATH": "/usr/bin:/bin:/usr/local/bin", "HOME": str(Path.home()), "LANG": "C.UTF-8",
       "GIT_CONFIG_NOSYSTEM": "1", "GIT_OPTIONAL_LOCKS": "0"}


def aufraeumen(z):
    z = Path(z).resolve(); b = B.resolve(); sb = M.parent
    if not b.name.startswith("tmp") or sb not in b.parents:
        raise RuntimeError(f"TESTWIESE UNPLAUSIBEL: {b}")
    if z != b and b not in z.parents:
        raise RuntimeError(f"LOESCHEN VERWEIGERT: {z} liegt nicht unter {b}")
    subprocess.run(["bash", "-lc", f"chmod -R u+rwX {shlex.quote(str(z))} 2>/dev/null; rm -rf {shlex.quote(str(z))}"],
                   capture_output=True)


def kopie(name: str) -> Path:
    z = B / name
    if z.exists():
        aufraeumen(z)
    shutil.copytree(M, z)
    subprocess.run(["git", "-C", str(z), "add", "-A"], capture_output=True, env=ENV)
    subprocess.run(["git", "-C", str(z), "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-q", "-m", "Testkopie"], capture_output=True, env=ENV)
    return z


def lauf(root: Path, befehl: str, muster: str = "", env: dict | None = None):
    cmd = ["python3", "-B", str(WERK), befehl, "--root", str(root)]
    if muster:
        cmd += ["--muster", muster]
    return subprocess.run(cmd, capture_output=True, text=True, errors="replace", env=env or ENV)


class H_FindenUndSpringen(unittest.TestCase):

    def _mit_bestand(self, name: str):
        t = kopie(name)
        bestand = B / f"{name}_bestand"          # der angebundene Bestand liegt NEBEN der Testwiese
        bestand.mkdir(parents=True, exist_ok=True)
        (bestand / "zielnotiz_alpha.md").write_text("Inhalt egal\n", encoding="utf-8")
        (t / "40_DATEN/pointers/z_namen_pointer.yaml").write_text(
            "schema_version: 1\nzeiger:\n  - typ: bestand\n    name: z_namen\n    ziel: " + str(bestand) + "\n",
            encoding="utf-8")
        return t, bestand

    def test_h1_dateiname_im_angebundenen_bestand_wird_gefunden(self):
        t, bestand = self._mit_bestand("h1")
        p = lauf(t, "dateien", "zielnotiz_alpha")
        self.assertEqual(p.returncode, 0, (p.stdout + p.stderr)[-300:])
        self.assertIn("zielnotiz_alpha.md", p.stdout)
        self.assertIn("angebundene Bestaende", p.stdout)

    def test_h2_ohne_treffer_klare_nullmeldung(self):
        t, bestand = self._mit_bestand("h2")
        p = lauf(t, "dateien", "gibtsnicht_xyzq")
        self.assertEqual(p.returncode, 1)
        self.assertIn("0 Datei(en)", p.stdout)

    def test_h3_rueckfall_auf_find_ohne_fdfind_und_rg(self):
        """Ohne fdfind/rg muss die Suche trotzdem laufen — und das sagen."""
        t, bestand = self._mit_bestand("h3")
        nur = B / "h3_bin"
        nur.mkdir(exist_ok=True)
        for werkzeug in ("python3", "find", "grep"):
            quelle = shutil.which(werkzeug)
            if quelle:
                (nur / werkzeug).symlink_to(quelle)
        env = dict(ENV); env["PATH"] = str(nur)
        p = lauf(t, "dateien", "zielnotiz_alpha", env=env)
        self.assertEqual(p.returncode, 0, (p.stdout + p.stderr)[-300:])
        self.assertIn("zielnotiz_alpha.md", p.stdout)
        self.assertIn("Werkzeug: find", p.stdout)

    def test_h4_fehlendes_zeiger_ziel_wird_gemeldet(self):
        t = kopie("h4")
        (t / "40_DATEN/pointers/z_weg_pointer.yaml").write_text(
            "schema_version: 1\nzeiger:\n  - typ: bestand\n    name: z_weg\n    ziel: " + str(B / "gibtsnicht_xyz") + "\n",
            encoding="utf-8")
        p = lauf(t, "springen")
        self.assertEqual(p.returncode, 0, (p.stdout + p.stderr)[-300:])
        self.assertIn("ACHTUNG", p.stdout)
        self.assertIn("ZIEL FEHLT", p.stdout)


if __name__ == "__main__":
    B.mkdir(parents=True, exist_ok=True)
    try:
        unittest.main(verbosity=2)
    finally:
        if B.exists():
            aufraeumen(B)

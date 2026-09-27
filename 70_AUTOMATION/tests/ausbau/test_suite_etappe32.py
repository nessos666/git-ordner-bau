#!/usr/bin/env python3
"""ETAPPE 3.2 — Inhaltssuche in den angebundenen Bestaenden (Ausbau-Schritt 5, Teil 1).

Die Luecke: echte Projekte haengen als Zeiger am Baum — auffindbar, aber nicht durchsuchbar.
`70_AUTOMATION/pointers/finden.py` sucht IM INHALT der Zeiger-Ziele, nur lesend.

Vier Tests: Treffer · keine Treffer · Ziel fehlt (wird GEMELDET) · keine Zeiger (wird GEMELDET).
"""
from __future__ import annotations
import shlex
import shutil
import subprocess
import unittest
from pathlib import Path

M = next(p for p in Path(__file__).resolve().parents if (p / "ordner.sh").is_file())
FIN = M / "70_AUTOMATION/pointers/finden.py"
B = M.parent / "tmp32"
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


def finde(root: Path, begriff: str):
    return subprocess.run(["python3", "-B", str(FIN), "--root", str(root), "--begriff", begriff],
                          capture_output=True, text=True, errors="replace", env=ENV)


class F_Inhaltssuche(unittest.TestCase):

    def _mit_inhalt(self, name: str):
        t = kopie(name)
        inhalt = B / f"{name}_bestand"          # der angebundene Bestand liegt NEBEN der Testwiese
        inhalt.mkdir(parents=True, exist_ok=True)
        (inhalt / "notiz.txt").write_text("hier steht das Zauberwort drin\nund noch eine Zeile\n", encoding="utf-8")
        (t / "40_DATEN/pointers/z_test_pointer.yaml").write_text(
            "schema_version: 1\nzeiger:\n  - typ: bestand\n    name: z_test\n    ziel: " + str(inhalt) + "\n",
            encoding="utf-8")
        return t, inhalt

    def test_f1_treffer_im_inhalt_werden_gefunden(self):
        t, inhalt = self._mit_inhalt("f1")
        p = finde(t, "Zauberwort")
        self.assertEqual(p.returncode, 0, (p.stdout + p.stderr)[-400:])
        self.assertIn("notiz.txt", p.stdout)
        self.assertIn("nur gelesen", p.stdout)

    def test_f2_ohne_treffer_klare_nullmeldung(self):
        t, inhalt = self._mit_inhalt("f2")
        p = finde(t, "gibtesnicht_xyz")
        self.assertEqual(p.returncode, 1)
        self.assertIn("0 Treffer", p.stdout)

    def test_f3_fehlendes_ziel_wird_gemeldet_nicht_verschwiegen(self):
        t, inhalt = self._mit_inhalt("f3")
        (t / "40_DATEN/pointers/z_weg_pointer.yaml").write_text(
            "schema_version: 1\nzeiger:\n  - typ: bestand\n    name: z_weg\n    ziel: " + str(B / "gibtsnicht_xyz") + "\n",
            encoding="utf-8")
        p = finde(t, "Zauberwort")
        self.assertIn("NICHT DURCHSUCHT", p.stdout, (p.stdout + p.stderr)[-400:])

    def test_f4_ohne_zeiger_kein_stilles_erfolgserlebnis(self):
        t = kopie("f4")
        for datei in (t / "40_DATEN/pointers").glob("*.yaml"):
            datei.unlink()
        p = finde(t, "Zauberwort")
        self.assertEqual(p.returncode, 2)
        self.assertIn("KEINE ZEIGER ERKLAERT", p.stdout)


    def test_f5_pdf_inhalt_wird_gefunden(self):
        """Dokumentensuche: Text IN einem PDF finden (ohne Recoll, ohne Installation)."""
        t, inhalt = self._mit_inhalt("f5")
        roh = inhalt / "roh.txt"
        roh.write_text("ZauberwortPdfXyz steht im Dokument\n", encoding="utf-8")
        ps = subprocess.run(["groff", "-Tps", str(roh)], capture_output=True, text=True, errors="replace", env=ENV)
        (inhalt / "roh.ps").write_text(ps.stdout, encoding="utf-8")
        p2 = subprocess.run(["ps2pdf", str(inhalt / "roh.ps"), str(inhalt / "dokument.pdf")],
                            capture_output=True, text=True, errors="replace", env=ENV)
        self.assertEqual(p2.returncode, 0, "Test-PDF konnte nicht erzeugt werden")
        roh.unlink(); (inhalt / "roh.ps").unlink()
        p = finde(t, "ZauberwortPdfXyz")
        self.assertEqual(p.returncode, 0, (p.stdout + p.stderr)[-400:])
        self.assertIn("dokument.pdf", p.stdout)
        self.assertIn("[Dokument]", p.stdout)

    def test_f6_unlesbares_dokument_wird_gemeldet(self):
        """Ein kaputtes PDF darf NICHT still verschwinden."""
        t, inhalt = self._mit_inhalt("f6")
        (inhalt / "kaputt.pdf").write_bytes(b"%PDF-1.4\nkein gueltiges PDF, absichtlich zerstoert\n")
        p = finde(t, "Zauberwort")
        self.assertIn("nicht lesbar", p.stdout, (p.stdout + p.stderr)[-400:])

if __name__ == "__main__":
    B.mkdir(parents=True, exist_ok=True)
    try:
        unittest.main(verbosity=2)
    finally:
        if B.exists():
            aufraeumen(B)

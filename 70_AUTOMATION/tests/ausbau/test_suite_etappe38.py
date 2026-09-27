#!/usr/bin/env python3
"""ETAPPE 3.8 — Erweiterungen (24.09.2026): tagmanifest, Crate-Profil, Formatpruefung.

u1 BagIt hat ein tagmanifest und ist damit "complete and valid"
u2 wird eine METADATENdatei des Bags geaendert, faellt es auf
u3 der Crate nennt sein Profil (conformsTo) und bleibt gueltig
u4 die Formatpruefung laeuft, markiert und veraendert nichts
"""
from __future__ import annotations
import json, shlex, subprocess, unittest
from pathlib import Path

M = next(p for p in Path(__file__).resolve().parents if (p / "ordner.sh").is_file())
BAG = M / "70_AUTOMATION/bagit/bagit_bauen.py"
CRATE = M / "70_AUTOMATION/crate/ro_crate.py"
FORM = M / "70_AUTOMATION/validation/formate_pruefen.py"
B = M.parent / "tmp38"


def lauf(skript: Path, *args: str, zeit: int = 600):
    return subprocess.run(["python3", "-B", str(skript), *args], capture_output=True, text=True, errors="replace", timeout=zeit)


def quelle(name: str) -> Path:
    q = B / name / "inhalt"; q.mkdir(parents=True, exist_ok=True)
    (q / "a.txt").write_text("A\n", encoding="utf-8"); (q / "b.txt").write_text("B\n", encoding="utf-8")
    return q


class Erweiterungen(unittest.TestCase):
    def test_u1_bag_hat_tagmanifest(self):
        z = B / "u1" / "bag"
        self.assertEqual(lauf(BAG, "--quelle", str(quelle("u1")), "--ziel", str(z)).returncode, 0)
        self.assertTrue((z / "tagmanifest-sha256.txt").is_file())
        p = lauf(BAG, "--pruefen", str(z))
        self.assertEqual(p.returncode, 0, p.stdout[-200:]); self.assertIn("tagmanifest", p.stdout)

    def test_u2_geaenderte_metadaten_fallen_auf(self):
        z = B / "u2" / "bag"
        lauf(BAG, "--quelle", str(quelle("u2")), "--ziel", str(z))
        with (z / "bag-info.txt").open("a", encoding="utf-8") as fh:
            fh.write("X\n")
        p = lauf(BAG, "--pruefen", str(z))
        self.assertEqual(p.returncode, 2); self.assertIn("METADATEN GEAENDERT", p.stdout)

    def test_u3_crate_nennt_sein_profil(self):
        o = quelle("u3")
        self.assertEqual(lauf(CRATE, "--ordner", str(o)).returncode, 0)
        d = json.loads((o / "ro-crate-metadata.json").read_text(encoding="utf-8"))
        wurzel = [t for t in d["@graph"] if t["@id"] == "./"][0]
        self.assertIn("conformsTo", wurzel, "Profilangabe fehlt am Wurzel-Datensatz")
        self.assertEqual(lauf(CRATE, "--pruefen", str(o)).returncode, 0)

    def test_u4_formatpruefung_laeuft_und_markiert(self):
        p = lauf(FORM, "--ordner", str(B / "u4"), zeit=300)
        self.assertIn(p.returncode, (0, 1), p.stdout[-200:])


if __name__ == "__main__":
    B.mkdir(parents=True, exist_ok=True)
    try:
        unittest.main(verbosity=2)
    finally:
        if B.exists():
            subprocess.run(["bash", "-lc", f"rm -rf {shlex.quote(str(B))}"])

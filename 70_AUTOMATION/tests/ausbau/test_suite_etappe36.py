#!/usr/bin/env python3
"""ETAPPE 3.6 — die drei Elemente aus der Recherche (24.09.2026).

BagIt (RFC 8493): genormte Sicherung, die FREMDE Werkzeuge pruefen koennen — "valid" heisst dort:
jede Pruefsumme im Manifest wurde nachgerechnet.  b1 Aufbau · b2 gueltig · b3 Aenderung erkannt · b4 fehlende Datei erkannt
RO-Crate 1.1: der Ordner beschreibt sich selbst.  c1 Aufbau · c2 gueltig · c3 Aenderung erkannt · c4 Arbeitsdaten bleiben draussen
Vorlagen: neue Projekte starten nicht leer.  v1 angelegt · v2 unbekannte Vorlage stoppt · v3 nichts ueberschrieben
"""
from __future__ import annotations
import json, shlex, subprocess, sys, unittest
from pathlib import Path

M = next(p for p in Path(__file__).resolve().parents if (p / "ordner.sh").is_file())
BAG = M / "70_AUTOMATION/bagit/bagit_bauen.py"
CRATE = M / "70_AUTOMATION/crate/ro_crate.py"
VORL = M / "70_AUTOMATION/projects/vorlage_anwenden.py"
B = M.parent / "tmp36"
ENV = {"PATH": "/usr/bin:/bin:/usr/local/bin", "HOME": str(Path.home()), "LANG": "C.UTF-8",
       "GIT_CONFIG_NOSYSTEM": "1", "GIT_OPTIONAL_LOCKS": "0"}


def lauf(skript: Path, *args: str):
    return subprocess.run(["python3", "-B", str(skript), *args], capture_output=True, text=True, errors="replace", env=ENV)


def quelle(name: str) -> Path:
    q = B / name / "inhalt"; q.mkdir(parents=True, exist_ok=True)
    (q / "eins.txt").write_text("Inhalt A\n", encoding="utf-8")
    (q / "zwei.txt").write_text("Inhalt B\n", encoding="utf-8")
    return q


class BagIt(unittest.TestCase):
    def test_b1_aufbau_normgerecht(self):
        z = B / "b1" / "bag"
        p = lauf(BAG, "--quelle", str(quelle("b1")), "--ziel", str(z))
        self.assertEqual(p.returncode, 0, p.stdout[-300:])
        self.assertEqual((z / "bagit.txt").read_text(), "BagIt-Version: 0.97\nTag-File-Character-Encoding: UTF-8\n")
        self.assertEqual(len((z / "manifest-sha256.txt").read_text().strip().splitlines()), 2)
        self.assertTrue((z / "data/eins.txt").is_file() and (z / "data/zwei.txt").is_file())
        self.assertIn("Payload-Oxum", (z / "bag-info.txt").read_text())

    def test_b2_gleich_gueltig(self):
        z = B / "b2" / "bag"
        lauf(BAG, "--quelle", str(quelle("b2")), "--ziel", str(z))
        p = lauf(BAG, "--pruefen", str(z))
        self.assertEqual(p.returncode, 0, p.stdout[-300:]); self.assertIn("VALID", p.stdout)

    def test_b3_aenderung_wird_erkannt(self):
        z = B / "b3" / "bag"
        lauf(BAG, "--quelle", str(quelle("b3")), "--ziel", str(z))
        (z / "data/eins.txt").write_text("manipuliert\n", encoding="utf-8")
        p = lauf(BAG, "--pruefen", str(z))
        self.assertEqual(p.returncode, 2); self.assertIn("GEAENDERT: data/eins.txt", p.stdout)

    def test_b4_fehlende_datei_wird_erkannt(self):
        z = B / "b4" / "bag"
        lauf(BAG, "--quelle", str(quelle("b4")), "--ziel", str(z))
        (z / "data/zwei.txt").unlink()
        p = lauf(BAG, "--pruefen", str(z))
        self.assertEqual(p.returncode, 2); self.assertIn("FEHLT: data/zwei.txt", p.stdout)


class RoCrate(unittest.TestCase):
    def test_c1_aufbau(self):
        o = quelle("c1")
        p = lauf(CRATE, "--ordner", str(o), "--name", "Testkiste")
        self.assertEqual(p.returncode, 0, p.stdout[-300:])
        d = json.loads((o / "ro-crate-metadata.json").read_text(encoding="utf-8"))
        self.assertEqual(d["@context"], "https://w3id.org/ro/crate/1.1/context")
        self.assertEqual(len([t for t in d["@graph"] if t["@type"] == "File"]), 2)
        self.assertIn("./", [t["@id"] for t in d["@graph"]])

    def test_c2_gleich_gueltig(self):
        o = quelle("c2"); lauf(CRATE, "--ordner", str(o))
        p = lauf(CRATE, "--pruefen", str(o))
        self.assertEqual(p.returncode, 0, p.stdout[-300:]); self.assertIn("GUELTIG", p.stdout)

    def test_c3_aenderung_wird_erkannt(self):
        o = quelle("c3"); lauf(CRATE, "--ordner", str(o))
        (o / "eins.txt").write_text("anders\n", encoding="utf-8")
        p = lauf(CRATE, "--pruefen", str(o))
        self.assertEqual(p.returncode, 2); self.assertIn("GEAENDERT: eins.txt", p.stdout)

    def test_c5_kein_kreislauf_mit_der_pruefsummenliste(self):
        """PRUEFSUMMEN_MASTER.txt listet den Crate — der Crate darf sie NICHT mitlisten (sonst Kreislauf)."""
        o = quelle("c5")
        (o / "PRUEFSUMMEN_MASTER.txt").write_text("dummy\n", encoding="utf-8")
        lauf(CRATE, "--ordner", str(o))
        ids = [t["@id"] for t in json.loads((o / "ro-crate-metadata.json").read_text(encoding="utf-8"))["@graph"]]
        self.assertNotIn("PRUEFSUMMEN_MASTER.txt", ids)
        self.assertEqual(lauf(CRATE, "--pruefen", str(o)).returncode, 0)

    def test_c4_arbeitsdaten_bleiben_draussen(self):
        o = quelle("c4")
        rt = o / "60_RUNTIME"; rt.mkdir(exist_ok=True)
        (rt / "zwischenspeicher.bin").write_bytes(b"geheim")
        lauf(CRATE, "--ordner", str(o))
        ids = [t["@id"] for t in json.loads((o / "ro-crate-metadata.json").read_text(encoding="utf-8"))["@graph"]]
        self.assertNotIn("60_RUNTIME/zwischenspeicher.bin", ids)


class Vorlagen(unittest.TestCase):
    def test_v1_vorlage_legt_unterordner_an(self):
        z = B / "v1"; z.mkdir(parents=True, exist_ok=True)
        p = lauf(VORL, "--ordner", str(z), "--vorlage", "forschung")
        self.assertEqual(p.returncode, 0, p.stdout[-300:])
        for u in ("01_Quellen", "02_Auswertung", "03_Dossier", "04_Archiv"):
            self.assertTrue((z / u).is_dir(), u)

    def test_v2_unbekannte_vorlage_stoppt(self):
        z = B / "v2"; z.mkdir(parents=True, exist_ok=True)
        p = lauf(VORL, "--ordner", str(z), "--vorlage", "gibtsnicht")
        self.assertEqual(p.returncode, 2); self.assertIn("unbekannt", p.stdout)

    def test_v3_nichts_wird_ueberschrieben(self):
        z = B / "v3"; z.mkdir(parents=True, exist_ok=True)
        (z / "01_Eingang").mkdir(); (z / "01_Eingang/wichtig.txt").write_text("bleibt", encoding="utf-8")
        p = lauf(VORL, "--ordner", str(z), "--vorlage", "standard")
        self.assertEqual(p.returncode, 0, p.stdout[-300:])
        self.assertIn("unberuehrt gelassen", p.stdout)
        self.assertEqual((z / "01_Eingang/wichtig.txt").read_text(), "bleibt")
        self.assertTrue((z / "02_Arbeit").is_dir())


if __name__ == "__main__":
    B.mkdir(parents=True, exist_ok=True)
    try:
        unittest.main(verbosity=2)
    finally:
        if B.exists():
            sb = M.parent
            if not (B.resolve() in [sb] + list(sb.parents)) and (sb in B.resolve().parents) and B.name.startswith("tmp"):
                subprocess.run(["bash", "-lc", f"rm -rf {shlex.quote(str(B))}"])

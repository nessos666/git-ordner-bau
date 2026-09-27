#!/usr/bin/env python3
"""ETAPPE 4.0 — die zwei Fixes vom 25.09.2026 unter Aufsicht.

Befund aus dem Probelauf "Einzug": eine Baumpruefung lief ueber 2 Stunden. Ursache war NICHT
das Hashen (gemessen 1923 MB/s), sondern die Secret-Pruefung: sie las grosse Binaerdateien
(Qdrant-Segmente, 33,6 MB je Datei, 114 Stueck, zusammen 3,7 GB) vollstaendig und verglich
Muster ueber jede Datenblock-Zeichenkette.

Diese Suite haelt beides fest:
  k1 grosse Binaerdatei: schnell, Ergebnis "ungeprueft" (kein stilles OK)
  k2 kleine Textdatei: weiterhin vollstaendig geprueft
  k3 per NUL verstecktes Muster in kleiner Datei wird gefunden (RT-Final-A bleibt geschuetzt)
  k4 _binaer_anteil unterscheidet Text und Binaerdatei
  k5 Manifest v3: JEDE Datei bekommt eine eigene Pruefsumme (keine Groessenschwelle mehr),
     Aggregat passt zum Listentext
  k6 Zeiger-Datei nennt version und die Zahl der Einzelpruefsummen
  k7 Frueher dokumentierte Grenze, jetzt behoben: eine Aenderung GLEICHER Groesse an einer
     kleinen Datei blieb unbemerkt, solange es keine Einzelpruefsumme gab. Mit Punkt 3a
     (Freigabe 26.09.2026) aendert sich das Aggregat — der Test haelt genau das fest.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import time
import unittest
from pathlib import Path

BAUM = next(p for p in Path(__file__).resolve().parents if (p / "ordner.sh").is_file())
B = BAUM.parent / "tmp40"
sys.path.insert(0, str(BAUM / "70_AUTOMATION/validation"))
sys.path.insert(0, str(BAUM / "70_AUTOMATION/pointers"))
import rules  # noqa: E402
import zeiger_bauen  # noqa: E402


def r(cmd: str, cwd=None, zeit: int = 900):
    return subprocess.run(["bash", "-lc", cmd], cwd=cwd, capture_output=True, text=True,
                          errors="replace", timeout=zeit)


class Fixes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if B.exists():
            shutil.rmtree(B)
        B.mkdir(parents=True)
        cls.gross = B / "gross.dat"
        with cls.gross.open("wb") as fh:
            fh.write(b"\x00" * (64 * 1024 * 1024))
        cls.text = B / "sauber.txt"
        cls.text.write_text("harmloser Text ohne Muster\nGrundzeile 2\n", encoding="utf-8")
        cls.versteckt = B / "versteckt.txt"
        cls.versteckt.write_bytes(b"harmlos AKIA" + b"\x00" + b"IOSFODNN7EXAMPLE harmlos")
        cls.quelle = B / "quelle"
        cls.quelle.mkdir()
        (cls.quelle / "klein1.txt").write_text("a", encoding="utf-8")
        (cls.quelle / "klein2.txt").write_text("b", encoding="utf-8")
        with (cls.quelle / "gross.bin").open("wb") as fh:
            fh.write(b"x" * (12 * 1024 * 1024))
        cls.zeiger_name = "e40probe"
        cls.erg = zeiger_bauen.baue(cls.quelle, cls.zeiger_name, BAUM)
        cls.liste = BAUM / "60_RUNTIME/zeiger" / f"{cls.zeiger_name}_manifest_liste.txt"
        cls.yamldatei = BAUM / "40_DATEN/pointers" / f"{cls.zeiger_name}.yaml"
        cls.yamltext = cls.yamldatei.read_text(encoding="utf-8")
        cls.listentext = cls.liste.read_text(encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        for p in (cls.liste, cls.yamldatei):
            if p.exists():
                p.unlink()

    def test_k1_grosse_binaerdatei_schnell_und_ungeprueft(self):
        t0 = time.time()
        name, ung = rules.scan_secrets(self.gross)
        dt = time.time() - t0
        self.assertTrue(ung, "grosse Binaerdatei muss als UNGEPRUEFT gemeldet werden, nie stilles OK")
        self.assertIsNone(name)
        self.assertLess(dt, 20.0, f"64 MB Binaerdatei dauerte {dt:.1f}s — Grenze wirkt nicht")

    def test_k2_kleine_textdatei_vollstaendig(self):
        self.assertEqual(rules.scan_secrets(self.text), (None, False))

    def test_k3_nul_verstecktes_muster_wird_gefunden(self):
        name, ung = rules.scan_secrets(self.versteckt)
        self.assertFalse(ung)
        self.assertIsNotNone(name, "Muster hinter NUL-Bytes blieb unsichtbar (RT-Final-A)")

    def test_k4_binaer_anteil(self):
        self.assertLess(rules._binaer_anteil(self.text), 0.02)
        self.assertGreater(rules._binaer_anteil(self.gross), 0.02)

    def test_k5_manifest_jede_datei_mit_eigener_pruefsumme(self):
        # Punkt 3a (freigegeben 26.09.2026): keine Groessenschwelle mehr. Recherche und Normen
        # sind eindeutig — jede Datei wird einzeln geprueft (NDSA-Survey: 94,9 %).
        zeilen = [z for z in self.listentext.splitlines() if not z.startswith("#")]
        mit_hash = [z for z in zeilen if z.split("  ")[0] != "-"]
        ohne = [z for z in zeilen if z.startswith("-  ")]
        self.assertEqual(len(mit_hash), 3, "ALLE drei Dateien muessen eine Einzelpruefsumme haben")
        self.assertEqual(len(ohne), 0, "keine Datei darf ohne Pruefsumme gelistet sein")
        self.assertTrue(any(z.endswith("gross.bin") for z in mit_hash))
        self.assertTrue(any(z.endswith("klein1.txt") for z in mit_hash),
                        "auch die 1-Byte-Datei braucht eine eigene Pruefsumme")
        self.assertEqual(hashlib.sha256(self.listentext.encode()).hexdigest(), self.erg["aggregat"],
                         "Aggregat passt nicht zum Listentext")

    def test_k6_zeiger_nennt_version_und_einzelpruefsummen(self):
        for feld in ("manifest_version: 3", "einzelpruefsummen_je_datei: ja", "einzelpruefsummen: 3"):
            self.assertIn(feld, self.yamltext)

    def test_k7_aenderung_gleicher_groesse_wird_jetzt_entdeckt(self):
        # Frueher war das die dokumentierte Grenze der Aggregation. Mit Einzelpruefsummen je
        # Datei muss eine Inhaltsaenderung GLEICHER Groesse das Aggregat veraendern.
        (self.quelle / "klein1.txt").write_text("Z", encoding="utf-8")   # gleiche Groesse, anderer Inhalt
        e2 = zeiger_bauen.baue(self.quelle, self.zeiger_name, BAUM)
        self.assertNotEqual(e2["aggregat"], self.erg["aggregat"],
                            "Aenderung gleicher Groesse blieb unentdeckt — Einzelpruefsumme fehlt")
        (self.quelle / "klein1.txt").write_text("a", encoding="utf-8")   # zurueckstellen

    def test_k8_pdfartige_datei_schnell_und_ungeprueft(self):
        # Befund 25.09.2026: eine 2,3-MB-PDF band einen Kern ueber 4 Minuten, weil sie wegen
        # fehlender NUL-Bytes als Text galt. Jetzt entscheidet der Anteil druckbarer Zeichen.
        pdfartig = B / "pdfartig.bin"
        with pdfartig.open("wb") as fh:
            fh.write(b"%PDF-1.7\n" + os.urandom(3 * 1024 * 1024))
        self.assertLess(rules._text_anteil(pdfartig), 0.95, "PDF-artige Datei muss als Binaerdatei gelten")
        t0 = time.time()
        name, ung = rules.scan_secrets(pdfartig)
        dt = time.time() - t0
        self.assertTrue(ung)
        self.assertIsNone(name)
        self.assertLess(dt, 20.0, f"PDF-artige Datei dauerte {dt:.1f}s — Grenze wirkt nicht")

    def test_k9_zeitbudget_meldet_ungeprueft(self):
        # Ein Lauf darf nicht unbegrenzt rechnen: nach dem Budget gilt der Rest als UNGEPRUEFT.
        alt = rules.MUSTER_ZEITBUDGET
        altstand = list(rules._scan_budget_stand)
        try:
            rules.MUSTER_ZEITBUDGET = 0.0
            rules._scan_budget_stand[0] = time.monotonic() - 5.0      # Fenster liegt in der Vergangenheit
            rules._scan_budget_stand[1] = 0.0
            self.assertEqual(rules.scan_secrets(self.text), (None, True))
            self.assertGreater(rules._scan_budget_stand[1], 0.0)
        finally:
            rules.SECRET_SCAN_BUDGET = alt
            rules._scan_budget_stand[0], rules._scan_budget_stand[1] = altstand


class FrischbaumTor(unittest.TestCase):
    """DAS GESETZ DES PROJEKTS (26.09.2026): ein frisch aus dem Repo erzeugter Baum muss beim
    ERSTEN `pruefen` 0 Fehler melden. Grund: ein unabhaengiger Pruefer hat reproduziert, dass ein
    frischer Spross-Baum 'verfolgt, aber NICHT in PRUEFSUMMEN_MASTER.txt' meldete, weil 'summen'
    die Selbstbeschreibung ERST NACH 'git add' erzeugte. Die Alt-Suite etappe39 prueft nur, dass
    'STATUS: CRITICAL' NICHT vorkommt — deshalb blieb der Fehler unsichtbar. Hier wird die
    Zusage ausdruecklich verlangt: 0 Fehler, kein ERROR, kein CRITICAL.
    """

    def test_f1_frischer_spross_ist_beim_ersten_pruefen_gruen(self):
        ziel = B / "Frischbaum"
        if ziel.exists():
            shutil.rmtree(ziel)
        p = r(f"bash {BAUM}/spross.sh {ziel} Frischbaum", cwd=BAUM, zeit=900)
        self.assertEqual(p.returncode, 0, p.stdout[-400:])
        c = r(f"cd {ziel} && ./ordner.sh pruefen", zeit=900)
        self.assertIn("0 Fehler", c.stdout, f"frischer Baum meldet keine 0 Fehler:\n{c.stdout[-800:]}")
        self.assertNotIn("STATUS: ERROR", c.stdout)
        self.assertNotIn("STATUS: CRITICAL", c.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)

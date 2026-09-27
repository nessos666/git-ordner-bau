# BAUPLAN AUSBAU — 5 Schritte (Stand 23.09.2026)

**Ziel:** den Git-Ordner-Baum Stück für Stück besser machen — **nicht** komplizierter.
**Regel für jeden Schritt (wie bisher):**

1. Behebt er einen echten Mangel? Nein → STOP.
2. Bringt er ein neues Konzept/Werkzeug/Format mit? Ja → vorher David fragen.
3. Kann ich ihn mit **einer Zahl** belegen? Nein → STOP.
4. Wird etwas **außerhalb** des Sandkastens verändert? Ja → STOP.
5. Am Ende: alle Suiten grün? Commit? Fortschritt dokumentiert? Sonst darf ich es nicht „fertig" nennen.

**Reihenfolge:** vom Kleinen zum Größeren. Nach **jedem** Schritt: messen, dokumentieren, committen.

---

## Schritt 1 — Git-Wartung (fertig 23.09.2026)

| | |
|---|---|
| **Ziel** | Der Baum bleibt über Jahre schnell und stabil; Git räumt sich selbst auf |
| **Änderung** | `git commit-graph write --reachable` + `git gc` **von Hand** (kein Cron — David will keine Vollautomatik) |
| **Beweis (gemessen)** | Repo **1,7 MB → 544 KB** · lose Objekte **140 → 0** · Commit-Graph angelegt (2.672 B) · `git fsck` sauber |
| **Risiko** | keins (nur committete Daten, nichts gelöscht) |
| **Wiederholen** | etwa monatlich: `git gc` im Baum — in `ANLEITUNG.md` festgehalten |
| **Offen** | 2 unreferenzierte Tags (Reste vom Umhängen) werden von Git später selbst entfernt |

## Schritt 2 — Redundanz-Prüfung (FERTIG 23.09.2026)

| | |
|---|---|
| **Ziel** | Der Baum **sagt** dir, ob eine zweite Kopie existiert und wie alt sie ist — statt es nur zu behaupten |
| **Änderung** | Neue Prüfung in `rules.py`: liest `50_INFRA/redundanz.yaml` (Liste erwarteter Kopien) und meldet: gefunden / fehlt / veraltet (Prüfsummen-Vergleich gegen `PRUEFSUMMEN_MASTER.txt`) |
| **Beweis (gemessen)** | Statuszeile vorher `REDUNDANZ: FEHLT` (feste Annahme) → jetzt `1 Kopie(n), aktuell — GLEICHE PLATTE (…)`; Rot-Proben: Kopie älter → `VERALTET`, Kopie weg → `FEHLT` |
| **Nutzen für P0** | sichtbarer Fortschritt, ohne etwas zu kaufen: der Baum unterscheidet **„Kopie auf gleicher Platte"** (schützt vor Fehlern) von **„Kopie außerhalb"** (schützt vor Plattenausfall) |
| **Risiko** | klein; reine Lese-Prüfung |
| **Aufwand** | klein (1 Regel + 3 Tests) |
| **Ergebnis** | `50_INFRA/redundanz.yaml` erklärt die Kopien; Statuszeile misst jetzt: `REDUNDANZ: 1 Kopie(n), aktuell — GLEICHE PLATTE (schuetzt vor Fehlern, NICHT vor Plattenausfall)` · Tests e1 aktuell / e2 VERALTET / e3 FEHLT |

## Schritt 3 — Stabile Nummern für Projekte (Johnny.Decimal-Prinzip) — FERTIG 24.09.2026

| | |
|---|---|
| **Ziel** | Umbenennen bricht nie wieder einen Pfad: die **Nummer** bleibt, der Name darf sich ändern |
| **Änderung** | Konvention für **neue** Projektordner: `20_PROJEKTE/021_island_sprache_2026-09-23` · K6-Regel prüft die Nummer; **bestehende** Ordner werden **nicht** umbenannt |
| **Beweis (gemessen)** | Werkzeug vergibt `001_…`, zweites Projekt `002_…`; **doppelte Nummer = ERROR**; nicht dreistellig = HINWEIS; unerlaubter Name wird abgewiesen (nichts angelegt). 5 Tests g1–g5 grün |
| **Risiko** | klein, wenn nur neue Ordner betroffen sind (Regel: nichts Bestehendes anfassen) |
| **Aufwand** | mittel |
| **Ergebnis** | `./ordner.sh projekt "name" [bereich]` legt Projekt mit Nummer + STATUS.md + Katalog-Eintrag an; **bestehende Ordner bleiben unangetastet** |

## Schritt 4 — Schnell finden und springen — FERTIG 24.09.2026

| | |
|---|---|
| **Ziel** | schnelles Finden und Springen im Terminal |
| **Änderung** | zwei kleine Werkzeuge installieren, 3 Zeilen in der Anleitung |
| **Beweis** | Suchdauer vorher/nachher auf demselben Ordner |
| **Risiko** | keins (Werkzeuge außerhalb des Baums) |
| **Ergebnis** | **Keine Installation nötig** — gemessen: `fdfind` und `fzf` sind bereits installiert. Neu: `./ordner.sh dateien "muster"` (Dateinamen im Baum **und** in den angebundenen Beständen) und `./ordner.sh springen "muster"` (Auswahlliste, mit fzf Pfeiltasten). Rückfall fdfind → rg → find; läuft auch **ohne PyYAML** (eingebauter Rückfall). 4 Tests h1–h4 grün |
| **Aufwand** | sehr klein — **nur wenn David es will** |

## Schritt 5 — Inhalte der Außenprojekte durchsuchbar (Teil 1 FERTIG · Teil 2 = Recoll, Davids Entscheidung)

| | |
|---|---|
| **Ziel** | Die eine Lücke schließen: echte Projekte sind im Baum nur **auffindbar**, nicht **durchsuchbar** |
| **Änderung** | Recoll indexiert die Inhalte der Außenprojekte (Inhaltssuche über PDF/DOCX/…); keine Daten in Git |
| **Beweis** | Suche nach einem Begriff, der nur **im Inhalt** eines Außenprojekts vorkommt → Treffer mit Datei + Pfad |
| **Risiko** | Index liegt lokal; Start-/Laufzeitkosten abhängig von Projektgröße |
| **Aufwand** | mittel (1× einrichten) — **Installation entscheidet David** |
| **Teil 1 (fertig 23.09.2026)** | `./ordner.sh finden "begriff"` durchsucht den **Inhalt** der Zeiger-Ziele, nur lesend, **ohne jede Installation** (nutzt das vorhandene `rg`). Probe an echten Daten: Island-Dossier 312 Dateien/94 MB → Treffer; Gegenprobe → `0 Treffer`. Tests f1–f4 grün. |
| **Teil 2 (fertig 24.09.2026, ohne Installation)** | PDF via `pdftotext`, DOCX/ODT/XLSX/PPTX via `libreoffice --headless`, mit Zwischenspeicher in `60_RUNTIME/dokumenttext/`. Messung: 16 PDFs im Island-Dossier → Treffer **im PDF-Text**; 1,5 s → 0,1 s beim zweiten Lauf. Ein kaputtes PDF wird **gemeldet**, nicht verschwiegen (Test f6). Recoll bleibt optional (`50_INFRA/RECOLL_ANLEITUNG.md`) — Installation braucht Davids Passwort |

---

## Was ausdrücklich NICHT passiert

- Keine neue Architektur, keine neue Datenbank, kein neues Format.
- Kein Cron/keine Automatik ohne Davids ausdrückliche Entscheidung.
- Kein Anker: bestehende Ordner/Projekte werden **nicht** umgebaut.
- Keine Daten > 10 MB in Git (Regel K1).

## Stand der Beweise (23.09.2026)

```
Schritt 1: fertig   · gemessen: 1,7 MB -> 544 KB, fsck sauber
Schritt 2: fertig  · gemessen: "1 Kopie(n), aktuell — GLEICHE PLATTE"; Tests e1-e3 grün
Schritt 3: fertig  · Werkzeug + 5 Tests (g1-g5) grün
Schritt 4: fertig (fdfind/fzf waren schon installiert)
Schritt 5: fertig (Text + PDF/DOCX, ohne Installation) · Recoll = optionale Zugabe
Suiten:    14/14 grün (224 Einzeltests) · Baum: 0 Fehler · Tag v0.2.15-prototyp
```

---

## Nachtrag 2026-09-24 — Element 1 aus der Recherche: Duplikat-Bericht

| | |
|---|---|
| **Ziel** | zeigen, wie viel Speicher durch identische Dateien belegt ist — ohne etwas zu löschen |
| **Änderung** | `./ordner.sh doppelt <Pfad>` (Pfad **Pflicht**), `70_AUTOMATION/pointers/doppelte.py`, 6 Tests (i1–i6) |
| **Beweis (gemessen)** | `03_PROJEKTE` 53.086 Dateien/10,83 GB → **13.276 doppelte Dateien = 1,395 GB in 2,9 s**; davon **1,303 GB wiederherstellbar** (venv) |
| **Passt ins System?** | Ja — Bericht, keine Regel: keine neue Datenbank, K1–K8 unverändert, kein Cron, nur lesend |
| **Drei Fallen vermieden** | Hardlink ≠ Dublette (eigener Test i2) · zweistufige Prüfung (Kopf 64 KB → voll) · Unlesbares wird gemeldet (i4) |
| **Urteil** | baut den Baum nicht komplizierter, liefert aber die erste handfeste Zahl für Speicher-Einsparung |

---

## Nachtrag 24.09.2026 — Elemente 2, 3, 4 aus der Recherche

| Element | Was | Beweis |
|---|---|---|
| **2 RO-Crate 1.1** | `./ordner.sh crate` schreibt `ro-crate-metadata.json` (jede Datei mit sha256, Groesse, Datum); `pruefen` rechnet nach | c1-c4 gruen: gueltig · Aenderung erkannt · Arbeitsdaten (`60_RUNTIME`) bleiben draussen |
| **3 Vorlagen** | `80_VORLAGEN/vorlagen.json` + `./ordner.sh vorlage <Ordner> <name>` | v1-v3 gruen: angelegt · unbekannte Vorlage stoppt · **nichts ueberschrieben** |
| **4 BagIt (RFC 8493)** | `./ordner.sh bag <Quelle> <Ziel>` erzeugt normgerechtes Bag (bagit.txt + manifest-sha256 + bag-info + data/) | b1-b4 gruen: Aufbau normgerecht · VALID · Manipulation erkannt · fehlende Datei erkannt |
| **Reste** | `README.md` (DoD-Punkt 7) · Testreste `tmp*` werden jetzt von `alle_suiten.sh` aufgeraeumt | 4 Reste automatisch entfernt |

**Warum das nicht komplizierter macht:** kein neues Konzept im Pruefer (K1-K8 unveraendert),
keine neue Datenbank, kein Cron. RO-Crate/BagIt sind **Normen**, die es schon gibt — wir sprechen sie
jetzt, statt eine eigene Sprache zu erfinden.

---

## Nachtrag 24.09.2026 — Nachbesserungen (Rollentrennung, Stichprobe, Bestands-Crate, Sicherung)

| Nr. | Vorher | Jetzt | Beweis |
|---|---|---|---|
| 1 | `ROLLENTRENNUNG: NICHT VERIFIZIERT` (in jeder Pruefzeile) | gemessen: **VERIFIZIERT, 418 Dateien, 0 Schreibspuren** | `50_INFRA/rollentrennung.yaml` + Tests t1/t2 |
| 2 | Zeiger ueber 50 MB: "NICHT einzeln geprueft" | **Stichprobe 16 von 312** einzeln nachgerechnet, Manipulation = Fehler | Live-Ausgabe + Test t3 |
| 3 | Crate nur im Baum | auch fuer **angebundene Bestaende** (`--zeiger <name>`) | Test t4, Island-Crate GUELTIG |
| 4 | Sicherung ohne Norm | `sicherung.sh kopie <ZIEL> --bag` | Test t5: BagIt VALID |

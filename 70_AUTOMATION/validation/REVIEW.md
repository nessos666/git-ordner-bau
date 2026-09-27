# REVIEW — Selbstprüfung nach Phase 17  ·  PROTOTYPE

## Gefundene und behobene Fehler im eigenen Code (während des Baus)
| # | Fehler | Auswirkung | Behebung |
|---|---|---|---|
| 1 | `rel()` lieferte für die Wurzel den **Absolutpfad** | K7 meldete die MASTER-Wurzel selbst als „Tiefe 6" | `relative_to(root)` mit `"."` für die Wurzel |
| 2 | K4 nutzte `e["pfad"]` direkt | **KeyError** bei unvollständiger Katalogzeile (Absturz statt Meldung) | fehlendes Feld wird K5 überlassen, K4/K3 überspringen |
| 3 | K8 verlangte SHA-256 auch **unter** 10 MB | widersprach der eigenen 10-MB-Schwelle (Falschalarm) | `sha256` muss als *Feld* da sein; *Wert* nur > 10 MB Pflicht |
| 4 | K6 prüfte den ganzen Pfad inkl. `00_SYSTEM` | 11 Falschalarme (Großbuchstaben der Bereichsnamen) | Bereichspräfix ausgenommen, nur selbst vergebene Namen geprüft |
| 5 | Default-Wurzel `parents[2]` | Prüfer zeigte auf den Sandkasten statt auf MASTER | `parents[1]`; der Prüfer meldete den Fehler selbst als CRITICAL |
| 6 | Fixture-Bau: Basis **nach** den Repos | Fixtures wurden sofort gelöscht → Selbsttest blind | Reihenfolge korrigiert (Basis zuerst) |
| 7 | Fremd-Repo **verschachtelt** im Projekt-Repo | Gitlink/Submodul (v1.3: nicht empfohlen) | Repo herausgelöst, Index bereinigt |
| 8 | K2 schlug auf **meine eigenen Testfixtures** an | korrektes Verhalten, aber Secret-Literal im Repo | Muster wird zur Laufzeit zusammengesetzt |

## Vom Prüfer gefundene, nicht behobene Punkte (bewusst)
* **REDUNDANZ: FEHLT** — nur ein Datenträger. Der Prüfer sagt es ehrlich, statt „OK".
* **P0** (zweite Kopie) bleibt eine **Anschaffung**, kein Designproblem.
* **Keine Netzprüfung** von `remote`-Werten (Offline-Prototyp).
* Fixtures liegen **außerhalb** MASTER (`../fixtures/`), damit der Hauptbaum sauber bleibt.
* `make_fixtures.py` nutzt `rmtree` — **ausschließlich** unter `fixtures/` (mit `assert`).
* Der Prüfer schreibt genau **zwei** Dateien: Quittung + Herzschlag in `60_RUNTIME/state/`
  (durch `test_38` auf genau 2 Schreibaufrufe festgenagelt).

## Interpretationsentscheidungen (offengelegt, nicht stillschweigend)
1. **`extern: true` darf unter `20_PROJEKTE` liegen** (vendor) — sonst wäre die Klassen↔Bereich-Prüfung
   für fremde Abhängigkeiten nicht erfüllbar.
2. **K1 prüft die vom Repository geführten Dateien** (`git ls-files`), nicht den Ordnerinhalt —
   sonst wären ignorierte Caches ein Falschalarm.
3. **`10_AGENT` ist Ziel-Struktur**, im Betrieb liegt der Bestand in `~/.hermes/` (v1.3 §6).

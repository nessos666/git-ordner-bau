# TESTLAUF C — echte Projekte (23.09.2026)

**Aufbau:** frische Instanz `_TESTLAUF_C/MASTER` (kein alter Stand) · 10 echte Projekte aus `03_PROJEKTE`
als **Zeiger** (2,14 GB, 42.377 Dateien) · zusätzlich **ein echtes Projekt als Kopie** im Baum
(`666_OSINT`: 1.508 Dateien, 9,9 MB, **6 eigene Repos**) — Originale nur gelesen.

## Was gemessen wurde
| Schritt | Ergebnis |
|---|---|
| 10 Zeiger bauen (Prüfsummen aller Dateien + Zeiger-Datei) | 9,9 s (2 GB gehasht) |
| Vollprüfung mit 10 Zeigern | 8,0 s · 140 geprüft |
| Projektkopie 1.508 Dateien | 0,3 s |
| Vollprüfung mit Projektkopie | 9,7 s · 975 geprüft · 109 Fehler |

## Fund 1 — „Datei" war nicht eindeutig definiert (BEHOBEN)
Drei Projekte meldeten „Dateizahl weicht ab: Zeiger 13064, gefunden 13067". Ursache gemessen: jedes
Projekt enthielt **4 Symlinks**; die Liste zählte nur reguläre Dateien, der Prüfer auch auflösbare
Symlinks. Zwei Stellen, zwei Definitionen. **Fix:** eine einzige Definition
(`rules.zaehle_objekt`) für Werkzeug UND Prüfer; tote Verweise zählen nicht als Datei und werden
als Hinweis gemeldet. Belegt durch 2 neue Dauer-Tests (`c1`, `c2`), Suite 8/8.

## Fund 2 — Prüfsummen-Listen sprengten `40_DATEN` (BEHOBEN)
Design: `40_DATEN` unter 1 MB (Zeiger, keine Daten). Mit 10 echten Projekten wurden daraus
**5,57 MB** → Fehler. **Fix:** abgeleitete Listen liegen jetzt in `60_RUNTIME/zeiger/`
(nie versioniert, jederzeit neu erzeugbar); `40_DATEN/manifests` bleibt als Rückfallweg.
Neues Werkzeug `70_AUTOMATION/pointers/zeiger_bauen.py` + `./ordner.sh zeiger <Pfad>` erzeugt
beides automatisch — damit können Werkzeug und Prüfer nicht mehr auseinanderlaufen.

## Fund 3 — Symlink im Ziel ließ die Regel abstürzen (BEHOBEN)
Ein Symlink im Zielobjekt führte zu `CRITICAL: SandkastenVerletzt: Special File (0o120000)` —
die gehärtete Öffnung verweigert Nicht-Regulär-Dateien, die Prüfung brach ab. **Fix:**
`sha256_datei_ziel()` liest bei einem Symlink bewusst das **Ziel** (nur lesen, nie schreiben);
die Schreib-Schranken bleiben unverändert. Belegt durch Test `c2`.

## Fund 4 — ECHTE PROJEKTE PASSEN NICHT UNVERÄNDERT IN DEN BAUM (offene Design-Frage)
Die Projektkopie erzeugte **109 Fehler**, davon über 100 aus zwei Breiten-/Tiefen-Regeln:
- **K7 Tiefe ≤ 5 ab MASTER-Wurzel**: echte Projekte haben Tiefe 6–7 (`fälle/…/03_rohdaten/bilder`)
- **K6 Breite ≤ 20 Einträge**: echte Projektordner haben 23 Unterordner

Das ist kein Programmfehler — die Regeln tun, was v1.3 sagt („keine Ausnahmen"). Es heißt:
**ein echtes Projekt mit eigener, gewachsener Struktur kann nicht unverändert in den Baum kopiert
werden**, ohne es umzubauen — und Umbauen widerspricht „nichts anfassen".

**Empfehlung:** echte Projekte bleiben, wo sie sind, und werden über **Zeiger** angebunden
(genau der Weg, der heute fertig und geprüft ist: A-Prüfung + `ordner.sh zeiger`).
`20_PROJEKTE` im Baum enthält nur flache, baum-eigene Projektordner (`JJJJ-MM-TT_name`).
**Entscheidung liegt bei David** — sie berührt K6/K7 in v1.3 (FROZEN), also nur über
`CHANGELOG_DESIGN.md`.

## Nebenfund
Die Projektkopie zeigte **K4 UNTERREPOS: 5 Repo(s)** als Hinweis statt 107 Fehler — B wirkt an
echten Daten. Und: der Katalogeintrag selbst wurde korrekt abgewiesen (Name `666_OSINT` verletzt
das Namensschema) — die Prüfung greift also auch gegen mich.

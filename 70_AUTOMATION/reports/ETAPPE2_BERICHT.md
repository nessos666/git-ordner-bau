# ETAPPE 2 — BERICHT (Prototyp Git-Architektur v1.3)

**Ort (damals):** `~/prototyp_git_ordner/` — Ordner am 23.09.2026 geloescht; heutiger Sandkasten: `~/HAUPTLAGER/03_PROJEKTE/55_Git_Ordner_Prototyp/` · **Status: PASS MIT EINSCHRAENKUNG** (Einschraenkung: P0 zweite Kopie fehlt)
**Sandkasten-Regel eingehalten (damals):** alle Schreibzugriffe innerhalb `~/prototyp_git_ordner/` (heute: `…/55_Git_Ordner_Prototyp/`) — produktive Pfade nur read-only.

## 1. Messungen Skalierung (synthetische, K7-konforme Baeume)

| Objekte | Dateien | Aufbau | Validator (Engine) | Validator (CLI) | Index | Indexgroesse | Dokumente | Suche ø | Suche max | Speicher | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1,000 | 1,002 | 0.02 s | 0.004 s | 0.077 s | 0.033 s | 0.418 MB | 1,003 | 0.7 ms | 1.1 ms | 26.8 MB | STATUS: OK |
| 10,000 | 10,002 | 0.23 s | 0.034 s | 0.1 s | 0.275 s | 5.132 MB | 10,003 | 3.8 ms | 5.1 ms | 29.3 MB | STATUS: OK |
| 100,000 | 100,002 | 2.2 s | 0.355 s | 0.423 s | 2.714 s | 41.796 MB | 100,003 | 39.7 ms | 51.2 ms | 28.1 MB | STATUS: OK |
| 250,000 | 250,002 | 5.59 s | 0.927 s | 0.96 s | 7.146 s | 95.064 MB | 250,003 | 107.3 ms | 134.9 ms | 29.1 MB | STATUS: OK |

Bemerkung: `Validator (Engine)` = Laufzeit des Regelwerks im Prozess (ohne Python-Start),
`Validator (CLI)` = ganzer Prozessaufruf inkl. Selbsttest.

## 2. Lastgrenzen (realistisches Projektmuster, echte Katalogform)

| Projekte | Validator | Befunde | Index | Indexgroesse | Suche ø | Speicher |
|---|---|---|---|---|---|---|
| 10 | 0.003 s | 0 | 0.009 s | 0.057 MB | 0.30 ms | 28.3 MB |
| 50 | 0.012 s | 0 | 0.026 s | 0.09 MB | 0.40 ms | 29.1 MB |
| 100 | 0.023 s | 0 | 0.051 s | 0.135 MB | 0.40 ms | 29.9 MB |
| 420 | 0.102 s | 0 | 0.205 s | 0.365 MB | 0.60 ms | 36.5 MB |

## 3. Index (Phase 1-5)

- SQLite **FTS5**, eine Datei: `60_RUNTIME/cache/index/suche.db` — **CACHE**, nicht Quelle der Wahrheit.
- Vollstaendig loeschbar und neu aus Katalog + Baum aufbaubar (Test 69/70).
- Ausschluesse dokumentiert (siehe `70_AUTOMATION/indexing/README.md`): `60_RUNTIME`, `cache`, `node_modules`, `.venv`, `.git`, Binaerendungen, Dateien > 10 MB, Text je Dokument auf 64 KB begrenzt, Secret-Muster werden nicht kopiert.
- **40_DATEN-Budget:** Grenzwert 1 MB aus v1.3 exakt verwendet — aktuell 1.134 B (**0,11 %**) = PASS. Bei Ueberschreitung wird gemeldet, nichts geloescht.

## 4. Reale Repositories (Phase 8-9) — read-only

| Repository | Typ | Beobachtet |
|---|---|---|
| `~/hermes-stable` | Hermes-bezogen (Quelle der Wahrheit) | HEAD, Branch, Status, Dateizahl |
| `~/HAUPTLAGER/Hermes-Git-Ordner` | aktives Projekt | dito |
| `~/HAUPTLAGER/03_PROJEKTE/54_Selbstorganisierender_Git_Ordner` | Recherche-/Tool-Projekt | dito |

**Beweis:** Fingerabdruck (SHA-256 ueber `.git`-Kerndateien **inkl. `.git/index`** + Working-Tree-Manifest)
vor und nach dem Lesen **identisch** fuer alle drei Repositories. Alle Git-Aufrufe mit `GIT_OPTIONAL_LOCKS=0`
(kein Schreib-Lock, keine Index-Aktualisierung). Adapter enthaelt nur lesende Aufrufe (`status`, `rev-parse`,
`log`, `ls-files`, `remote`) — **0** schreibende Git-Befehle (statisch und durch Test 76 belegt).

## 5. Waechter / Heartbeat / Quittung (Phase 10-11)

Zustaende A-E in der Sandbox simuliert. Ergebnis: `OK` nur bei laufendem Pruefer ohne Befund.
Alter/fehlender Herzschlag, fehlende/alte/beschaedigte Quittung, ausgefallener Waechter, fehlgeschlagener
Selbsttest, wiederholter ERROR → **nie** `OK`, sondern `UNBESTAETIGT` bzw. `CRITICAL`.
Quittung > 7 Tage = UNBESTAETIGT. Kein produktiver Telegram-Versand, kein Cron installiert.

## 6. Red Team (intern, reproduzierbar) — Phase 13/14

`70_AUTOMATION/tests/redteam.py` — 25 Angriffe in 3 Perspektiven (A Daten/Skalierung,
B Git/Isolation, C Waechter/Mensch), jede mit Urteil nach dem Massstab *verhindert ODER erkannt UND
Schaden begrenzt UND Recovery definiert*:
- **PASS**: 22
- **PASS MIT EINSCHRAENKUNG**: 3

## 7. Korrekturen (Phase 15) — Fund → Ursache → Korrektur → Regressionstest

| Fund | Ursache | Minimale Korrektur | Test |
|---|---|---|---|
| Index zerschlagen → Absturz | ungefangener `sqlite3.DatabaseError` | `IndexDefekt` + Selbstheilung bei `build` | 92 |
| provisional liegt liegen | v1.3-30-Tage-Regel nicht implementiert | K5-Frist: >30 T WARNING, >90 T ERROR | 90, 91 |
| ungeschuetzte Loeschpfade | Waechter nur im Skelettbau vorhanden | `nur_sandkasten()` in 5 Modulen, vor jedem Loeschen | 93, 94 |
| Filter `--klasse` wirkungslos | Dateien hatten keine Klasse geerbt | Klasse/Status/Bereich aus Katalog per Pfadprefix | 64 |
| Herkunft falsch erkannt | zu lockere Textsuche | Herkunft nur bei echtem Kopf-Block | 66 |
| `BrokenPipeError` | ungefangene Ausnahme bei Pipe | sauberer Exit | 60 |

## 8. Sicherheit (Phase 16) — PASS

- **Inhaltsaenderungen ausserhalb der Sandbox durch diesen Build: 0**
- 117.456 produktive Dateien geprueft · 96 Laufzeit-Dateien der Plattform (Sitzungszustand, DB/WAL, Heartbeats)
- 11 inhaltlich wirkende Dateien **mit benennbarer Herkunft zugeordnet** (Modell-/Provider-Caches, Cron-Zustand, Desktop-UI-Paste, systemd-Zeitstempel, Hintergrund-Memory-Review) · **UNGEKLAERT: 0**
- 1 Datei nur **Zeitstempel**-beruehrt, Inhalt nachweislich identisch mit HEAD (Blob-Vergleich), Verursacher **nicht zugeordnet**
- Cronjobs-Datei inhaltlich nicht angefasst (kein Prototyp-Job) · neue systemd-Units 0 · produktive Hooks 0
- Fremde uncommittete Aenderungen in `51_Reparaturen_01`/`52_Lokaler_Web_Extraktor` sind **Altbestand (vor der Referenzzeit)**

## 9. Code Review (Phase 17)

0x `shell=True` · 0x SQL per f-string · 0x `os.system`/`eval`/`exec` · 0 hartcodierte Benutzerpfade ·
0x ungeschuetzte Datei-Schreibzugriffe · `followlinks` nicht aktiv (keine Symlink-Schleife) ·
Exitcodes geprueft (Validator 0-3, Index 0-2) · keine Rekursion · Ausnahmen dokumentiert gefangen.

## 10. Tests

| Suite | Ergebnis |
|---|---|
| Etappe 1 (Regression) | **43/43 OK** |
| Etappe 2 (neu) | **30/30 OK** |
| Gesamt | **73 passed / 0 failed / 0 skipped** |

## 11. Restrisiken

1. `REDUNDANZ: FEHLT` — eine Platte (P0, Anschaffung 60-120 EUR), blockiert jede Schutzwirkung.
2. Index wird nicht automatisch erneuert — bewusst (keine Voll-Automatik); Veralten ist messbar.
3. K4-Scanraum begrenzt auf den Baum; Repositories ausserhalb werden nicht geprueft.
4. Keine Netzpruefung der `remote`-Werte (synthetisch).
5. K6-Datumsregel bleibt Hinweis, kein Verstoss (Altbestand legal).
6. Grosse Cache-Objekte (Artefakt faelschlich als Cache) haben **keinen** Detektor — bewusst nicht ergaenzt (keine neue Regel in v1.3).
7. Kein Index-Schutz gegen gleichzeitigen Zugriff (Einzelprozess-Annahme).
8. Skalierung nur synthetisch gemessen, nicht mit realen 100.000 Projektdateien.
9. Red-Team-Abdeckung endlich (29 Angriffe) — keine Aussage ueber unbekannte Klassen.
10. Textinhalte im Index sind gekuerzt (64 KB/Dokument) — sehr lange Dokumente nur teilweise durchsuchbar.

---

# NACHTRAG — UNABHAENGIGE ABNAHMERUNDE (3 fremde Pruefer) UND IHRE KORREKTUREN

Drei unabhaengige Pruefer haben den REALEN Prototyp angegriffen (nicht das Papierdesign):
**RED TEAM A Daten/Skalierung** · **RED TEAM B Git/Isolation** · **RED TEAM C Waechter/Mensch**.
Berichte: `/home/user/rt2a/BERICHT.md` · `/home/user/rt2b/BERICHT.md` · `/home/user/rt2c/BERICHT.md`.

## Ergebnis der unabhaengigen Runde (vor den Korrekturen)

| Perspektive | CRITICAL FAIL | FAIL | PASS MIT EINSCHRAENKUNG | PASS | Angriffe |
|---|---|---|---|---|---|
| A — Daten, Index, Skalierung | 0 | 11 | 10 | 25 | 46 |
| B — Git, Isolation, Read-only | 2 | 10 | 4 | 12 | 28 |
| C — Waechter, Mensch | 1 | 7 | 12 | 9 | 29 |
| **Summe** | **3** | **28** | **26** | **46** | **103** |

Die Runde war berechtigt und hart. Sie hat u. a. gefunden: **der Pruefer stellte sich die Quittung
selbst aus** (damit waren 26-h- und 7-Tage-Regel aushebelbar), **der Adapter liess schreibende
git-Argumente durch** (`log --output=<pfad>` schrieb ausserhalb), **mein eigener Isolationsbeweis
lief ohne Schreib-Lock ueber die produktiven Repos**.

## Korrekturen (Phase 15: Fund -> Ursache -> minimale Korrektur -> Regressionstest)

| # | Fund (unabhaengig) | Ursache | Minimale Korrektur | Test |
|---|---|---|---|---|
| 1 | C: Quittung selbst ausgestellt, Zustellfehler nicht protokollierbar | Pruefer schrieb `quittung` selbst; Waechter las nur den Zeitstempel | Pruefer schreibt nur `status.json` + Herzschlag; Quittung traegt `zugestellt ok|fehler`; Zustellfehler = CRITICAL | 108, 110 |
| 2 | C: 7 d 23 h 59 m galt als OK | `.days` schnitt ab | volle `timedelta`-Pruefung | 111 |
| 3 | C: Waechter meldete `OK`, waehrend Pruefer `CRITICAL` sagte | Waechter leitete den Stand nicht aus `status.json` ab | Waechter meldet den **bestaetigten Stand**, nie blind OK | 109 |
| 4 | A: Zeigerdatei ohne Mapping toetete den Pruefer (kein Status, kein Herzschlag) | ungepruefte Typen, kein Absturzschutz | Typpruefung + **jede Regel einzeln abgesichert** (Fehler wird CRITICAL-Befund) | 95 |
| 5 | B: `git log --output=` / `config` / `branch` / `symbolic-ref` aendern Repos | Waechter prueft nur `args[0]` | **exakte Befehls-Allowlist** + Options-Verbot + fsmonitor/hooks neutralisiert + `GIT_DIR` entfernt | 104 |
| 6 | B: Symlink-README las `/etc/hostname` | kein Zielcheck | `im_repo()` — Lesen ausserhalb wird verweigert | 105 |
| 7 | B: 3-GB-README → MemoryError, ganzer Lauf stirbt | unbegrenztes Lesen | harte 64-KB-Obergrenze | 106 |
| 8 | B: `--root <fremd>` schrieb Zustand/Cache dort | Sandbox-Pflicht nur im Skelettbau | Pruefer und Indexer **verweigern** Wurzeln ausserhalb; Suche/Status nur lesend | 103, 107 |
| 9 | A: neue Datei in `20_PROJEKTE` liess den Index „nicht veraltet" | Frische nur in 2 Bereichen, Sekundenvergleich | Frische ueber **den ganzen Baum** (Ordner-Zeitstempel), numerisch statt Zeichenkette | 102 |
| 10 | A: gueltige, aber leere DB galt als Index | keine Plausibilitaet | leere/ausgeraeumte DB = defekt, klarer Hinweis | 100, 101 |
| 11 | A: Pfad-Dublette ueber `…/d1/.` | Zeichenkettenvergleich | Normalisierung + `realpath`-Dublettenpruefung | 96 |
| 12 | A: Case-Kollision bei Dateien unentdeckt | K6 gruppierte nur Ordner | K6 vergleicht auch Dateien | 97 |
| 13 | A: Secret in 3,2-MB-Datei unsichtbar | 2-MB-Deckel | **blockweiser Stream-Scan** (bis 64 MB), darueber WARNING „nicht geprueft" | 98 |
| 14 | A: Symlink in `40_DATEN` umging das Budget | `rglob` folgt nicht | Symlink-Ziele werden gerechnet + K8-Hinweis | 99 |
| 15 | C: gefaelschte Herkunft (falscher SHA, erfundener Commit) unbeanstandet | die drei Pflicht-Gegenproben fehlten | SHA gegen echten Inhalt, `quelle_commit` per `cat-file -e`, Eingaben geprueft | 115 |
| 16 | C: `REDUNDANZ: vorhanden` fuer leeren zweiten Ort | nur `st_dev`-Vergleich | `_archiv_gefunden()`: echtes Archiv/Manifest noetig | 114 |
| 17 | C: nicht schreibbarer Herzschlag endete als OK | Befund kam NACH der Bewertung | Schreibpruefung vor der Bewertung, Fehler = CRITICAL | 113 |
| 18 | C: beschaedigte Zustellprotokolle toeteten den Waechter | `json.loads` ungeschuetzt | robuste Auswertung -> UNBESTAETIGT | 112 |
| 19 | C: `status_sim` Exit 0 trotz 7x UNBESTAETIGT | keine Erwartungspruefung | Exit 2 bei Abweichung, Exit 0 nur wenn alle Zustaende stimmen | Sim |
| 20 | B: Fangnetz im Isolationsbeweis selbst ohne Schreib-Lock | `git status` ohne `GIT_OPTIONAL_LOCKS` | Beweis laeuft jetzt mit Lock-Schutz | Ph16 |

**Offenlegung:** Ein fremder Pruefer hat waehrend seiner Runde `~/.gitconfig` veraendert
(`core.pager`) und selbst zurueckgesetzt. Ich habe das **selbst nachgeprueft**: Datei ist 236 B,
`git config --global --get core.pager` ist leer, die Differenz zum Sicherungsstand sind genau die
zwei wieder entfernten Zeilen. Kein Produktiv-Repository wurde beruehrt.

## Stand nach den Korrekturen

| Pruefung | Ergebnis |
|---|---|
| Etappe-1-Regression | **43/43 OK** |
| Etappe 2 | **30/30 OK** |
| Regressionstests der unabhaengigen Runde | **21/21 OK** (Tests 95-115) |
| Gesamttests | **94/94 (0 failed, 0 skipped)** |
| Red Team intern (reproduzierbar) | 0 CRITICAL, 0 FAIL, 3 PASS MIT EINSCHRAENKUNG, 22 PASS |
| Waechter-Simulation | 14 Zustaende, alle wie erwartet, nie faelschlich OK, Exit 0 |
| Validator MASTER | `STATUS: OK` · 0 Fehler · Selbsttest ok |
| Adapter (3 echte Repos) | unveraendert: **True** |

**Wichtig und ehrlich:** Die Korrekturen sind durch 21 neue Tests belegt — aber es hat sie noch
**keine frische unabhaengige Runde** geprueft. Das ist der Unterschied zwischen „behoben" und
„von aussen bestaetigt behoben".

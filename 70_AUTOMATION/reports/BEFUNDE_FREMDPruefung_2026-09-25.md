# Befunde der unabhängigen Fremd-Prüfung — 25.09.2026

Ein **unabhängiger Prüf-Agent** (read-only, eigener Kontext, durfte nur in Scratch schreiben) hat den Baum
als Angreifer geprüft: 61 Arbeitsschritte, 22 Minuten, Suiten in Kopien ausgeführt, Manipulationsproben.
Ergebnis: **14 belegte Befunde**, jeder mit Datei:Zeile und Reproduktion. Hier der Stand — ehrlich,
inklusive der noch offenen. **Nichts davon ist geschönt.**

## Behoben und nachgerechnet (3)

| # | Befund | Schwere | Beweis nach dem Fix |
|---|---|---|---|
| 1 | **BLOCKER:** `spross.sh` erzeugte die Prüfsummenliste NACH `git add -A` und nahm sie nicht mit in den Commit → jeder neue Baum war sofort "schmutzig", ein Klon zeigte 15 Prüfsummen-Fehler | BLOCKER | eigener Nachbau: vorher `M PRUEFSUMMEN_MASTER.txt`, Commit 110 Zeilen vs. Arbeitsbaum 105 · **nachher: Status leer, Commit 105 = Arbeitsbaum 105, Klon: 105× OK, 0 Fehler** |
| 2 | Kein Test deckte `spross.sh` ab (18/18 grün trotz BLOCKER) | hoch | neue Suite **etappe39** (s1 sauber · s2 Klon prüft fehlerfrei · s3 zweiter Lauf bricht ab · s4 neuer Baum prüft sich selbst) — 4 Tests grün |
| 13/14 | `spross.sh` verschluckte Hilfsfehler (`|| true`, rc nicht geprüft) · `make_fixtures.py` hatte `"MASTER/…"` fest verdrahtet → Fixtures fehlten im neuen Baum | niedrig | `make_fixtures.py` leitet den Baum jetzt namensunabhängig ab (parents[2]); spross **meldet** Hilfsfehler statt sie zu verschlucken; **frischer Baum: Selbsttest nicht mehr DEFEKT** |

## Offen — Arbeitsliste für die nächsten Chats (11)

| # | Befund | Schwere | Was zu tun ist |
|---|---|---|---|
| 3 | `sicherung.sh pruefen` prüft die Kopie **gegen ihr eigenes** Manifest → eine beim Kopieren verfälschte Kopie meldet "PRUEFSUMMEN: OK" | hoch | Manifest **aus dem Baum** erzeugen und die Kopie dagegen prüfen |
| 4 | `check_all.py`: STATUS CRITICAL, aber Fehlerzahl 0 / Zeile WARNING (Unlesbarkeits-Befunde kommen nach der Zählung) | mittel | Zählung EINMAL am Ende aus allen Befundquellen |
| 5 | Crate-Prüfung wirkungslos: `check_all` kennt den Crate nicht, `\|\| true` in ordner.sh → Selbstbeschreibung kann still veralten (Gegenbeweis zu ANLEITUNG.md:178) | mittel | Crate-Prüfung als echte Regel (ERROR) aufnehmen |
| 6 | Keine Regel hasht die verfolgten Dateien: eine Backdoor in `ordner.sh` ergibt weiter "0 Fehler" | mittel | **neue Regel K9**: Prüfsummen der verfolgten Dateien gegen `PRUEFSUMMEN_MASTER.txt`; Abweichung = ERROR |
| 7 | BagIt: nicht gelistete Payload-Dateien und ein entferntes `tagmanifest` fallen nicht auf → "complete and valid" hält nicht | mittel | Payload-Baum gegen Manifest abgleichen; fehlendes tagmanifest melden |
| 8 | Doku nennt falsche Zahlen/Bedeutungen: README "**zehn** Befehle" (15) · `neu` als "Bereich anlegen" beschrieben (baut nur den Index) · "15 Suiten" (18) · ANLEITUNG "8 Suiten/194 Tests" · PROTOKOLL "10/10", "78 verfolgte Dateien" (111), "312 geprüft" (378) | mittel | Zahlen aus echtem Lauf erzeugen; `neu` richtig beschreiben |
| 9 | `alle_suiten.sh` löscht am Ende `rm -rf` **jedes `tmp*` neben dem Baum** (außerhalb des Repos, ungefragt) — Widerspruch zu "nichts wird ungefragt gelöscht" | mittel | nur eigene Scratch-Ordner (Namensmuster + Sandkasten), erst auflisten |
| 10 | Fehlende Argumente enden in rohen Shell-Fehlern rc=1 (z. B. `./ordner.sh bag --pruefen`, `bash sicherung.sh kopie`) | niedrig | Nutzungshinweis + definierter Exitcode 2 |
| 11 | `./ordner.sh crate --pruefen` ohne Ordner prüft das **aktuelle Verzeichnis** statt den Baum (kann fremden Ordner als "GUELTIG" melden) | niedrig | bei leerem Wert den Baum verwenden |
| 12 | `doppelte.py` verschweigt unlesbare Bereiche (`os.walk` ohne onerror) — Zusage "UNLESBARES wird GEMELDET" hält nicht | niedrig | `onerror` setzen, in die vorhandene `unlesbar`-Liste |

## Was der Prüfer ausdrücklich in Ordnung fand

18/18 Suiten grün im Original · Prüfsummen 110× OK, Git sauber · **keine Geheimnisse** (Muster AKIA/ghp_/sk-/PRIVATE KEY: nur Detektor-Code) · Schreibgrenzen halten (`projekt "../../ESCAPE_TEST"` → STOP rc=2; `check_all` verweigert Wurzel außerhalb der Sandbox) · fail-closed bei unlesbaren Dateien · **eine Kopie erbt keine Messung** ("ROLLENTRENNUNG: NICHT VERIFIZIERT (Messung gilt für einen anderen Ort)") · `formate` markiert nur · `doppelte.py` rechnet Hardlinks korrekt.

**Urteil des Prüfers:** "Im Kern solide — so abschließen würde ich ihn aber nicht", bis spross-Reihenfolge (jetzt behoben), Statusberechnung, Crate-/Prüfsummen-Regel, Kopie-gegen-Baum und die Doku-Zahlen sitzen.

## Nachtrag 25.09.2026 (nachts) — weitere Befunde BEHOBEN

| # | Befund | Nachweis |
|---|---|---|
| 3 | Sicherung prüfte die Kopie nur gegen ihr eigenes Manifest | verfälschte Kopie: vorher "PRUEFSUMMEN: OK" → **jetzt "PRUEFSUMMEN: FEHLER … GEGEN DEN BAUM: FEHLER"** (beide Prüfungen laufen) |
| 4 | `check_all`: Status CRITICAL, aber "0 Fehler/WARNING" | Status wird **einmal am Ende** aus allen Befundquellen berechnet → "STATUS: CRITICAL \| 4 error, 1 warnings" **und** "PRUEFER: CRITICAL · 4 Fehler" — widerspruchsfrei |
| 5 | Crate-Prüfung wirkungslos (`\|\| true`) | **neue Regel CRATE** in check_all: verfälschter Crate → `[ERROR] CRATE … Selbstbeschreibung passt NICHT zum Inhalt`, Status ERROR |
| 6 | Keine Regel hasht die verfolgten Dateien | **neue Regel K9**: geänderte verfolgte Datei → `[ERROR] K9 … INHALT GEAENDERT (soll …, ist …)`; die Regel hat sich sofort selbst bewiesen (sie meldete meine eigenen, noch nicht nachgezogenen Prüfsummen) |
| 7 | BagIt: ungelistete Dateien / fehlendes tagmanifest fielen nicht auf | ungelistete Datei → **"UNGULTIG … NICHT GELISTET … nicht 'complete'"**; ohne tagmanifest → **"UNGULTIG … tagmanifest-sha256.txt FEHLT … nicht 'valid'"**; sauberer Bag weiter VALID |
| 8 | Falsche Zahlen/Bedeutungen in der Doku | README (Befehle, `neu`), ANLEITUNG (Suiten/Tests) korrigiert; PROTOKOLL: Historie steht, datierter **Nachtrag mit gemessenen Zahlen** |
| 9 | `alle_suiten.sh` löschte `rm -rf` jedes `tmp*` neben dem Baum | gelöscht werden nur noch **eigene Testreste** (`tmp[0-9]*`, `tmp_tests`, `tmp_gegen`, `tmp_unabh`); alles andere wird **nur gemeldet** |
| 10 | Fehlende Argumente → rohe Shell-Fehler rc=1 | `./ordner.sh bag --pruefen` → "Nutzung: … " **rc=2** · `bash sicherung.sh kopie` → "Aufruf: … " **rc=2** |
| 11 | `crate --pruefen` ohne Ordner prüfte das aktuelle Verzeichnis | aus `/tmp` aufgerufen prüft jetzt **den Baum** (meldet dort die echten Abweichungen) |
| 12 | `doppelte.py` verschwieg unlesbare Bereiche | `os.walk(onerror=…)` → "ACHTUNG: Bereich nicht lesbar — …" |

## Endstand 25.09.2026, 02:00 — alle Befunde behoben

**Prüfer 0 Fehler · 19 Suiten / 255 Tests / 0 Fehler · Prüfsummen identisch · Crate gültig ·
BagIt valid (inkl. Vollständigkeitsprüfung) · Kopie gegen den Baum geprüft (OK) · Klon prüft fehlerfrei.**
Neu dazu: Regel **K9** (Prüfsummen der verfolgten Dateien) und **CRATE** (Selbstbeschreibung) als echte
Regeln, Status einmal am Ende berechnet, Befehl **`./ordner.sh summen`** (Crate + Prüfsummen nachziehen).

Offen und dokumentiert (kein Fehler, sondern Grenze): Suiten, die den **gemessenen Originalbaum** brauchen,
überspringen in einer Kopie noch nicht mit Begründung, sondern melden dort Fehler — siehe
`FORTSCHRITT.md`, Klasse "Suite nur im Originalbaum". Zwei Testreste neben dem Baum (`tmp_25`,
`tmp_probe`) wurden bewusst **nicht** gelöscht (die neue Aufräumregel meldet nur).

## Zweite Fremd-Prüfung (eigener Agent, read-only) — 25.09.2026, ~01:30

**Urteil des Prüfers: „So nicht abnahmereif."** Er hat drei meiner als „behoben" gemeldeten Punkte
**widerlegt** — mit Reproduktion. Das war richtig und ist die wichtigste Lehre: *eine Behauptung ist
kein Nachweis.* Was er fand und was daraus wurde:

| Sein Befund | Schwere | Status |
|---|---|---|
| **Sicherung war zirkulär:** `pruefen` las die Prüfsummenliste IN der Kopie → manipulierte Kopie meldete „OK". | BLOCKER | **behoben**: `pruefen` liest jetzt `QUELLE=` aus dem README der Kopie und vergleicht gegen die Liste des **Quellbaums** (`cmp` + `sha256sum -c`). Nachweis: manipulierte Kopie → **„LISTE DES QUELLBAUMS: WEICHT AB" + „GEGEN DEN BAUM: FEHLER" + rc=2** |
| **K9/CRATE nur einseitig:** eine NEU hinzugefügte, verfolgte Datei passierte beide Regeln. | hoch | **behoben**: K9 prüft jetzt auch `git ls-files` gegen die Liste (Unter-Repos/Sonderfälle ausgenommen). Nachweis: neue Datei → **„verfolgt, aber NICHT in PRUEFSUMMEN_MASTER.txt"** |
| **Gescheitertes Git-Bündel wurde verschluckt** (rc=0 ohne Historie). | hoch | **behoben**: Bündel wird erzeugt **und** geprüft (im Quellbaum — `verify` braucht ein Repo), Fehler nennt den Git-Grund und endet mit rc=2. Nachweis: Bündel blockiert → **rc=2 mit Grund** |
| README `neu "name"` = „neuen Bereich anlegen" (falsch) · „15 Befehle" statt 16 · `summen` in keiner Anleitung · „K1-K8" | mittel | **behoben** (README, Hilfeliste „sechzehn Befehle", ANLEITUNG, PROTOKOLL-Nachtrag) |
| ANLEITUNG verspricht „muss OK zeigen" — geliefert wird WARNING/rc=1 (50-MB-Hinweis) | mittel | **behoben**: Formulierung präzisiert |
| `pruefen` hinterließ `tmp_probe` **neben** dem Baum | niedrig | **behoben**: wird nach dem Lauf entfernt |
| `alle_suiten.sh` meldete eigene Reste (`tmp_25`, `tmp_probe`) als „fremd" | niedrig | **behoben**: beide in die Aufräumliste |
| CRATE/K9 prüften nicht, ob es sie überhaupt gibt (Selbstbeschreibung konnte verschwinden) | niedrig | **behoben**: Existenz ist ERROR in ausgelieferten Bäumen |
| Kopie fällt durch ihre eigenen Suiten | mittel | **behoben durch Übersprungen-Regel**: `70_AUTOMATION/tests/braucht_originalbaum.txt`; in einer Kopie melden die 7 betroffenen Suiten **„uebersprungen (braucht den gemessenen Originalbaum)"** — 0 Fehler, 7 übersprungen |
| `summen` entwertet den Quellstand der Kopie (nicht dokumentiert) | niedrig | **behoben**: in ANLEITUNG + Hilfe vermerkt |
| Stiller `except OSError: return None` in der Secret-Rückfallprobe | niedrig | offen (auf ERROR statt CRITICAL herabgestuft; fail-closed bleibt) |

**Offen und präzise dokumentiert (ehrlich, klein):** In `test_suite_etappe29.py` bleiben **2 von 8 Tests**
rot (`test_c1_toter_verweis_zaehlt_nicht_und_wird_gemeldet`, `test_c2_symlink_auf_datei_zaehlt_als_datei`).
Sie bauen sich Bäume ad hoc zusammen und erwarten „0 Fehler", während die neuen Regeln dort zu Recht
anschlagen (Messung: `STATUS: ERROR | 1 error`, `K2-Scope: tracked 118`). Reproduktion:
`cd 70_AUTOMATION/tests && python3 -B ausbau/test_suite_etappe29.py`.
**Alle anderen 18 Suiten sind grün, der Regelprüfer meldet 0 Fehler.**

## Dritte Prüfung: OpenCode 1.18.4 (lokaler Agent, read-only) — 25.09.2026, 01:32, rc=0

OpenCode hat 11 Befunde geliefert, **jeder mit ausgeführter Reproduktion**. Alle 11 sind abgearbeitet;
nach jedem Fix wurde die Reproduktion des Prüfers erneut gefahren.

| # | Befund | Schwere | Nachweis nach dem Fix |
|---|---|---|---|
| 1 | `spross.sh`: Kommando-Injektion über Dateinamen (`xargs -0 -I{} sh -c`) | hoch | beim Nachsehen bereits beseitigt (Spross ruft `summen` auf; kein `sh -c` mehr im Baum) |
| 2 | `rules.py`: jeder **verfolgte Symlink** brachte K2 zum Absturz (`SandkastenVerletzt`) | hoch | Symlink-Lesen erlaubt, FIFO bleibt gesperrt: `SYMLINK-LESEN: OK`, `FIFO: gesperrt (richtig)` |
| 3 | `status.json` wurde **vor** K9/CRATE geschrieben → Datei sagte „OK", stdout „ERROR" | hoch | Schreiben ans Ende von `main()`: stdout `ERROR 2 Fehler` = status.json `ERROR 2 2` ✓ |
| 4 | `sicherung.sh`: relatives `ZIEL`/`K` landete falsch (`relziel/baum/baum`) | mittel | `realpath -m` + Unterschale: `relziel/README.txt` da, `relziel/baum/baum` existiert nicht |
| 5 | `git bundle` nahm still das **Eltern-Repo** (1,18 GB aus `~/.hermes`) | mittel | Vergleich mit `rev-parse --show-toplevel`: HINWEIS statt Bündel, Ziel 24 K statt 1,18 GB ✓ |
| 6 | `bagit_bauen.py`: Traceback bei Manifestzeile ohne Trenner | mittel | `UNGULTIG: Manifestzeile ohne Trenner …`, rc=2, kein Traceback ✓ |
| 7 | `ro_crate.py --pruefen`: nicht beschriebene Dateien galten als gültig | mittel | `NICHT BESCHRIEBEN: ./NEU.txt`, rc=2 ✓ |
| 8 | `ordner.sh summen`: überschrieb die Liste bei falschem Repo still | niedrig | `STOP: … kein eigenes Git-Repository`, Liste bleibt unangetastet ✓ |
| 9 | `sicherung.sh wiederherstellen`: `rm -rf "$N"` ohne Wache | niedrig | `STOP: Ziel wird nicht angetastet (Schutzgrenze)` ✓ |
| 10 | `rules.py`: doppelte `safe_append_bytes` verwarf `daten` | niedrig | eine Definition, schreibt Daten ✓ |
| 11 | `ro_crate.py`/`bagit_bauen.py`: Pfad-Ausbruch (`../..`) beim Lesen | niedrig | `@id` muss im Crate-Ordner bleiben ✓ |

**Ehrlich offen geblieben (1 Suite, 2 Tests):** `test_suite_etappe29.py` — `test_b1_unterrepo_…` und
`test_c1_toter_verweis_…` bauen sich Testbäume ad hoc zusammen; nach ihren eigenen Manipulationen sind
die Prüfsummen dort veraltet, was die neue Regel K9 **korrekt** meldet. Ursache eingegrenzt (der
`summen`-Aufruf der Testhilfe läuft in diesen Bäumen nicht durch), Fix-Hinweis notiert.
Reproduktion: `cd 70_AUTOMATION/tests && python3 -B ausbau/test_suite_etappe29.py`.
**Alle anderen 18 Suiten sind grün; der Regelprüfer meldet 0 Fehler.**

### Nachtrag 25.09.2026, ~03:00 — die offene Testklasse ist GESCHLOSSEN

Die zwei roten Tests in `test_suite_etappe29.py` hatten **einen** echten Grund, und er lag nicht im Test:

1. **`summen` brach ab**, wenn der Baum ein **eingebettetes Unter-Repo ohne Commit** enthielt
   (`git add -A` → „does not have a commit checked out") → die Liste wurde nicht nachgezogen.
   **Fix:** `git add -A --ignore-errors` + sichtbarer Hinweis, was ausgelassen wurde.
2. **K2 (Secret-Prüfung) meldete einen toten Symlink als ERROR** („Geführte Datei NICHT lesbar"),
   weil `stat()` dem Verweis folgt. Ein toter Verweis ist aber Sache von **K8** (Warnung).
   **Fix:** toter Verweis wird in K2 übersprungen.
3. Dazu: die Crate-Vollständigkeitsprüfung zählte tote Verweise als „nicht beschrieben" → ebenfalls
   übersprungen (keine Doppelmeldung).

**Ergebnis: 19 von 19 Suiten grün, Regelprüfer 0 Fehler.** Lehre: eine Testhilfe, die Fehler
verschluckt (`>/dev/null 2>&1`), kostet Stunden — die Ausgabe des `summen`-Aufrufs wird jetzt
gezeigt, wenn er fehlschlägt.

# Git-Ordner-Baum — Bedienung in einer Seite

**Wo:** `~/HAUPTLAGER/03_PROJEKTE/71_Git_Ordner`
**Was:** Ein Ordnerbaum mit festen Regeln, einem Katalog (was liegt wo), einem Suchindex
und einem Prüfer, der jederzeit sagt, ob der Baum in Ordnung ist.

## Die vier Befehle

```bash
cd ~/HAUPTLAGER/03_PROJEKTE/71_Git_Ordner

./ordner.sh status            # Kurzer Zustand (Index vorhanden? frisch? Quellen komplett?)
./ordner.sh pruefen           # Vollprüfung: Katalog, Regeln, Secrets, Index, Git
./ordner.sh suchen "begriff"  # Im ganzen Baum suchen (Inhalt + Namen)
./ordner.sh neu               # Suchindex neu bauen (Index ist nur eine Projektion)
./ordner.sh hilfe             # Kurzhilfe
```

## Was die Prüfung sagt

| Anzeige | Bedeutung | Was du tun musst |
|---|---|---|
| `OK` | Alles geprüft, nichts gefunden | nichts |
| `WARNING` | Hinweis, kein Fehler (z. B. Obergrenze erreicht) | lesen, meist nichts |
| `ERROR` | Ein Fehler: Katalog/Regel/Datei passt nicht | Meldung lesen, Angabe beheben |
| `CRITICAL` | Ernst: z. B. Secret-Muster gefunden, Pflichtquelle fehlt | sofort beheben |

Exitcodes (für Skripte): `0` = OK · `1` = WARNUNG · `2` = FEHLER · `3` = KRITISCH.
Die Vollprüfung **schreibt nur ihren eigenen Zustand** (`60_RUNTIME/state/`) und **ändert sonst nichts** —
sie löscht, verschiebt und repariert nie.

## Einen neuen Ordner aufnehmen (3 Schritte)

1. Ordner anlegen, z. B. `20_PROJEKTE/standalone/2026-10-01_mein_projekt`
2. Eintrag in `00_SYSTEM/manifest/repos.yaml` ergänzen (Name, Klasse, Bereich, Pfad, `git: false` oder `true`)
3. `./ordner.sh pruefen` → muss `0 Fehler` melden (Status WARNING und Exitcode 1 sind normal, solange der 50-MB-Hinweis des Zeigers steht), dann committen

## Was garantiert ist — und was nicht

**Garantiert (nachgemessen: 20 Suiten / 265 Testfunktionen):**
- Eine nicht lesbare Pflichtdatei ergibt **nie** „alles OK" — immer sichtbare Meldung + Exitcode ≠ 0
- Ab 5000 Dateien wird **nicht still** abgeschnitten, sondern gemeldet, wie viel ungeprüft bleibt
- Eine Sonderdatei (FIFO) als Index lässt das Werkzeug **nicht** hängen
- Ungewöhnliche Dateinamen ergeben keine kaputten Zeichen
- `--json` liefert **nur** JSON
- Der Index ist nur eine Projektion: er kann jederzeit mit `neu` gebaut werden, **Quellen gehen nie verloren**

**Dokumentierte Grenzen (ehrlich, nicht „gelöst"):**
- `60_RUNTIME` (Zustand/Logs/Cache) liegt im Baum, ist aber **nie** von Git verfolgt — geprüft
- `ROLLENTRENNUNG: NICHT VERIFIZIERT` — echte Prozess-/Rollentrennung ist Etappe 3
- **Zweite Kopie (P0) fehlt noch** — kommt als Schritt 9; bis dahin ist der Baum nicht gegen Plattenverlust geschützt
- Angriffs-/Race-Labor ist bewusst **nicht** Teil dieses Projekts (eine dokumentierte Grenze, kein Sicherheitsversprechen)

## Zweite Kopie und Unveränderbarkeit

```bash
./sicherung.sh kopie ~/sicherung_git_ordner                        # Baum + Prüfsummen + Git-Bündel
./sicherung.sh pruefen ~/sicherung_git_ordner                      # Prüfsummen der Kopie
./sicherung.sh wiederherstellen ~/sicherung_git_ordner ~/tmp/neu  # Wiederherstellung testen
sha256sum -c PRUEFSUMMEN_MASTER.txt                                # Code unverändert?
git tag -l                                                         # eingefrorener Stand
```
**Getestet:** Kopie · Prüfsummen OK · Wiederherstellung OK · Git aus Bündel · veränderte Datei erkannt.
**Offen (deine Entscheidung):** die Kopie liegt noch auf **derselben** Platte — echtes P0 braucht ein
zweites Medium. Das Verfahren dafür ist fertig und bewiesen.

## Änderungshistorie

Nur in `70_AUTOMATION/reports/FORTSCHRITT.md` (was wurde wann gebaut, mit welchem Beleg) und in `70_AUTOMATION/reports/BAUPLAN_WEG1.md`
(was ist der Plan, was ausdrücklich **nicht**). Der Regeltext ist eingefroren.

## Was neue Meldungen bedeuten (23.09.2026)

| Meldung | Bedeutung |
|---|---|
| `Zeiger zeigt INS LEERE` | Ziel existiert nicht — Zeiger korrigieren oder Daten herstellen |
| `Pruefsumme weicht ab` / `Groesse weicht ab` | Ziel passt nicht zum Zeiger |
| `OBERGRENZE … NICHT einzeln geprueft` | Ziel > 50 MB: nur Sammelprüfsumme geprüft |
| `UNTERREPOS: n Repo(s) …` | Projekt bringt eigene Repos mit — kein Fehler, nur Hinweis |
| `n Verweis(e) (Unterrepo/Submodul) uebersprungen` | Git-Verweise sind kein Repo-Inhalt |

## Echte Projekte im Baum (K7-Ausnahme, 23.09.2026)

Ein echtes, gewachsenes Projekt bringt seine **eigene** Struktur mit (gemessen: Tiefe 7, Breite 23).
Unverändert in den Baum kopiert erzeugt das über 100 Fehler. Deshalb zwei Wege:

1. **Empfohlen — Zeiger:** das Projekt bleibt, wo es ist:
   `./ordner.sh zeiger /Pfad/zum/Projekt`
2. **Kopie im Baum:** nur mit ausdrücklicher Erklärung im Katalog (`00_SYSTEM/manifest/repos.yaml`):
   ```yaml
   inhalt_ausgenommen: true
   ```
   Dann wird der Projektinhalt nicht nach K7 gemessen — es gibt **eine** Meldung je Projekt
   statt hunderter Fehler. Der Projektordner selbst wird weiter geprüft.

Alle Suiten auf einmal prüfen: `bash 70_AUTOMATION/tests/alle_suiten.sh`

## Git-Wartung (etwa monatlich, von Hand)

```bash
cd ~/HAUPTLAGER/03_PROJEKTE/71_Git_Ordner
git commit-graph write --reachable && git gc
```
Macht das Repo kleiner und schneller (gemessen 23.09.2026: 1,7 MB → 544 KB). Kein Automatismus,
kein Cron — nur wenn du willst.

**Ausbau-Plan:** siehe `70_AUTOMATION/reports/BAUPLAN_AUSBAU.md` (5 Schritte, Stück für Stück).

## Zweite Kopie: der Baum sagt dir, ob sie noch aktuell ist

In `50_INFRA/redundanz.yaml` stehen die **erklärten** Kopien. Bei jedem `./ordner.sh pruefen`
misst der Prüfer drei Dinge je Kopie: **existiert sie? ist sie aktuell? liegt sie auf einer
anderen Platte?** In der Statuszeile steht dann zum Beispiel:

```
REDUNDANZ: 1 Kopie(n), aktuell — GLEICHE PLATTE (schuetzt vor Fehlern, NICHT vor Plattenausfall)
```

**Kopie erneuern** (nach Änderungen): `./sicherung.sh kopie ~/sicherung_git_ordner`
Die Kopie hält den **Quellstand** fest (`QUELLSTAND=` in ihrer README.txt) — daran erkennt der
Prüfer, ob sie älter ist als der Baum.

## Inhalt der angebundenen Bestaende durchsuchen

```bash
./ordner.sh finden "begriff"     # sucht IM INHALT der Zeiger-Ziele — nur lesend
```
Findet Text in .txt/.md/.py/.json usw. Fuer PDF/DOCX zusaetzlich Recoll:
siehe `50_INFRA/RECOLL_ANLEITUNG.md` (Installation entscheidest du).

## Neues Projekt mit fester Nummer

```bash
./ordner.sh projekt "island_sprache" standalone
```
Legt `20_PROJEKTE/standalone/001_island_sprache_2026-09-24/` an — mit `STATUS.md` und
Eintrag im Katalog. **Die Nummer ist die Kennung: sie bleibt. Der Name darf sich ändern.**
Deshalb bricht Umbenennen nie mehr einen Weg (Notizen, Zeiger, Skripte).

Regeln (K6): Nummer **dreistellig** (001…) · Nummer **nie doppelt** → sonst Fehler ·
Form `NNN_name_JJJJ-MM-TT` · bestehende Ordner werden **nicht** umbenannt.

## Schnell finden und springen (Schritt 4)

```bash
./ordner.sh dateien "rechnung"    # Dateinamen suchen — im Baum UND in den angebundenen Projekten
./ordner.sh springen "island"     # Auswahlliste mit Pfeiltasten (fzf), um direkt hinzuspringen
```
`fdfind` und `fzf` waren auf diesem Rechner schon installiert — es wurde nichts nachinstalliert.
Fällt ein Werkzeug aus, nimmt das Programm das nächste (`fdfind` → `rg` → `find`).

## Doppelte Dateien BERICHTEN (Element 1 aus der Recherche)

```bash
./ordner.sh doppelt ~/HAUPTLAGER/03_PROJEKTE      # Pfad ist PFLICHT
```
Nur lesend — es wird **nie gelöscht, nie verschoben**. Bericht: `60_RUNTIME/doppelt/` (nie in Git).

Drei Zahlen, die man unterscheiden muss:
| Zahl | Bedeutung |
|---|---|
| **Extra-Speicher** | was wirklich zusätzlich belegt ist |
| **Hardlink-Gruppen** | zweimal benannte EINZELNE Datei — belegt **nichts** extra |
| **wiederherstellbar** | `venv/`/`node_modules` — neu erzeugbar, **kein Datenverlust** |

Gemessen (24.09.2026): `03_PROJEKTE` 53.086 Dateien / 10,83 GB → **13.276 doppelte Dateien = 1,395 GB
in 2,9 s**, davon **1,303 GB wiederherstellbar** (venv-Kopien).

## Drei Elemente aus der Recherche (Standard-Anschluss)

```bash
./ordner.sh crate [Ordner]           # Ordner SELBSTBESCHREIBEND machen (RO-Crate 1.1)
./ordner.sh vorlage <Ordner> <name>  # Vorlage anwenden: standard|forschung|handwerk|trading
./ordner.sh bag <Quelle> <Ziel>      # normgerechte Sicherung bauen (BagIt, RFC 8493)
./ordner.sh bag --pruefen <Bag>      # jede Pruefsumme nachrechnen -> "VALID" oder Fehler
```
* **RO-Crate** legt `ro-crate-metadata.json` in den Ordner: Name, Datum, jede Datei mit Groesse und Pruefsumme.
  `./ordner.sh pruefen` rechnet sie mit nach (Zeile `CRATE: ...`) — die Selbstbeschreibung kann nicht still veralten.
* **BagIt** erzeugt `bagit.txt` + `manifest-sha256.txt` + `bag-info.txt` + `data/`. Fremde BagIt-Werkzeuge
  verstehen diese Sicherung ohne unsere Doku. Ein Bag ist eine **Momentaufnahme** (kein Dauerzustand).
* **Vorlagen** stehen in `80_VORLAGEN/vorlagen.json` — David kann sie ohne Programmieren aendern;
  existierende Unterordner werden **nie** ueberschrieben.

## Einen NEUEN Git-Ordner-Baum anlegen (spross)

```bash
./ordner.sh spross /pfad/zum/neuen/Baum "Projektname"
```
Legt aus **diesem** Baum einen neuen an: dieselben zehn Bereiche, Werkzeuge, Tests und Pruefungen —
aber **frische Git-Historie**, keine Arbeitsdaten (`60_RUNTIME`), keine Zeiger auf fremde Bestaende,
und **keine geerbten Messungen** (Redundanz/Rollentrennung gelten nur fuer ihren Ort).
Existiert das Ziel, bricht der Befehl ab — es wird nie ueberschrieben.

**Ein neuer Baum ist noch nicht selbst gruen.** Einmalig noetig (gibt der Befehl selbst aus):
```bash
cd <NEUER BAUM> && ./ordner.sh neu        # Suchindex bauen
cd <NEUER BAUM> && ./ordner.sh pruefen    # Selbsttest-Fixtures bereitstellen (make_fixtures.py)
```
Noch offen (ehrlich): der Katalog (`00_SYSTEM/manifest/repos.yaml`) bringt Eintraege des Elternbaums mit
(Pfade wie `60_RUNTIME/artefakt/...`), die im neuen Baum nicht existieren -> K4 meldet sie als Fehler.

## Erweiterungen (24.09.2026)

* **BagIt jetzt "complete and valid":** der Bag enthaelt zusaetzlich `tagmanifest-sha256.txt`
  (Pruefsummen ueber bagit.txt/manifest/bag-info). Wird eine METADATENdatei geaendert, meldet
  `./ordner.sh bag --pruefen <Bag>` -> "METADATEN GEAENDERT". Die Pruefkette ist damit transitiv.
* **RO-Crate nennt sein Profil:** der Wurzel-Datensatz traegt `conformsTo` (RO-Crate 1.1) und eine Lizenz.
* **`./ordner.sh formate`** prueft Dateitypen (mit dem vorhandenen `file`) und Namen
  (Leerzeichen/Sonderzeichen) — **es markiert nur, es verurteilt nichts** und aendert nichts.

## Kopie und Originalbaum (wichtig, 25.09.2026)

* Die Testsuiten prüfen **Eigenschaften des gemessenen Originalbaums**. In einer Kopie melden die
  betroffenen Suiten deshalb **"uebersprungen (braucht den gemessenen Originalbaum)"** — das ist die
  ehrliche Antwort, kein Fehler. Im Originalbaum laufen alle Suiten.
* `./ordner.sh summen` entwertet den Quellstand einer Kopie (die Kopie gilt danach als **VERALTET**).
  Nach dem Nachziehen also einmal `bash sicherung.sh kopie <ZIEL> --bag` laufen lassen.

## Voraussetzung: Python mit PyYAML

Der Pruefer liest den Katalog (`00_SYSTEM/manifest/repos.yaml`) als YAML. Fehlt die
Bibliothek, meldet er das als CRITICAL-Befund (K5/K6/K7 nicht pruefbar) und der Selbsttest
gilt als NICHT ausgefuehrt — der Zustand ist dann bewusst nicht OK (fail-closed), statt mit
einem Absturz zu enden. Pruefen mit: python3 -c "import yaml".

Gemessen am 26.09.2026: /usr/bin/python3 hat PyYAML 6.0.3 und jsonschema. Andere
Python-Installationen (z. B. die mitgelieferte 3.14) haben beides nicht — dann den Pruefer
und die Suiten ausdruecklich mit einer passenden Python aufrufen, etwa:

    PATH=/usr/bin:$PATH ./ordner.sh pruefen
    PATH=/usr/bin:$PATH bash 70_AUTOMATION/tests/alle_suiten.sh

## Exitcodes (vollstaendig)

0 = OK · 1 = WARNUNG · 2 = FEHLER · 3 = KRITISCH · 4 = UNBESTAETIGT
Der Code 4 stammt aus der zentralen Tabelle in `rules.py` und wird von
`indexer.py` und `status_sim.py` verwendet — er stand bisher in keiner Nutzerdoku.

---

## Ab 27.09.2026: Neue Themen landen im Baum (Entscheid „Option 2")

**Alles, was ab jetzt NEU entsteht, wird als Thema im Baum angelegt.** Bestehendes bleibt, wo es ist:
der Baum verschiebt, benennt und loescht nichts von aussen. Wo ein Thema liegt, entscheidet der
Mensch — der Baum haelt fest, wo es liegt.

Drei Befehle, mehr nicht:

```bash
./ordner.sh projekt "thema_name" standalone            # legt das Thema an (vergibt selbst eine Nummer)
./ordner.sh vorlage 20_PROJEKTE/standalone/<nummer>_thema_name_<datum> forschung   # Vorlage: standard, forschung, handwerk, trading
./ordner.sh summen && ./ordner.sh pruefen              # Selbstbeschreibung + Pruefsummen, dann Kontrolle
git add -A && git commit -m "Thema <name> angelegt"
```

**Nachgemessen am 27.09.2026 (Wegwerf-Kopie, echter Baum blieb unberuehrt):** Ein neues Thema
beruehrt genau VIER Dinge — den Katalog (`00_SYSTEM/manifest/repos.yaml`), die neue `STATUS.md`,
`PRUEFSUMMEN_MASTER.txt` und `ro-crate-metadata.json`. Danach meldet die Kontrolle 0 Fehler.
Nichts ausserhalb des Baums wird angefasst.

**Merkblatt (eine Seite, zum Hinstellen):** `00_SYSTEM/MERKBLATT_NEUES_THEMA.md` — dort stehen
dieselben Schritte in Kurzform. **Auslöser im Chat** („neues Thema …" / „neuer Ordner …") ruft genau
diesen Weg auf: `neuesProjekt "<name>"` legt das Thema an, wendet die Vorlage an, zieht Selbstbeschreibung
und Pruefsummen nach, prueft und committet. Der klassische Weg bleibt mit `--klassisch` bzw. mit einem
ausdruecklichen Pfad erhalten (fuer Archiv-/System-/Temp-Ordner).

## Auf dem System installiert (27.09.2026)

```bash
ordner pruefen          # funktioniert aus JEDEM Verzeichnis
```

`~/bin/ordner` ist ein winziges Weiterleitungs-Skript auf `MASTER/ordner.sh`. Es aendert nichts am
Baum, es reicht nur den Aufruf weiter. Der Baum selbst liegt unveraendert an seinem Platz.
Getestet aus `~` und aus `/tmp`: `--hilfe`, `status`, `suchen`, `pruefen` laufen von ueberall.

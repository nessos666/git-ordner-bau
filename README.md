# Git-Ordner-Baum

Ein hierarchischer Ordnerbaum unter Versionskontrolle. Er beschreibt sich selbst, prueft sich
selbst und sagt ehrlich, was er **garantiert** und was er **nicht** kann.

**Anfangen:** `./ordner.sh` (zeigt alle sechzehn Befehle) · **Nachlesen:** `ANLEITUNG.md` ·
**In normaler Sprache:** `PROTOKOLL.md` · **Was bisher geschah:** `70_AUTOMATION/reports/FORTSCHRITT.md`

## Aufbau (zehn Bereiche)

| Bereich | Inhalt |
|---|---|
| `00_SYSTEM/` | Manifest, Schemas, Uebernahme-Doku |
| `10_AGENT/` | Regeln und Rollen fuer Automatik |
| `20_PROJEKTE/` | baum-eigene Projektordner (feste Nummern `NNN_name_JJJJ-MM-TT`) |
| `30_WISSEN/` | Wissen, Notizen |
| `40_DATEN/` | Zeiger auf grosse Bestaende AUSSERHALB (`pointers/*.yaml`) |
| `50_INFRA/` | Redundanz-Erklaerung, Werkzeug-Anleitungen |
| `60_RUNTIME/` | Arbeitsdaten des Baums — **absichtlich NICHT von Git verfolgt** |
| `70_AUTOMATION/` | Regelpruefer, Werkzeuge, Tests, Berichte |
| `80_VORLAGEN/` | Vorlagen fuer neue Projekte |
| `90_ARCHIV/` | Befunde, Stillgelegtes |

## Die sechzehn Befehle (hier vollstaendig, aus ordner.sh abgeleitet)

```
./ordner.sh status
./ordner.sh pruefen
./ordner.sh suchen
./ordner.sh neu
./ordner.sh zeiger
./ordner.sh projekt
./ordner.sh finden
./ordner.sh dateien
./ordner.sh springen
./ordner.sh doppelt
./ordner.sh bag
./ordner.sh crate
./ordner.sh vorlage
./ordner.sh spross
./ordner.sh summen
./ordner.sh formate
```

```bash
./ordner.sh                        # Hilfe
./ordner.sh status                 # Kurzlage
./ordner.sh pruefen                # Regelpruefer (K1-K9 + CRATE) + Pruefsummen + Redundanz
./ordner.sh suchen "begriff"       # Index-Katalog durchsuchen
./ordner.sh neu                  # Suchindex neu bauen (legt NICHTS an)
./ordner.sh projekt NAME standalone [--vorlage X]   # Projekt mit fester Nummer
./ordner.sh zeiger <Ordner>        # Zeiger auf einen grossen Bestand bauen
./ordner.sh finden "begriff"       # in TEXTEN und PDF/DOCX suchen (auch ausserhalb)
./ordner.sh dateien "muster"       # Dateien/Ordner nach Namen finden
./ordner.sh springen "muster"      # schnell zu einem Ort springen
./ordner.sh doppelt <Pfad>         # doppelte Dateien BERICHTEN (nur lesen, nie loeschen)
```

## Was garantiert ist — und was nicht

**Garantiert:** jede Aenderung ist versioniert und pruefbar · Pruefsummen der verfolgten Dateien
sind nachpruefbar · der Pruefer laeuft ohne Zusatz-Software · groesstenteils ohne Netz und ohne
Passwort · alles ist umkehrbar, nichts wird ungefragt geloescht.

**Nicht garantiert (ehrlich):** eine zweite Kopie liegt derzeit auf **derselben Platte** — sie
schuetzt vor Bedienfehlern, **nicht** vor einem Plattenausfall. Die Zeiger erfassen grosse Bestaende
nur als Ganzes oberhalb 50 MB. Die Rollentrennung (wer schreiben darf) ist im Prototyp **nicht
verifiziert**. Angriffe/Wettlaeufe sind eine dokumentierte Grenze, keine zugesicherte Eigenschaft.

## Selbst pruefen

```bash
./ordner.sh pruefen                          # muss "0 Fehler" melden
bash 70_AUTOMATION/tests/alle_suiten.sh      # 20 Suiten, 0 mit Fehlern
sha256sum -c PRUEFSUMMEN_MASTER.txt          # Pruefsummen der verfolgten Dateien
```

## Wenn du den Baum frisch klonst

Ein Klon enthaelt nur die versionierten Dateien. Drei Dinge fehlen darum planmaessig und werden
BENANNT gemeldet, nicht verschwiegen:

| Meldung | Warum | Was tun |
|---|---|---|
| `SELBSTTEST NICHT AUSFUEHRBAR: Fixtures fehlen` (Hinweis) | Die Selbsttest-Fixtures liegen NEBEN dem Baum und enthalten eigene Git-Repositories — sie koennen nicht mitversioniert werden | Fixtures aus dem Originalordner daneben kopieren, dann laeuft der Selbsttest |
| `Manifest '…' fehlt … Noch nicht gebaut` (Hinweis) | Zeiger-Manifeste liegen in `60_RUNTIME` und sind abgeleitete Laufzeit | `./ordner.sh zeiger <Objekt>` |
| `Laufzeit-Pfad fehlt` (Hinweis) | `60_RUNTIME` wird nie versioniert | Artefakt sichern, nicht neu bauen |

Ein Klon meldet darum **0 Fehler** beim ersten `./ordner.sh pruefen` — aber Hinweise, die man lesen
sollte. Suiten, die den gemessenen Originalbaum brauchen, werden uebersprungen (Merker
`60_RUNTIME/state/baum_original` fehlt) und das wird ausgedrueckt gesagt.

**Exitcodes:** 0 = OK · 1 = WARNUNG · 2 = FEHLER · 3 = KRITISCH · 4 = UNBESTAETIGT

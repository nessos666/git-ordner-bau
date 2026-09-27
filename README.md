# Git-Ordner-Baum

**Ein Ordnerbaum, der sich selbst beschreibt, sich selbst prüft und nichts anfasst, was ihm nicht gehört.**

![Prüfung](https://img.shields.io/badge/Pruefung-0_Fehler-brightgreen)
![Suiten](https://img.shields.io/badge/Suiten-20_von_20-brightgreen)
![Python](https://img.shields.io/badge/Python-3_%2B_PyYAML-blue)
![Normen](https://img.shields.io/badge/BagIt-RFC_8493-informational)

---

## Das Problem

Eine gewachsene Ablage hat drei Krankheiten:

1. **Niemand weiß, ob sie noch stimmt.** Dateien verschwinden, Ordner werden umbenannt, und keine
   Prüfung sagt es.
2. **Die Prüfungen lügen freundlich.** Läuft eine Prüfung nicht, meldet sie oft trotzdem „OK".
3. **Der Aufräumversuch ist gefährlicher als das Chaos.** Werkzeuge, die „automatisch sortieren",
   verschieben und löschen echte Daten.

Dieser Baum antwortet auf alle drei.

## Die drei Ideen

**1. Der Baum beschreibt sich selbst.**
Ein Katalog nennt jedes Projekt. Eine Selbstbeschreibung nach dem [RO-Crate](https://www.researchobject.org/ro-crate/)-Standard
nennt jede Datei mit Prüfsumme. Eine Prüfsummenliste und ein [BagIt](https://datatracker.ietf.org/doc/html/rfc8493)-Bag
rechnen unabhängig nach. Die Design-Dokumente liegen mit im Baum (`00_SYSTEM/design/`). Wer den Baum
allein bekommt, kann ihn lesen **und** nachrechnen — er muss nichts nachbauen.

**2. Jede Prüfung sagt die Wahrheit, auch wenn sie unangenehm ist.**
Fehlt eine Bibliothek, endet der Prüfer mit *Kritisch* statt mit einem stillen „OK". Kann ein Bereich
nicht geprüft werden, heißt der Befund **UNGEPRÜFT** — nicht „in Ordnung". Grenzen (etwa ein
Prüf-Fenster von 50 MB pro Lauf) werden als Grenze benannt, nicht als Schutz verkauft.

**3. Große Bestände bleiben, wo sie sind.**
Was nicht in den Baum gehört, bekommt einen **Zeiger**: Ort, Größe, Prüfsumme, Anleitung zum
Nachrechnen. Das Original wird nicht verschoben, nicht kopiert, nicht gelöscht.

## Schnellstart

Voraussetzung: `bash`, `git`, Python 3 mit `PyYAML`. Sonst nichts — keine Installation, kein Dienst,
kein Netz, kein Passwort.

```bash
./ordner.sh              # alle sechzehn Befehle
./ordner.sh pruefen      # Vollprüfung — muss "0 Fehler" melden
```

Ausgabe (echt, gekürzt):

```
STATUS: WARNING | 0 error, 1 warnings
PRUEFER: WARNING · 0 Fehler · 1 Hinweise · 404 geprueft · Selbsttest: ok
ZEITEN: gesamt 0.53s · Baumdurchlauf 0.01s · Regeln zusammen 0.31s · K9/CRATE 0.05s
CRATE: GUELTIG: 121 Dateien beschrieben und nachgerechnet, alle identisch.
```

## Was geprüft wird

| Regel | Prüft |
|---|---|
| `K1`, `K2` | Git-Bereiche, verfolgte vs. nicht geführte Dateien, **Secret-Scan** (auch im Git-Objektspeicher) |
| `K3` | Katalog-Einträge und die von jedem Projekt verlangte `STATUS.md` |
| `K4` | Laufzeit-Pfade in `60_RUNTIME` — fehlen sie, wird das als *Hinweis* benannt, nicht versteckt |
| `K5`, `K6` | Pflichtfelder im Katalog, erlaubte Namen für selbst vergebene Ordner |
| `K7` | Tiefe und Breite ab der Wurzel |
| `K8` | Zeiger auf Bestände außerhalb: Ziel vorhanden, Größe, Prüfsumme, rollierende Nachprüfung |
| `K9` | Selbstbeschreibung und Prüfsummenliste stimmen mit dem Inhalt überein |
| `CRATE` | RO-Crate-Selbstbeschreibung formal gültig |
| `SELFTEST` | Der Prüfer prüft sich selbst gegen absichtlich fehlerhafte Testobjekte |

**Exitcodes:** `0` OK · `1` WARNUNG · `2` FEHLER · `3` KRITISCH · `4` UNBESTÄTIGT

## Aufbau (zehn Bereiche)

| Bereich | Inhalt |
|---|---|
| `00_SYSTEM/` | Manifest, Katalog, Schemas, Design-Dokumente |
| `10_AGENT/` | Regeln und Rollen für Automatik |
| `20_PROJEKTE/` | baum-eigene Projekte (feste Kennung `NNN_name_JJJJ-MM-TT`) |
| `30_WISSEN/` | Wissen, Notizen, Dossiers |
| `40_DATEN/` | **Zeiger** auf große Bestände außerhalb (`pointers/*.yaml`) |
| `50_INFRA/` | Redundanz-Erklärung, Werkzeug-Anleitungen |
| `60_RUNTIME/` | Arbeitsdaten des Baums — **absichtlich nicht versioniert** |
| `70_AUTOMATION/` | Regelprüfer, Werkzeuge, Vorlagen, Tests, Berichte |
| `80_VORLAGEN/` | Vorlagen für neue Projekte |
| `90_ARCHIV/` | Befunde, Stillgelegtes |

## Befehle

| Befehl | Wirkung |
|---|---|
| `status` | Kurzlage: Index vorhanden und frisch? Quellen vollständig? |
| `pruefen` | Vollprüfung des Baums |
| `suchen "begriff"` | im Baum suchen (Inhalt + Namen) |
| `neu` | Suchindex neu bauen (der Index ist nur eine Projektion) |
| `zeiger <Pfad>` | Bestand außerhalb **read-only** aufnehmen (Zeiger + Prüfsummenliste) |
| `finden "begriff"` | im Inhalt angebundener Bestände suchen (nur lesend) |
| `projekt "name"` | neues Projekt mit fester Kennung anlegen |
| `dateien "muster"` | Dateinamen suchen |
| `springen "muster"` | zu Projekt oder Ordner springen |
| `doppelt <Pfad>` | doppelte Dateien **berichten** (nie löschen) |
| `crate [Ordner]` | Ordner selbstbeschreibend machen (RO-Crate) |
| `vorlage <Ordner> <name>` | Vorlage anwenden (`standard`, `forschung`, `handwerk`, `trading`) |
| `bag <Quelle> <Ziel>` | normgerechte BagIt-Sicherung bauen (RFC 8493) |
| `spross <Ziel>` | neuen Git-Ordner-Baum anlegen |
| `formate` | Dateitypen und Namen markieren (ändert nichts) |
| `summen` | Selbstbeschreibung und Prüfsummen nachziehen (nach **jeder** Änderung) |

## Gemessen (27.09.2026)

| Prüfung | Ergebnis | So nachprüfbar |
|---|---|---|
| Baumprüfung | **0 Fehler** · 404 geprüft · 0,53 s | `./ordner.sh pruefen` |
| Testsuiten | **20 von 20** grün · 265 Testfunktionen | `bash 70_AUTOMATION/tests/alle_suiten.sh` |
| Frisch ausgepackte Kopie, erster Lauf | **0 Fehler** (drei benannte Hinweise) | `git clone … && ./ordner.sh pruefen` |
| Selbstbeschreibung | gültig · 121 Dateien, alle Prüfsummen nachgerechnet | `./ordner.sh crate` |
| BagIt-Bag | 148 Dateien · 148 Prüfsummen, alle identisch | `./ordner.sh bag --pruefen <Bag>` |
| Prüfsummenliste der verfolgten Dateien | alle identisch | `sha256sum -c PRUEFSUMMEN_MASTER.txt` |

## Grenzen (ehrlich, nicht versteckt)

* **Test-Fixtures liegen neben dem Baum** — sie enthalten eigene Git-Repositories und können nicht
  mitversioniert werden. Ein Klon sagt darum ausdrücklich
  `SELBSTTEST NICHT AUSFUEHRBAR: Fixtures fehlen`, statt ein grünes OK zu erfinden.
* **Neun Suiten** brauchen den gemessenen Originalbaum. In einer Kopie werden sie **mit Begründung
  übersprungen** — nicht rot, aber auch nicht still.
* **Ein Prüflauf deckt bei großen Beständen ein Fenster von 50 MB ab** (rollierend über mehrere
  Läufe). Der jeweils ungeprüfte Rest wird ausdrücklich als `UNGEPRUEFT` ausgewiesen.
* **Kein Schutz gegen Plattenausfall:** die mitgelieferte Kopie liegt auf derselben Platte.
* **Nebenläufigkeit/Wettläufe** sind eine dokumentierte Grenze, keine zugesicherte Eigenschaft.

## Selbst prüfen

```bash
./ordner.sh pruefen
bash 70_AUTOMATION/tests/alle_suiten.sh
sha256sum -c PRUEFSUMMEN_MASTER.txt
```

Nach **jeder** Änderung im Baum gilt diese Reihenfolge — sonst passt die Selbstbeschreibung nicht
mehr zum Inhalt, und der Prüfer sagt es:

```bash
./ordner.sh neu && ./ordner.sh summen && ./ordner.sh pruefen
```

## Nach dem Klonen

| Meldung | Warum | Was tun |
|---|---|---|
| `SELBSTTEST NICHT AUSFUEHRBAR: Fixtures fehlen` | Fixtures liegen neben dem Baum (siehe Grenzen) | Fixtures daneben kopieren |
| `Manifest '…' fehlt … Noch nicht gebaut` | Zeiger-Manifeste liegen in `60_RUNTIME` (abgeleitete Laufzeit) | `./ordner.sh zeiger <Objekt>` |
| `Laufzeit-Pfad fehlt` | `60_RUNTIME` wird nie versioniert | Artefakt sichern, nicht neu bauen |

## Design

Das eingefrorene Design, jede Abweichung mit Begründung und die Gegenprüfung liegen **im Baum**:
`00_SYSTEM/design/`. Bei Widerspruch gilt `MASTER_DESIGN_v1.3.md`.

## Lizenz

Noch nicht festgelegt. Ohne Lizenzdatei darf der Code offiziell nicht weiterverwendet werden.

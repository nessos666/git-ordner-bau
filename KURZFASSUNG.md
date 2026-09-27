# Git-Ordner-Bau — Kurzfassung

**Was es ist:** Eine Ordnerstruktur, die sich selbst beschreibt, selbst prüft und nichts anfasst, was
ihr nicht gehört. Sie ist kein Ersatz für eine bestehende Ablage — sie ist die Beschreibung darüber.

## Die drei Ideen

1. **Der Baum beschreibt sich selbst.** Ein Katalog nennt jedes Projekt, eine Selbstbeschreibung
   (RO-Crate) nennt jede Datei mit Prüfsumme, eine Prüfsummenliste und ein BagIt-Bag rechnen
   unabhängig nach. Wer den Baum allein bekommt, kann ihn lesen und nachrechnen — er muss nichts
   nachbauen. Die Design-Dokumente liegen mit im Baum (`00_SYSTEM/design/`).
2. **Jede Prüfung sagt die Wahrheit, auch wenn sie unangenehm ist.** Fehlt eine Bibliothek, endet der
   Prüfer mit „Kritisch" statt mit einem stillen OK. Kann ein Bereich nicht geprüft werden, heißt der
   Befund „UNGEPRÜFT" — nicht „in Ordnung". Obergrenzen (z. B. 50 MB je Prüflauf) werden als Grenze
   benannt, nicht als Schutz verkauft.
3. **Große Bestände bleiben, wo sie sind.** Was nicht in den Baum gehört, bekommt einen *Zeiger*:
   Ort, Größe, Prüfsumme, wie man es nachrechnet. Das Original wird nicht verschoben, nicht kopiert,
   nicht gelöscht.

## Was es kann (16 Befehle, u. a.)

```bash
ordner pruefen               # Vollprüfung: Katalog, Regeln, Secrets, Index
ordner suchen "begriff"      # im Baum suchen
ordner finden "begriff"      # in angebundenen Beständen suchen (nur lesend)
ordner zeiger <Pfad>         # großen Bestand read-only aufnehmen
ordner projekt "name"        # neues Thema anlegen
ordner bag <Quelle> <Ziel>   # BagIt-Bag bauen (unabhängige Kontrolle)
```

## Gemessene Zahlen

| Prüfung | Ergebnis |
|---|---|
| Baumprüfung | **0 Fehler** · 404 geprüft · 0,53 s |
| Testsuiten | **20 von 20** grün · 265 Testfunktionen (im gemessenen Originalbaum) |
| Frischer Klon, erster Lauf | **0 Fehler** (drei benannte Hinweise) |
| Selbstbeschreibung | gültig · 121 Dateien, alle Prüfsummen nachgerechnet |
| BagIt-Bag | 148 Dateien · 148 Prüfsummen, alle identisch |
| Baumgröße | 6,5 MB (der Zeiger auf einen 99-MB-Bestand: 1 Datei) |

Alle Zahlen gelten für den gemessenen Originalbaum (27.09.2026). In einer frisch ausgepackten
Kopie meldet die Prüfung **0 Fehler** und überspringt 9 Suiten — jede mit Begründung.

## Was es ausdrücklich nicht ist

Kein Dienst, kein Hintergrundprozess, kein Cron, keine Telemetrie, keine Cloud.
Es verschiebt, benennt und löscht nichts außerhalb seiner selbst. Die Prüfregeln lesen fremde
Bestände ausschließlich.

## Voraussetzungen

Python 3 mit PyYAML, `git`, `bash`. Keine weiteren Abhängigkeiten, keine Installation nötig —
der Baum läuft aus seinem eigenen Verzeichnis.

## Grenzen, die benannt sind

* Die Test-Fixtures liegen neben dem Baum (sie enthalten eigene Git-Repositories) — ein Klon sagt
  darum ausdrücklich „Selbsttest: nicht ausführbar".
* Neun Suiten brauchen den gemessenen Originalbaum und werden in einem Klon mit Begründung
  übersprungen, nicht rot gemeldet.
* Die mitgelieferte Sicherungskopie liegt auf derselben Platte: sie schützt vor Fehlern, nicht vor
  Plattenausfall.

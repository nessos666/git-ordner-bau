# Datierte Recherche: Wie kann unser System besser werden? — 24.09.2026

**Auftrag (David):** datierte Suche, zwei Agenten parallel + eigene Suche; danach eine Liste, was wir
verbessern können — **nicht komplizierter, sondern besser.**

**Methode, ehrlich:** 2 Unter-Agenten (getrennte Suchrichtungen) + eine eigene Suche mit dem
SUCHER-1000-Werkzeug. *Meine eigene Suche war unergiebig* (130 Treffer, überwiegend YouTube-Ordner-Tipps;
Begriff zu allgemein). Die Agenten lieferten 16 Vorschläge; die tragenden Quellen wurden von mir
einzeln geprüft: **alle 6 geprüften URLs antworten HTTP 200**; die Behauptung „NDSA Levels V2.1,
März 2026" ist auf ndsa.org **wörtlich bestätigt** („2.1 was released in March of 2026").

## Was wir SCHON haben (damit nichts doppelt gebaut wird)

Prüfsummen-Manifest über alle verfolgten Dateien · Selbstbeschreibung (RO-Crate) · normgerechte
Sicherung (BagIt, RFC 8493) · Stichprobenprüfung bei großen Zeigern · Duplikat-Bericht (nur lesend) ·
**gemessene** Rollentrennung (423 Dateien, 0 Schreibspuren) · Redundanz-Erklärung · 17 Suiten/247 Tests ·
Regelprüfer K1–K8 · 14 Befehle.

## Die Ideen, die WIRKLICH neu sind (dedupliziert, nach Nutzen/Aufwand)

| # | Idee | Quelle (geprüft) | Aufwand | Messgröße (wie wir den Nutzen belegen) |
|---|---|---|---|---|
| **1** | **Fixity-Prüf-Log + Prüfplan**: jede Prüfung protokolliert Datum, Ort, Umfang, Ergebnis, Dauer; Rhythmus als Satz festgeschrieben (z. B. Bestand 180 Tage) | dpconline.org (NDSA Level 3: „Maintain logs of fixity info and supply audit on demand") | klein | „Anteil geprüfter Dateien in den letzten 180 Tagen: X von Y" + „Tage seit letztem Lauf" |
| **2** | **Hash-Kette im Log** (jede Zeile enthält HASH der vorherigen → einzelne Änderung fällt auf) | rfc-editor.org/rfc/rfc9162.html (append-only Log) | klein | „Kette passt: X von Y" + **Negativprobe** (1 Zeile ändern → Bruch an genau dieser Stelle) |
| **3** | **Schnellvorprüfung Größe+Anzahl** vor dem Hashing (BagIt „Payload-Oxum") | rfc-editor.org/info/rfc8493/ | klein | Laufzeit ms vs. Sekunden + Detektion: 1 von 1 |
| **4** | **Wiederherstellungs-Übung mit Zeitmessung**: Bag/Kopie zurückholen, Hashes prüfen, eine Datei absichtlich beschädigen und reparieren — gestoppt | dpconline.org (NDSA Level 4: „Ability to replace/repair"); git-bundle | klein–mittel | Wiederherstellungsdauer Minuten, „Hashtreffer X von Y", „repariert 1 von 1" |
| **5** | **Fehlerinjektion: muss der Prüfer Fehler finden?** (Bit kippen, Datei löschen/umbenennen, Manifestzeile streichen) | IEEE TSE 2011 (Mutation Testing) | klein–mittel | „erkannt X von Y" je Fehlerart — 17 grüne Suiten beweisen nur, dass Tests laufen |
| **6** | **Zeiger-Prüflauf im git-annex-Stil** (Ziel vorhanden? Größe? Hash? — für ALLE Zeiger auf einmal) | git-annex fsck | klein | „Zeiger geprüft X, Fehler Y" |
| **7** | **Objekt-Index je Bereich** (Johnny.Decimal „JDex": je Kind Kennung, Titel, Zweck, Status; Gegenseitigkeit erzwungen) | johnnydecimal.com + index-spec | mittel | „Verzeichnisse ohne Eintrag: 0" / „Einträge ohne Verzeichnis: 0" |
| **8** | **Entscheidungsprotokoll (ADR)**: WARUM unsere Regeln so sind (kein Cron, 60_RUNTIME nicht in Git, Zeiger statt Kopien) | adr.github.io | klein | „Entscheidungen dokumentiert X" — verhindert späteres Auseinanderbauen |
| **9** | **Signierte Tags** (SSH-Schlüssel, ohne ~/.gitconfig anzufassen: `git -c`) + `git fsck` im Prüflauf | git-scm.com, GitHub/GitLab-Doku | klein | „signierte und verifizierte Tags X von Y" |
| **10** | **Belegpflicht für Zahlen** in Grundsatzdateien + Werkzeugversionen festhalten (Drift-Test) | PLOS Comput Biol 2013 (Sandve et al., Regeln 3/4/9) | mittel | „Zahlen mit Beleg X von Y"; Driftprobe → Test rot 1 von 1 |

**Erweiterungen ohne neuen Aufwand (klein):** BagIt um `tagmanifest-sha256.txt` + `fetch.txt` ergänzen ·
RO-Crate mit Profilangabe (`conformsTo`) und Pflichtfeld-Prüfung härten · Format-/Namenspolitik mit
vorhandenem `file` prüfen (Datum ISO 8601, feste Nummern, keine Sonderzeichen).

## Bewusst NICHT empfohlen

* **siegfried** (Format-Identifikation, Go-Binary) → neue Abhängigkeit ✗
* **externer rocrate-validator** (Python-Paket) → neue Abhängigkeit ✗
* **Cron/Hintergrund-Überwachung** → verstößt gegen Davids Regel (keine Voll-Automatik) ✗
  Die Prüfungen laufen **auf Zuruf**, das Log beweist nur, was wirklich lief.

## Meine Empfehlung (Reihenfolge)

1. **Fixity-Log + Hash-Kette (1+2)** — kleinster Aufwand, größter Ehrlichkeitsgewinn: aus „0 Fehler jetzt"
   wird „geprüft am Datum, X von Y, Kette nachrechenbar".
2. **Schnellvorprüfung (3)** — Sekunden statt Minuten, sofort spürbar.
3. **Fehlerinjektion (5)** — beantwortet die Frage, ob unsere Prüfungen überhaupt greifen.
4. **Wiederherstellungs-Übung (4)** — die einzige Zahl, die im Ernstfall zählt.
5. **Entscheidungsprotokoll (8)** + **Belegpflicht (10)** — damit Wissen und Ehrlichkeit bleiben.

Alles davon: kein Cron, keine neue Abhängigkeit, umkehrbar, in Scratch prüfbar.

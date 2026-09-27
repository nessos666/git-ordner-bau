# CHANGELOG_DESIGN — Historie des MASTER DESIGN

**Warum diese Datei existiert:** In v1.2 stand die Änderungs-Historie **im Regeltext selbst** — und
die Verifikation fand daraufhin **fünf Selbstwidersprüche** (alte Lesarten, alte Versionsetiketten,
alte Zahlen, die dem aktuellen Regeltext widersprachen). Die Historie ist deshalb **hier** und nicht
mehr in der Spezifikation. **Die Spezifikation enthält nur den aktuellen Stand.**

## v1.0 -> v1.1 (nach 50 Red-Team-Szenarien: 0/50 sauber bestanden)
- 15 Regeln -> **8 Kernregeln** (K1–K8); entfernt: R14 (Archiv, von Git-Historie bereits belegt),
  R7 (in K6 aufgegangen), R15 (in K5), Symlink-Regel (nicht prüfbar)
- Tiefenregel neu gefasst · **GATE ≠ AUDIT** · Prüfer-Statuswerte (OK/WARNING/ERROR/CRITICAL)
- **Pin nur für fremde Abhängigkeiten** · Katalog bidirektional (K4) · `nodes/` ausgenommen
- **Bootstrap `provisional` -> `active`** · Secret-Pflichtreaktionskette · Prüfsummen-Schwelle 10 MB
- 37.314 B -> **25.214 B (−32 %)**

## v1.1 -> v1.2 (nach Re-Test: 4 CRITICAL FAIL, 9 FAIL)
- **P0** zweite Kopie als blockierende Vorbedingung · **neue Klasse „Artefakt"** (Finetunes u. a.)
- Restrisiko-Tarnung entfernt („UNGEBUFFERT") · **Träger = Telegram** (der vorausgesetzte
  07:00-Bericht **existierte nicht** — am lebenden System nachgewiesen)
- Tiefe **≤ 5 ab Wurzel, keine Ausnahmen** · `skills`-Pfadbindung · `schema_version` zurück
- Reaktionsketten-Ausführer · 90-Tage-Frist · Index-Sektion wieder aufgenommen + gehärtet
- 25.214 B -> **31.139 B (+23 %)**

## v1.2 -> v1.3 (nach Verifikation: 4 FAIL, 0 CRITICAL, 5 Regressionen)
- **Rechenfehler korrigiert:** Kapazität ist **~420 Projekte**, nicht 10.000 (der Prüfer rechnete nach)
- **Artefakt** in K1 + Baum + Kopf integriert (war „Klasse ohne Durchsetzung")
- **5-Minuten-Test ersetzt** durch prüfbare Regel (Dauer/Geld/Fremdzugriff, „im Zweifel Artefakt")
- **`schema_version`** in alle drei Feldlisten · **K8-Selbstwiderspruch aufgelöst**, „Datensatz" definiert
- **P0-Erkennung** ergänzt (der Prüfer liest das zweite Archiv — vorher nur Vorbehalt)
- **Bereiche als ZIEL-Struktur gekennzeichnet**; `10_AGENT` existiert heute nicht (real: `~/.hermes/`)
- `nodes/<gruppe>` festgeschrieben · Restore-Test einheitlich **vierteljährlich**
- **Ritual gestrichen:** `zuletzt_gesehen`, Index-Selbsttest/Frische-Monitor (jetzt freiwillig)
- **Historie aus dem Regeltext entfernt** (diese Datei)
- **Ehrlich:** v1.3 ist **größer als v1.1** (37.8 KB, gemessen am 24.09.2026) — die Härtung, die die Prüfer verlangten, kostet
  Platz. Kleiner als v1.0 (37,3 KB). Was **nicht** gestrichen wurde: die Antworten der 10 Bereiche
  (vom Auftrag ausdrücklich verlangt).

## Verfahren (Kurzfassung)
v1.0: 50 Red-Team-Szenarien (3 Prüfer) -> durchgefallen. v1.1: 45 Punkte Re-Test -> durchgefallen.
v1.2: Verifikation der 17 Korrekturen -> 4 FAIL. v1.3: Korrektur. **Jede Runde mit unabhängigen
Prüfern, jede Fundstelle mit Bewertung PASS / PASS MIT EINSCHRÄNKUNG / FAIL / CRITICAL FAIL.**

## Legende der Fundcodes (nur hier definiert)

*Die Spezifikation selbst nennt **keine** Fundcodes mehr — sie enthält nur den aktuellen Stand.
Die Codes erscheinen ausschließlich in diesem Changelog und in den Prüfberichten.*

| Code | Bedeutung |
|---|---|
| `T1`–`T3` | „tödliche Treffer" der v1.0-Prüfung: Selbstwiderspruch Tiefe · kein Empfänger · „Job ist das Gate" |
| `S1`–`S50` | Szenariennummern aus dem v1.0-Red-Team (50 Szenarien) |
| `C1`–`C4` | CRITICAL FAILs: Redundanz · Modell-Klasse · Kaschierung · nicht existierender Bericht |
| `F-a`…`F-n` | FAILs des v1.1-Re-Tests (14 Punkte) |
| `W1`–`W5` | dokumentarische Widersprüche der v1.3-Prüfung |
| `R1`–`R15` | die 15 Regeln der v1.0 (in v1.1 zu K1–K8 verdichtet) |

## 2026-09-22 — Bau-Abweichung A1: 60_RUNTIME innerhalb des Baum-Repositories

**Freigabe:** David, 22.09.2026 (mündlich: "ja").

**Ausgangslage:** Der Prototyp-Baum ist auf Davids Wunsch EIN Git-Repository.
Das eingefrorene v1.3 verlangt für `60_RUNTIME` "KEIN Repo".

**Entscheidung:** Die Regel wird am Zweck ausgerichtet. Verboten ist nicht die
Lage im Baum, sondern die **Versionierung** des Zustands. Der Pruefer prueft
deshalb jetzt die tatsaechliche Verfolgung durch Git (`git ls-files -- 60_RUNTIME`).

**Beleg:** 0 von Git verfolgte Dateien unter `60_RUNTIME` (gemessen 22.09.2026),
`.gitignore` fuehrt `60_RUNTIME/`. Der Schutz bleibt erhalten, die Pruefung sitzt
an der richtigen Stelle.

**Betroffen:** `MASTER_DESIGN_v1.3.md` Abschnitt K4/Wartungstabelle (Regeltext bleibt
eingefroren; diese Abweichung ersetzt ihn im Prototyp).

## 23.09.2026 — Prototyp 2.9 (Umsetzung, kein Designwechsel)
Zwei echte Lücken aus dem Testlauf an `03_PROJEKTE` geschlossen, beide **innerhalb** der
bestehenden Regeln (K8 Zeiger, K4 Katalog, K2 Secret-Scope) — `MASTER_DESIGN_v1.3.md` bleibt
unverändert eingefroren:
- **K8**: Zeiger werden inhaltlich geprüft (Existenz, Größe, Prüfsumme, Dateizahl, Manifest-Aggregat).
  Grenze: >50 MB nur Aggregat, sichtbar ausgewiesen.
- **K4**: Repos unterhalb eines katalogisierten Pfads sind Unterrepos des Projekts (Hinweis, kein Fehler).
- **K2**: Git-Verweise (Index-Modus 160000) sind kein Repo-Inhalt → übersprungen und gemeldet.
Beleg: 9/9 Suiten, Basisbaum 0 Fehler, Tag `v0.2.9-prototyp`.

## 23.09.2026 — Entscheidung K7/K6 und echte Projekte (Prototyp 2.11)
**Befund (gemessen):** Ein echtes Projekt unverändert in den Baum kopiert (`666_OSINT`, 6 eigene Repos)
erzeugte **109 Fehler** — über 100 davon nur aus K7 (Tiefe 6–7, Breite 23). Echte Projekte bringen ihre
eigene, gewachsene Struktur mit; Umbau wäre „etwas anfassen" und verboten.
**Entscheidung:** Echte Projekte werden **als Zeiger** angebunden (`./ordner.sh zeiger <Pfad>`), nicht kopiert.
Für den Fall, dass ein Projekt doch kopiert werden muss, gilt die Ausnahme **nur auf ausdrückliche
Erklärung im Katalog** (`inhalt_ausgenommen: true`): dann wird der Projektinhalt nicht nach K7 gemessen und
das Ergebnis ist **eine** Meldung je Projekt statt ~100 Fehler.
**Messung der Ausnahme (vor dem Einbau):** im Testobjekt fiel die Fehlerzahl damit von **109 auf 10**
(die verbliebenen 10 sind Schema/K3/Budget — nichts mit Tiefe/Breite).
**Beim Einbau passiert (offen dokumentiert):** zwei eigene Fehler — (1) `rules.py` durch einen falschen
Textanker beschädigt, aus Git zurückgeholt; (2) `catalog` als Liste statt als Dict behandelt
(AttributeError, per Fehlermeldung gefunden). Seither: Anker VOR dem Schreiben prüfen, Ergebnis NACH dem
Schreiben verifizieren.
**GEBAUT (23.09.2026):** `k7` sauber eingebaut (`inhalt_ausgenommen: true`), Feld im Katalog-Schema
ergänzt, 2 Dauer-Tests (Schärfekontrolle d1 + Wirkung d2), Sammelstarter `alle_suiten.sh`; 10/10 Suiten grün.
Am echten Projekt gemessen: ~100 K7-Tiefe-Fehler → 1 sichtbare Meldung.

## 2026-09-24 — K7 unveraendert: Ordnung statt Ausnahme (Ausbau-Schritt 3)
- Anlass: `70_AUTOMATION/tests` meldete **Breite 21 > 20** — kein Fehlalarm und kein Cache-Artefakt:
  der Ordner war durch eine neue Suite **tatsaechlich** auf 21 Inhaltseintraege gewachsen (erzeugte
  Zwischenspeicher zaehlen bereits nicht mit, `EXCLUDE_DIRS`). Korrektur deshalb NICHT an der Regel,
  sondern an der Ordnung: Suiten liegen jetzt in `tests/weg1/` (8) und `tests/ausbau/` (5).
  K7 bleibt damit **unveraendert**.


## Korrektur 24.09.2026

- Zeile 34 nannte fuer v1.3 "33,6 KB"; **gemessen** sind es **37.8 KB** (`stat -c %s MASTER_DESIGN_v1.3.md`). Korrigiert.

## 27.09.2026 — Abweichung A1: Einzelprüfsumme je Datei + rollierender Prüflauf

**Freigabe:** David, 27.09.2026 (Kurzwahl 1a). **Das eingefrorene Design (`MASTER_DESIGN_v1.3.md`) wurde NICHT verändert** — die Abweichung steht ausschließlich hier.

**Was das Design sagte:** Regel K8 verlangte Einzelprüfsummen nur für Objekte ab einer Größe von 10 MB; kleinere Dateien galten über die Prüfsumme der Manifest-Liste als abgesichert (Aggregation). Für Zeiger über der Tiefengrenze war eine feste Stichprobe von 16 gleichmäßig verteilten Dateien vorgesehen.

**Warum das so nicht bleibt (gemessen, nicht gemeint):**
- Eine Größen-Schwelle kennt keine Norm. Die Erhebung des NDSA (US-National Digital Stewardship Alliance) zeigt 94,9 % der Einrichtungen mit dateiweiser Fixity-Prüfung, keine nimmt kleine Dateien aus; die Empfehlung lautet: Prüfsumme je Datei, rollierender Durchlauf, Abdeckung in Dateien *und* Bytes.
- Die Preisangst war unbegründet: Hashen kostet in diesem Bestand etwa 3 Minuten für 341 GB (1923 MB/s gemessen).
- Die Aggregation hatte eine echte Lücke: eine Änderung **gleicher Größe** an einer kleinen Datei blieb unsichtbar. Mit Einzelprüfsummen ändert sich das Aggregat.

**Neue Festlegung:**
1. **Jede** Datei bekommt eine eigene Prüfsumme. Manifest-Version 2 → 3; das Feld `schwelle_mb` entfällt, dafür steht `einzelpruefsummen_je_datei: ja`. Die Zeile mit `-` bedeutet jetzt nur noch „unlesbar oder toter Verweis".
2. Zeiger über der Tiefengrenze werden **rollierend** geprüft: je Lauf eine Zeitscheibe (3 s oder 200 MB, je nachdem was zuerst greift), Stand in `60_RUNTIME/state/rollierend.json`, Fortsetzung beim nächsten Lauf. Gemeldet wird die Abdeckung in Dateien und Bytes plus die Fortsetzungsstelle. Der Rest gilt ausdrücklich als ungeprüft; mindestens ein Eintrag je Lauf ist erzwungen, damit sich die Scheibe auch bei knappem Budget dreht.
3. Vorbild für 2: `git-annex --incremental --time-limit` und die Praxis großer Archive (GovInfo prüft je Durchlauf etwa einen Monat des Bestands).

**Nachweis (27.09.2026):** vier Läufe mit erzwungenem Mini-Budget wandern 1 → 2 → 3 → 4 (Stand-Datei `{"probe": {"pos": 4}}`); ein Lauf mit normalem Budget prüft 40 von 40 Dateien (100 % der Bytes); eine veränderte Datei wird als Abweichung gemeldet (Positivkontrolle); die Tests `etappe40 k5/k6/k7` und `etappe37 t3` prüfen die neuen Zusagen. Stand Baum: `v0.2.66-prototyp`, 20 von 20 Suiten grün, Baumprüfung 0 Fehler.

## 2026-09-27 — Entscheid: Neue Themen in den Baum (Option 2)

David hat aus vier Moeglichkeiten **Option 2** gewaehlt: *neue* Themen entstehen ab jetzt im Baum,
alles Bestehende bleibt unangetastet. Das Design bleibt davon unberuehrt (FROZEN) — es ist ein
Betriebs-Entscheid, keine Design-Aenderung.

Begruendung: kleinster moeglicher Schritt. Nichts wird verschoben, umbenannt oder geloescht; kein
neuer Ort, keine neue Architektur, kein Cron. Der Mechanismus war bereits gebaut (`ordner.sh projekt`
+ `ordner.sh vorlage`) und ist durch die Suiten abgedeckt.

Beleg (Wegwerf-Kopie `_beweis/neues_thema`, 27.09.2026): Ein neues Thema beruehrt genau vier Dateien
(Katalog, neue STATUS.md, Pruefsummenliste, Selbstbeschreibung). Kontrolle danach: 0 Fehler.
Der echte Baum meldete nach dem Versuch `git status` = sauber.

Offen gelassen: WO der fuer neue Themen massgebliche Baum liegt (dieser Prototyp-Baum oder ein
frischer `./ordner.sh spross`). Davids Entscheid, nicht meine.

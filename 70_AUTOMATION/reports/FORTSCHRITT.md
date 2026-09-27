# FORTSCHRITT — Weg 1

Stand: 2026-09-22 · Basis-Commit: 19e529f

- [x] 0  Verbindungsfehler: EINE Fehlerklasse + EINE Exitcode-Tabelle (Blocker 6+7) — 188/188 gruen, MASTER OK
- [x] 0b Gesamter MASTER-Baum als EIN Projekt unter Git (Commit 19e529f, 54 Dateien)
- [x] 1  F1 unlesbare Pflichtdatei darf nie "OK" ergeben
      Zwischenstand: Baum ist jetzt EIN Git-Repo (dein Wunsch). Dadurch meldete der Pruefer
      7 Fehler (4 = Folgen der Zusammenlegung, alle behoben; 3 = K2 "Gefuehrte Datei ist keine
      regulaere Datei" in drei Katalogordnern, noch offen).
      Katalog korrigiert (00_SYSTEM/70_AUTOMATION git:false), Wurzel-Repo als bekannt markiert,
      60_RUNTIME-Regel neu verankert: geprueft wird Verfolgung durch Git, nicht die Lage im Baum.
      ABWEICHUNG vom eingefrorenen Design v1.3 (dort: 60_RUNTIME 'KEIN Repo') -> braucht Davids Ja.
      Ursache der 3 Restfehler gefunden: drei Ordner hatten noch eigene Repos, Git hat sie beim
      Zusammenlegen nur als VERWEIS eingetragen -> der Pruefer sah dort "eine Datei, die ein Ordner ist".
      Behoben: Historien als Buendel archiviert, Verweise entfernt, Inhalte normal versioniert,
      Katalog angepasst (git:false fuer die drei).
      Zustand: PRUEFER OK - 0 Fehler - 293 geprueft - EIN Repo - 7/7 Suiten gruen (Commit 6e130d4)
      BELEG F1 (7 Varianten gemessen, Positivkontrolle rc=0 sauber):
        toter Symlink/Ordner/chmod 000/kaputtes YAML -> CRITICAL, rc=3, sichtbare Meldung
        Regelmodul rules.py unlesbar -> VORHER rc=1 + Traceback (Fehler!), JETZT rc=2 + Meldung
        "--root ausserhalb" -> sauber abgewiesen; Katalog fehlt -> rc=3
      Fix: Notausgang + Excepthook in check_all.py (kein Traceback, kein stilles OK),
      Exitcode-Zahlen kommen jetzt aus der EINEN zentralen Tabelle (rules.EXIT).
      BELEG F2 (3 Faelle gemessen, korrigierter Aufbau nach zwei eigenen Messfehlern):
        Positivkontrolle      rc=0 | Datei: status=OK       exit=0 geprueft=293
        Katalog entfernt      rc=3 | Datei: status=CRITICAL exit=3 geprueft=260   (vorher: exit=None)
        Zustand nicht schreibbar rc=3 | sichtbare stderr-Meldung, KEIN stilles OK
      Vorher fehlten in der Statusdatei "exit" und "geprueft" (waren None) und ein nicht
      schreibbarer Zustand wurde still verschluckt. Beides behoben, 7/7 Suiten gruen.
      BELEG F5 (2 Laeufe, Positivkontrolle sauber):
        ROT: Baum ohne .git + 6002 Dateien -> "158 geprueft", KEIN Wort ueber den Rest (stiller Abbruch,
             Ursache rules.py:1166-1170 "if n > grenze: break").
        GRUEN: sichtbare WARNUNG "OBERGRENZE 5000: 1002 von 6002 Dateien wurden NICHT auf Secrets
             geprueft. Rest gilt als UNGEPRUEFT." | Positivkontrolle: OK, keine Meldung, rc=0.
        SCHRITT 4 ZWISCHENSTAND: ROT belegt und reproduzierbar — FIFO als Indexdatei
      (60_RUNTIME/cache/index/suche.db) laesst 'indexer status' UND 'indexer search'
      unbegrenzt haengen (>25 s, timeout, rc 124). check_all ist nicht betroffen (rc 0).
      Blockierender Syscall per strace belegt: openat("<...suche.db>", O_RDONLY|O_NOFOLLOW|O_CLOEXEC)
      = ? ERESTARTSYS  -> es fehlt O_NONBLOCK; die Stelle liegt NICHT in safe_open_fd (dort
      versucht, wirkungslos) und nicht in verbinde(). Beide Versuche wurden zurueckgenommen,
      Baum wieder gruen. Naechster Ansatz: die Stelle setzt O_NOFOLLOW selbst (Grep oben).
      BEHOBEN (Commit folgt): Pruefung VOR dem Oeffnen in verbinde() — Sonderdatei/Symlink als
      Indexdatei wird abgewiesen. Stack war per faulthandler belegt: indexer.py:118 verbinden
      <- :212 verbinde <- :463 status.
      NACHMESSUNG mit FRISCHER Kopie (wichtig!):
        FIFO: status rc=2 ohne Haenger | search rc=2 + Meldung "Indexpfad ist ein SONDERDATEI
              (FIFO/Geraet/Socket) (…suche.db) — kein regulaerer Index" | build rc=0 (ersetzt die
              Datei atomar, dokumentiertes Verhalten)
        Positivkontrolle (echter Index): status rc=0, search rc=0
      MEINE ZWEI FEHLER dabei: (1) Anker war nur Teilstring einer eingerueckten Zeile ->
      IndentationError, per 'git checkout' geheilt; (2) ich habe den Fix gegen eine VERALTETE
      Testkopie gemessen und deshalb faelschlich "wirkt nicht" geschlossen.
      Lehren: Anker mit voller Einrueckung + Vorgaengerzeile; nach jeder Aenderung eine FRISCHE
      Kopie messen.
      BELEG F3 (5 Namensarten gemessen, frische Kopie): Nicht-UTF8 (\xff\xfe), Zeilenumbruch,
      Tab, Steuerzeichen \x01, 200-Zeichen-Name -> ueberall rc=0, Ausgabe als UTF-8 dekodierbar,
      KEINE rohen 0xff-Bytes, Name escaped als fremdname_\xff\xfe.md. F3 war bereits korrekt
      (kein Fix noetig) — belegt statt behauptet.
      BELEG F4: ROT war 'indexer build --json' -> erst 2 Klartextzeilen, dann JSON (nicht auslesbar).
      Fix: build(root, still=a.json) + JSON mit Einrueckung. GRUEN (frische Kopie): build --json
      json.loads OK, status --json OK, search --json OK, check_all --json OK, Klartext-Ausgabe
      ohne --json unveraendert.
      BELEG F9 (Schritt 7): neue Datei 70_AUTOMATION/tests/test_suite_etappe28.py mit 6 Tests
      (F1, F2/FIFO, F3, F4, F5, F8) — jeder Test mit eigener Positivkontrolle. Zwei eigene
      Testfehler dabei gefunden und behoben (Kopien lagen INNERHALB des Baums -> Rekursion;
      stdout war schon str -> .decode() unmoeglich) und zwei Umgebungsfallen (Testkopie braucht
      einen sauberen git-Stand; der Pruefer-Selbsttest braucht Fixtures neben der Baumwurzel ->
      in Kopien --no-selftest, er ist Gegenstand der uebrigen Suiten).
      SCHAERFEKONTROLLE: mit abgeschaltetem Fix wird der FIFO-Test ROT ("Werkzeug HAENGT
      (Timeout)"), mit Fix gruen — der Test kann also wirklich fehlschlagen.
      Gesamtstand: 8/8 Suiten gruen (194 Tests).
      BELEG Schritt 8: ordner.sh (755) mit 5 Befehlen — hilfe, status, pruefen, suchen, neu.
      Alle fünf einzeln ausgefuehrt: hilfe rc=0, status rc=0 (Index vorhanden/veraltet), pruefen
      rc=0 (STATUS: OK · 295 geprueft), suchen "Standalone" rc=0 (5 Treffer), neu rc=0
      (INDEX GEBAUT 80 Dokumente). ANLEITUNG.md = 1 Seite: Befehle, Statusstufen, Exitcodes,
      Aufnahme eines neuen Ordners, garantierte Eigenschaften und dokumentierte Grenzen.
      KLEIN OFFEN: 'status' meldet im FIFO-Fall nur die verkürzte Zeile ("vorhanden · 0.00 MB"),
      Exitcode 2 ist aber korrekt; klarere Wortwahl folgt in Schritt 7.
      OFFEN (klein): die maschinenlesbare ungeprueft-Liste in status.json bleibt 0 — die sichtbare
        Warnung steht, die Zaehlung im Artefakt noch nicht. Wird in Schritt 7 mitgetestet.
- [x] 2  F8 kein "OK" + "KRITISCH" im selben Lauf
- [x] 3  F5 Abschneiden ab 5000 Dateien sichtbar
- [x] 4  F2 FIFO -> sauberer Fehler statt Haenger
- [x] 5  F3 ungewoehnliche Dateinamen ohne kaputte Bytes
- [x] 6  F4 --json sauber auslesbar
- [x] 7  F9 dauerhafte Selbsttests (Regression)
- [x] 8  Anleitung + Startskript ordner.sh
- [x] 9  Zweite Kopie + Wiederherstellungs-Test (P0) — Verfahren bewiesen
- [x] 10 Freeze: Tag + Pruefsummen
- [x] 11 Abschlusslauf 2x + Bericht

Regel: Nach JEDEM Schritt wird hier abgehakt und der Beleg (Zahl) eingetragen.


## Umzug in den HAUPTLAGER (23.09.2026)
Baum liegt jetzt unter `~/HAUPTLAGER/03_PROJEKTE/55_Git_Ordner_Prototyp/MASTER` (03_PROJEKTE ist selbst kein Repo -> keine verschachtelten Repos).
Die Sandbox ist **ortsunabhängig** gemacht: `Path(__file__).resolve().parents[3]` statt festem
Heimpfad (17 Dateien). Belege: 8/8 Suiten am neuen Ort grün, Prüfer OK · 0 Fehler, Prüfsummen identisch.

### Vorfall beim Umzug (bitte lesen)
Ein Kommentar am Zeilenende eines Ersetzungstextes machte in `test_suite_etappe28.py` aus
`B = <Sandbox>/"tmp28"` die Variable `B = <Sandbox>`. Die Aufräumfunktion der Suite löschte damit
den **ganzen Baum** (Git-Inhalt + Laufzeit-Zustand). Wiederhergestellt aus Git-Bündel + zweiter Kopie
+ Artefakt aus Prüfer-Kopien (md5 `144129f9`, byte-identisch). **Kein Datenverlust.**
Schutz jetzt: `rules.nur_scratch()` + Schranke in der Suite + 2 Dauer-Tests (verweigert Sandbox/Baum,
erlaubt Testwiese). Lehren: Kommentare nie an ersetzte Codezeilen hängen; Testwiesen nie aus einer
einzigen Variable ableiten; vor jedem Messen kompilieren; bei tieferen Pfaden AF_UNIX-Länge beachten.

## A+B (23.09.2026) — aus dem Testlauf mit echten Projekten
- **A Zeiger-Prüfung** (`rules.py`, K8): `ziel` existiert · Größe (Datei) · Einzelprüfsumme (Datei) ·
  Dateizahl (Ordner) · Aggregat über die Manifest-Liste. Ordner-`groesse` wird NICHT gegen die
  Byte-Summe geprüft (kann sich auf Quelldaten beziehen). >50 MB: nur Aggregat, sichtbar als
  „NICHT einzeln geprüft". **Rot vor Grün belegt:** Tests `a1` (Zeiger ins Leere) und `a2`
  (falsche Prüfsumme) waren ROT, jetzt grün.
  Nebenbefund: Fixture benutzte ein unersetztes Ziel `<sandbox>/…` → behoben; Demo-Zeiger des
  Baums auf echte Daten ausgerichtet.
- **B Repo-Politik** (K4 + K2): Repos unterhalb eines katalogisierten Pfads = Unterrepos des
  Projekts → **gezählt und gemeldet** (`UNTERREPOS: n Repo(s) …`), nicht verlangt. Beleg:
  Test `b1` fällt von 2 Verweigerungen auf **0 Fehler**. Schärfekontrolle `b2`: Repo ohne
  katalogisierten Elternpfad bleibt ERROR. Git-**Verweise** (Index 160000) werden von der
  Secret-Prüfung übersprungen und sichtbar gemeldet (vorher „keine reguläre Datei").
- **Ursache der zunächst roten Läufe (ehrlich):** ein Unter-Repo OHNE eigenen Commit lässt
  `git add -A` mit „does not have a commit checked out" scheitern — dann fehlt auch STATUS.md
  im Index und K3 meckert zu Recht. Vier Anläufe gebraucht; danach Ursache gemessen statt geraten.
- **Stand:** 9/9 Suiten grün · Basisbaum `PRUEFER: OK · 0 Fehler · 279 geprüft · Selbsttest ok` ·
  Prüfsummen identisch · Tag `v0.2.9-prototyp`.

## TESTLAUF C (23.09.2026)
Siehe `_TESTLAUF_C/C_BEFUND.md`. Kurz: 10 echte Projekte als Zeiger (2,14 GB, 42.377 Dateien)
laufen sauber; drei Fehler behoben (Datei-Definition, Listen-Ort, Symlink-Absturz); **offene Design-Frage**:
echte Projekte mit Tiefe 6-7 / Breite 23 verletzen K7/K6 -> nur per Zeiger anbinden, nicht kopieren.

## K7-Ausnahme GEBAUT (23.09.2026)
- `k7` misst Tiefe/Breite weiter ab MASTER-Wurzel — **außer** der Katalog erklärt für ein Projekt
  ausdrücklich `inhalt_ausgenommen: true`. Dann: eine sichtbare Meldung je Projekt statt ~100 Fehler.
  Ohne Marker ändert sich nichts (kein stiller Verhaltenswechsel).
- Neue Tests `test_suite_etappe30.py`: `d1` Schärfekontrolle (ohne Marker greift K7 weiter),
  `d2` Wirkung (mit Marker keine Fehler + sichtbare Meldung + kein Schema-Fehler).
- Feld im Katalog-Schema ergänzt (`00_SYSTEM/schemas/repos.schema.json`, additionalProperties=false).
- Neu: `70_AUTOMATION/tests/alle_suiten.sh` lässt **alle** Suiten automatisch laufen.
- Gemessen am echten Projekt in der Testinstanz: ~100 K7-Tiefe-Fehler → **1** Meldung.
- **Eigener Fehler, offen dokumentiert:** der erste Einbau stürzte ab, weil ich `catalog` als Liste
  statt als Dict (`catalog["repos"]`) behandelt habe — Ursache per Fehlermeldung gefunden, nicht geraten.
  Ferner habe ich davor `rules.py` durch einen falschen Textanker beschädigt (aus Git zurückgeholt).
  Seither prüfe ich Anker VOR dem Schreiben und verifiziere nach dem Schreiben (Zeichenzahl, Marker-Anzahl).

## Ausbau-Schritte 1 · 2 · 5 (23.09.2026)

- **Schritt 1 — Git-Wartung (von Hand, kein Cron):** `git commit-graph write --reachable && git gc`
  → Repo **1,7 MB → 544 KB**, lose Objekte 140 → 0, `git fsck` sauber. In `ANLEITUNG.md` als
  monatlicher Handgriff festgehalten (keine Automatik).
- **Schritt 2 — Redundanz wird GEMESSEN:** `50_INFRA/redundanz.yaml` erklaert die Kopien; der
  Pruefer meldet je Kopie *existiert / aktuell / andere Platte*. Statuszeile vorher
  `REDUNDANZ: FEHLT` (feste Annahme) → jetzt
  `1 Kopie(n), aktuell — GLEICHE PLATTE (schuetzt vor Fehlern, NICHT vor Plattenausfall)`.
  Eigener Denkfehler dabei gefunden und behoben: der erste Vergleich nutzte die Pruefsummenliste
  der Kopie, die andere Pfad-Praefixe (`./...`) hat — **Fehlalarm „VERALTET"**. Richtig ist der
  festgehaltene **QUELLSTAND** (`QUELLSTAND=` in der README der Kopie). Tests e1/e2/e3 gruen.
- **Schritt 5, Teil 1 — Inhaltsuche ohne Installation:** `./ordner.sh finden "begriff"` sucht
  IM INHALT der Zeiger-Ziele (nur lesend, nutzt das vorhandene `rg`). Probe an echten Daten:
  Island-Dossier 312 Dateien/94 MB → Treffer; Gegenprobe → `0 Treffer`. Tests f1-f4 gruen.
  Teil 2 (Recoll fuer PDF/DOCX) ist vorbereitet in `50_INFRA/RECOLL_ANLEITUNG.md` —
  **Installation entscheidet David**.
- **Audit der eigenen Arbeit (auf Davids Wunsch):** sechs veraltete Zahlen in Dokumenten
  korrigiert (PROTOKOLL, BAUPLAN, ABSCHLUSSBERICHT, ETAPPE2_BERICHT); 4 Testreste neben dem
  Baum (24 MB) nach Pruefung geloescht; datierte Altabschnitte bleiben als Historie stehen.
- **Stand:** 12/12 Suiten · **213 Einzeltests** · Baum `0 Fehler · 318 geprueft` · 32 Commits ·
  Tag `v0.2.16-prototyp` · zweite Kopie 110 Dateien · Pruefsummen identisch.

## Ausbau-Schritt 3 — feste Projekt-Nummern (24.09.2026)

- **Regel:** Projektordner = `NNN_name_JJJJ-MM-TT`. Die **Nummer ist die Kennung** (bleibt dauerhaft),
  der Name ist die Beschriftung (darf sich aendern). Alte Form `JJJJ-MM-TT_name` bleibt gueltig —
  **kein bestehender Ordner wurde umbenannt.**
- **Werkzeug:** `./ordner.sh projekt "name" [bereich]` → naechste freie Nummer, Ordner, `STATUS.md`,
  Katalog-Eintrag. Doppelvergabe wird verweigert; unerlaubte Namen werden abgewiesen.
- **K6 schaerfer:** Nummer doppelt vergeben = **ERROR**; Nummer nicht dreistellig = HINWEIS.
- **Eigene Tests fanden zwei echte Fehler** (genau dafuer sind sie da):
  (1) meine Formpruefung verbot Unterstriche im Namen → `001_island_sprache_…` wurde beanstandet; behoben.
  (2) **der Baum war ueber seine eigene Breiten-Grenze gewachsen**: `70_AUTOMATION/tests` hatte
  21 Eintraege (erlaubt 20) → K7 ERROR. Nicht die Regel aufgeweicht, sondern Ordnung geschaffen:
  Suiten jetzt in `tests/weg1/` (8) und `tests/ausbau/` (5); `alle_suiten.sh` findet sie in
  beiden Ordnern. 29 Pfadangaben in den Suiten nachgezogen, `__pycache__` entfernt.
- **Stand:** 13/13 Suiten · **218 Einzeltests** · Baum `0 Fehler` · Tag `v0.2.18-prototyp`.

## Ausbau-Schritt 5 Teil 2 — PDF und Office durchsuchbar, ohne Installation (24.09.2026)

- **Installation nicht moeglich und nicht noetig:** `sudo` verlangt hier ein Passwort (nur David).
  Stattdessen die vorhandenen Werkzeuge genutzt: `pdftotext` (PDF) und `libreoffice --headless`
  (DOCX/ODT/XLSX/PPTX). Damit ist die Luecke geschlossen, ohne neue Abhaengigkeit.
- **Zwischenspeicher** in `60_RUNTIME/dokumenttext/`, benannt nach dem **Dateiinhalt** (SHA256):
  geaenderte Datei -> neuer Eintrag, kein veralteter Treffer moeglich. Nie in Git.
- **Messung an echten Daten:** Island-Dossier 16 PDFs -> Treffer IM PDF-Text;
  erster Lauf **1,5 s**, zweiter Lauf **0,1 s** (Zwischenspeicher, 15x schneller).
- **Tests f5/f6** (etappe32, jetzt 6 Tests): PDF-Treffer; **kaputtes PDF wird gemeldet** (`nicht lesbar`),
  nicht still uebersprungen.
- **Stabilisierung:** Design-CHANGELOG-Eintrag berichtigt — K7 wurde **nicht** veraendert
  (erzeugte Zwischenspeicher zaehlen schon nicht mit); die Breiten-Meldung war echt und wurde
  durch Ordnung geloest, nicht durch Regelaufweichung.
- **Stand:** 13/13 Suiten · 220 Einzeltests · Baum `0 Fehler · 330 geprueft`.

## Ausbau-Schritt 4 — finden und springen (24.09.2026)

- **Keine Installation noetig** (gemessen): `fdfind` und `fzf` sind schon da, `rg` ebenfalls.
  Kein Download, kein `sudo`, keine neue Abhaengigkeit.
- **Neu:** `./ordner.sh dateien "muster"` (Dateinamen im Baum UND in den angebundenen Bestaenden,
  Werkzeug wird mit ausgegeben) und `./ordner.sh springen "muster"` (Auswahlliste; mit fzf
  Pfeiltasten, ohne Terminal eine schlichte Liste). Proben: `PROTOKOLL` im Baum gefunden,
  `SUCHER` im **angebundenen** Island-Projekt gefunden, Gegenprobe 0 Treffer, 21 anspringbare Ziele.
- **Zwei eigene Fehler, beide vom Test gefunden und behoben:**
  1. In der neuen Testdatei stand `parents[3]` statt `parents[4]` -> die Testwiese lag **im Baum**,
     `copytree` lief in eine Endlosrekursion. Reste geprueft (keine im Baum), Testdatei korrigiert,
     alte Scratch-Ordner entfernt.
  2. Der Testlauf ohne PyYAML zeigte: ohne `yaml` waren die Zeiger-Dateien unlesbar und die
     Aussenbestaende fielen aus der Suche. **Rueckfall eingebaut** (`ziele_ohne_yaml`) — die Suche
     laeuft jetzt auch ohne PyYAML; der Test erzwingt das.
- **Stand:** 14/14 Suiten · **224 Einzeltests** · Baum `0 Fehler` · Tag `v0.2.21-prototyp`.

## Element 1 (aus der Recherche) — Duplikat-Bericht (24.09.2026)

- **Vorher geprueft, ob es ins System passt** (auf Davids Wunsch): Bericht, keine Regel — keine neue
  Datenbank, K1-K8 unveraendert, kein Cron, nur lesend, Loeschen nie automatisch. **Urteil: passt.**
- **Gebaut:** `./ordner.sh doppelt <Pfad>` (Pfad Pflicht — bewusste Empfehlung: nie ungefragt der
  ganze Rechner). Zweistufige Pruefung (Kopf 64 KB, dann voll), Hardlink-Erkennung, Bericht nach
  `60_RUNTIME/doppelt/` (nie in Git).
- **Messung an echten Daten:** `03_PROJEKTE` 53.086 Dateien / 10,83 GB → **13.276 doppelte Dateien =
  1,395 GB in 2,9 s** (Gruppierung 0,48 s). Davon **1,303 GB wiederherstellbar** (venv/node_modules) —
  das ist die handlungsfaehige Zahl: neu erzeugbar, kein Datenverlust. Ursache im Bericht sichtbar:
  z.B. 7x dieselbe 120-MB-`playwright/driver/node`, 3x dieselbe `curl_cffi`-Bibliothek.
- **6 Tests** (i1-i6) gruen: echte Dublette · **Hardlink ist KEINE Dublette** · Nullmeldung ·
  Unlesbares wird gemeldet · fehlender Pfad stoppt · venv getrennt ausgewiesen.
- **Eigener Fehler, ehrlich:** die neue Testklasse stand zuerst HINTER dem `unittest.main()`-Block
  und lief deshalb nicht ("Ran 5 tests"). Beim Reparieren entstanden Duplikate im Testfile; sauber
  neu zusammengesetzt, jetzt 1x main / 1x Klasse I / 1x Klasse J, 6 Tests. (Das ist genau die Falle,
  die in den Lehren steht — der eigene Fehler wurde zweimal gemacht und beim zweiten Mal bemerkt.)
- **Baum-Hygiene-Fund:** eine unversionierte Fremddatei `SUCHER.md` (268 B, 06:00 Uhr, nicht von mir)
  lag im Wurzelverzeichnis. **Nicht angefasst** — gemeldet, damit David entscheidet.
- **Stand:** 15/15 Suiten · 230 Einzeltests · Baum `0 Fehler` · Tag `v0.2.25-prototyp`.

### Korrektur (24.09.2026, abends)

Mein `git add -A` hat die fremde `SUCHER.md` **mitversioniert**, obwohl ich sie unangetastet lassen
wollte. Korrigiert: `git rm --cached` — die Datei **bleibt auf der Platte**, ist aber nicht mehr Teil
des Baums. Der Fehler bleibt in der Historie sichtbar (kein Wegschminken). Lehre: fremde Dateien im
Wurzelverzeichnis ausschliessen, bevor `git add -A` laeuft.

## Elemente 2-4 + Reste abgeschlossen (24.09.2026)

- **Waechter:** der Sucher-Waechter (`2b0262eb4405`, taeglich 06:00, `hermes-stable/scripts/sucher_waechter.py`)
  hatte `SUCHER.md` + leeren `sucher_results/`-Ordner in den Baum gelegt — es war **kein fremder Chat**,
  sondern sein normales Verhalten fuer jedes neue Git-Repo (Protokoll 06:00 nennt drei Repos). Auf Davids
  Wunsch **ausgenommen** (Ausschluss-Liste), die zwei Artefakte entfernt (Datei war 1 von 115 identischen).
  Baum-Wurzel wieder **15 Eintraege**, 0 offen.
- **README.md** geschrieben (DoD-Punkt 7): zehn Bereiche, dreizehn Befehle, "was garantiert / was nicht".
- **Scratch-Aufraeumen:** `alle_suiten.sh` entfernt Testreste `tmp*` neben dem Baum (nur eigene Namen, nie MASTER).
- **Element 4 BagIt (RFC 8493):** `bagit_bauen.py` + `./ordner.sh bag` — normgerechte Sicherung, von fremden
  Werkzeugen pruefbar. 4 Tests (b1-b4).
- **Element 3 Vorlagen:** `80_VORLAGEN/vorlagen.json` (standard/forschung/handwerk/trading) +
  `vorlage_anwenden.py`. 3 Tests (v1-v3). Eigener Fehler: `parents[3]` statt `parents[2]` -> 3 Tests rot,
  vom Test gefunden, korrigiert.
- **Element 2 RO-Crate 1.1:** `ro_crate.py` + `./ordner.sh crate`; `pruefen` rechnet die Selbstbeschreibung
  nach (Zeile `CRATE:`), damit sie nicht still veralten kann. 4 Tests (c1-c4).
- **Stand:** 16 Suiten · 242 Einzeltests · Baum 0 Fehler · Tag v0.2.30-prototyp.

### Nachtrag (24.09.2026): ein echter Fund beim Abschliessen

`PRUEFSUMMEN_MASTER.txt` und `ro-crate-metadata.json` beschrieben sich **gegenseitig** — sobald eines
geschrieben war, galt das andere als veraendert (`sha256sum -c` meldete "GESCHEITERT"). Aufgeloest:
der Crate listet die Pruefsummenliste **nicht** mit (eine Richtung genuegt, PRUEFSUMMEN deckt den Crate ab),
Test `c5` haelt das fest. Reihenfolge fuer die Zukunft: **crate bauen -> PRUEFSUMMEN erneuern -> committen**.

## Rollentrennung, Stichprobe, Zeiger-Crate, Sicherung mit Bag (24.09.2026, spaet)

- **ROLLENTRENNUNG GEMESSEN statt behauptet** (war die letzte ehrliche Luecke in jeder Pruefzeile):
  neues Werkzeug `rollentrennung_messen.py` laeuft mit 18 lesenden Befehlen gegen Baum + angebundenen
  Bestand, vergleicht vorher/nachher jede Datei (Groesse, Aenderungszeit, 100 Stichproben-Prüfsummen).
  **Ergebnis: VERIFIZIERT — 418 Dateien beobachtet, 0 Schreibspuren.** Die Pruefzeile zeigt jetzt
  `ROLLENTRENNUNG: VERIFIZIERT 2026-09-24 (...)`. Fehlt die Messdatei, steht dort weiter
  "NICHT VERIFIZIERT" — Test t2 haelt diese Ehrlichkeit fest.
- **50-MB-Grenze verbessert:** der K8-Zeiger prueft jetzt eine **Stichprobe von 16 gleichmaessig
  verteilten Dateien** einzeln nach. Live am Island-Zeiger: "Stichprobe 16 von 312 Dateien einzeln
  geprueft — alle identisch; Rest gilt als UNGEPRUEFT." Eine manipulierte Datei in der Stichprobe
  ergibt einen **Fehler** statt eines stillen Hinweises.
- **Element 2 fuer Bestaende:** `./ordner.sh crate --zeiger 47_Island_Sprache` legt eine
  `ro-crate-metadata.json` **im Bestand** ab (79 Dateien, 52,88 MB, GUELTIG nachgerechnet).
  Hinweis: das ist bewusst **eine** geschriebene Datei ausserhalb des Baums — auf Wunsch jederzeit loeschbar.
- **Element 3:** `bash sicherung.sh kopie <ZIEL> --bag` erzeugt jetzt in **einem** Befehl die normale
  Kopie **und** ein normgerechtes BagIt-Bag (Test t5: VALID).
- **5 neue Tests (t1-t5)**, davon t2 ein Ehrlichkeitstest (ohne Messung kein "OK").
- **Eigene Fehler in dieser Runde:** K8-Patch mit Ein-Zeichen-Variable `_` (haesslich, aber lauffaehig),
  `--zeiger` scheiterte zwei Mal an der Argument-Regel, Hilfsfunktion stand hinter dem main-Block
  (NameError) — alle drei gefunden und behoben; die Lehre "erst Struktur lesen, dann patchen" hat
  diesmal gegriffen, aber erst nach dem ersten Fehlversuch.
- **Stand:** 17 Suiten · 247 Einzeltests · 0 Fehler · Tag `v0.2.31-prototyp`.

## Punkt 4 + 6 (angefangen) und der neue Befehl `spross` (24.09.2026, Nacht)

- **Punkt 4 — 115 × SUCHER.md geprueft (nur gelesen):** 115 Dateien, aber **nur 2 verschiedene Inhalte**
  (114 identisch, 1 andere) · 26 davon in ihren Repos versioniert · 114 leere `sucher_results/`,
  3 mit Inhalt · viele liegen in `*.ARCHIVED_*`-Ordnern (also vor der Ausschluss-Regel entstanden).
  **Urteil: kein Schaden, nichts geloescht** — es sind Markierungen des Sucher-Waechters.
- **Punkt 6 — alte Doku-Widersprueche lokalisiert:** u. a. `CHANGELOG_DESIGN.md:34` nennt v1.3 "33,6 KB"
  (tatsaechlich groesser); die Widerspruchs-Stellen liegen in `daten/analyse_2.7_2.8/CHECKPOINT.md`,
  `daten/quellen/redteam/`, `Hermes-Git-Ordner/System-Check/`. **Noch nicht korrigiert** — als naechster Schritt.
- **NEU: `./ordner.sh spross <Ziel> [Name]`** — legt einen NEUEN Git-Ordner-Baum an (Bereiche, Werkzeuge,
  Tests, Doku; frische Historie; keine Daten/Zeiger; kein Ueberschreiben). Live geprueft: 10 Bereiche,
  102 Dateien, eigener Commit; zweiter Lauf bricht ab.
  **Ehrlich offen:** ein frischer Baum ist noch nicht selbst gruen — Katalog bringt Eintraege des
  Elternbaums mit (K4-Fehler) und die Selbsttest-Fixtures fehlen. Beides ist als einmalige
  Initialisierung dokumentiert (ANLEITUNG).
- **Stand:** 17 Suiten · 247 Tests · Tag `v0.2.34-prototyp`.

## Erweiterungen gebaut (24.09.2026, Nacht 2)

- **BagIt vervollstaendigt:** `tagmanifest-sha256.txt` (Pruefsummen ueber die Metadatendateien) —
  live geprueft: Manipulation an `bag-info.txt` wird als **METADATEN GEAENDERT** gemeldet; gueltiger Bag
  meldet "132 Pruefsummen nachgerechnet ... 3 Metadatendateien mitgeprueft (tagmanifest)".
- **RO-Crate:** Wurzel-Datensatz nennt Profil (`conformsTo` RO-Crate 1.1) + Lizenz.
- **Neu: `./ordner.sh formate`** — Dateitypen je Bereich (mit `file`) und Namensregeln; markiert
  risikoreiche Typen (live: 5 von 111 Dateien, HINWEIS) und aendert nichts. 15. Befehl.
- **4 neue Tests** (u1-u4) gruen; die alten BagIt/Crate-Tests (etappe36) laufen unveraendert weiter.
- **OpenCode 1.18.4** ist installiert; ob Zugangsdaten hinterlegt sind, wird vor der Fremd-Validierung geprueft.
- **Stand:** 18 Suiten · 251 Tests · 0 Fehler · Tag `v0.2.37-prototyp`.

## OFFEN — Klasse "Suite nur im Originalbaum" (aus der Fremd-Prüfung, 25.09.2026)

Zwei unabhängige Läufe des Prüf-Agenten in **Kopien** des Baums ergaben jeweils **5 rote Suiten**
(im Originalbaum: **0**). Die Menge ist nicht konstant — sie hängt davon ab, WAS die Kopie mitbringt
(Git-Historie, Messdatei der Rollentrennung, Fixtures neben dem Baum):

| Lauf | Kopie | rot |
|---|---|---|
| Prüf-Agent, Lauf 1 (vor Pfad-Fix) | beliebiger Name | 18 von 18 (= Namensabhängigkeit, **behoben**) |
| Prüf-Agent, Lauf 2 | `rt/eiswiese/MASTER` | 5 (etappe37, etappe28, test_suite + 2) |
| eigene Gegenprobe | beliebiger Name | etappe37, etappe25, etappe2, finalabnahme, gegenprobe25 |

**Deutung:** Diese Suiten prüfen Eigenschaften des *gemessenen Originalbaums* (z. B. "Messung gilt fuer
diesen Ort", Zeiger-Stichprobe, Git-Historie). In einer Kopie ist "NICHT VERIFIZIERT" dann die
**richtige** Antwort — der Test soll deshalb **überspringen mit Begründung**, nicht scheitern.

**Auftrag für den nächsten Chat:** je rotem Test entscheiden — (a) Voraussetzung fehlt → `skipTest`
mit Begründung ("braucht den gemessenen Originalbaum"), (b) echter Fehler → korrigieren.
Abnahmekriterium: **Kopie meldet 18 Suiten, 0 Fehler, N übersprungen (mit Begründung)**.

## Schritt 2 abgeschlossen (25.09.2026)

Der Pruefer nennt seine Dauer jetzt selbst, je Regel. Gemessen auf dem MASTER-Baum:
gesamt 0,43 s · Baumdurchlauf 0,01 s · Regeln 0,23 s (davon K2 0,21 s) · K9/CRATE 0,04 s ·
Selbsttest 0,08 s · Redundanz 0,00 s · Rest 0,04 s.

Vorher war die Pruefdauer ein Bauchgefuehl: die Testinstanz wurde zweimal abgebrochen (2 h
Zeitueberschreitung, 14:40 ohne Ende). Ursachen nach Groesse:
1. Mustervergleich mit zwei unbegrenzten [\w\-]* um eine Wortliste (Rueckverfolgung).
2. Vergleich ueber den ganzen 4-MB-Block statt zeilenweise.
3. Binaerinhalte wurden als Text geprueft, Deckel je Datei fehlte.
Behoben in v0.2.49 bis v0.2.54. Nachgewiesen: 64-MB-Binaerdatei 0,03 s; 2,25-MB-PDF 0,23 s
(vorher > 20 s); NUL-verstecktes AWS-Muster wird weiterhin gefunden.

Eigener Fehler, von den Suiten gefangen: die neue zeilenweise Suche pruefte nur die
abgeschlossenen Zeilen - in einer kleinen Datei ohne Zeilenumbruch fiel die einzige Zeile
durch (vier Suiten rot). Behoben in v0.2.52.

Offen: (a) {"client_secret":"..."} in JSON-Notation wird nicht erkannt (Anfuehrungszeichen
zwischen Wort und Doppelpunkt). (b) Die Zeittabelle steht auf stdout, noch nicht in der
Zustandsdatei 60_RUNTIME/state/status.json.

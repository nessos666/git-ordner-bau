# MASTER DESIGN — v1.3

**Status:** KORRIGIERTE FASSUNG nach Red-Team · **nicht umgesetzt**
**v1.3 ersetzt alle früheren Fassungen.** Bei Widerspruch gilt **diese** Datei.
**Grundlage:** 5 unabhängige Prüfrunden (Red-Team v1.0/v1.1, Verifikation v1.2/v1.3); Berichte in `daten/quellen/redteam/`.
**v1.3 korrigiert die 4 FAILs der v1.2-Verifikation und die Widersprüche der v1.3-Prüfung. Die Änderungs-Historie steht in `CHANGELOG_DESIGN.md` — nicht hier.** **Jede** Änderung in v1.1 löst ein dort
gefundenes Problem. Keine neue Schicht, keine neue Plattform, keine neue Hauptkategorie.
**Umfang:** 8 Kernregeln · 10 Bereiche · 2 Begriffe (Gate/Audit). **Größe ehrlich: 33 KB** — kleiner
als v1.0 (37 KB), **größer als v1.1** (25 KB), weil die Prüfrunden Härtung verlangt haben
(siehe `CHANGELOG_DESIGN.md`).
**Freigaben:** 1a Regelwerk vereinfachen · 2a Prüfer + Empfänger · 3a Schlüsselübergabe.

---

## 1 · Leitprinzipien

| # | Prinzip | Beleg |
|---|---|---|
| P1 | **Flache Topologie** — Ziel 3–4 Ebenen, harte Grenze 5 | Bergman: gelebte Tiefe 2,86 (JASIST 2010) |
| P2 | **Breite gedeckelt** — ≤ 20 je Ordner, Ziel 8–12 | Miller 1981 · Bergman 2010 · UK Data Service |
| P3 | **Eine Sortierachse pro Ebene** — Funktion, nicht Thema | Johnny.Decimal · NARA |
| P4 | **Stabile Kennung** — einmal vergeben, nie geändert | Johnny.Decimal |
| P5 | **Index ÜBER dem Baum** — nicht der Baum trägt die Ordnung | Taxonomie-Algebra (arXiv cs/0312059) |
| P6 | **Erzwingung statt Absicht** — der Prüfer, nicht der Mensch | nixpkgs-vet in CI · 84,5 % Terraform-Repos mit Smells |
| P7 | **Klassen trennen** — Quelle ≠ Konfig ≠ Zustand ≠ Artefakt ≠ Cache | ArgoCD · XDG · 12-Factor |
| P8 | **Pinning nur für Fremdes** — nie falsche Autorität erzeugen | Google `repo` Tiefe 8 · `west` zerstört Bisect |
| P9 | **Teil-Automatik** — Automatik **meldet**, verändert nicht | Voll-Automatik widerlegt (Wellen 3/7) · Automation Bias |
| P10 | **Verfallen ist normal** — Archiv ist Pflicht | < 50 % überleben 5 Jahre (ESEM 2019) |
| P11 | **Kein Inhalt in Git, der groß, erzeugt oder geheim ist** | GitHub: *"Git is not designed to handle large SQL files"* |
| P12 | **Backup ≠ Repo** — zweite Kopie, Prüfung, Restore-Test | *"A snapshot is not a backup"* (Btrfs) · CISA |

*Die Änderungs-Historie steht **nicht hier**, sondern in `CHANGELOG_DESIGN.md` — Historie im
Regeltext erzeugt Selbstwidersprüche (in der v1.2-Verifikation nachgewiesen).*

---

## 2 · Die 8 Kernregeln (ersetzt R1–R15)

**Auswahlmaßstab:** eindeutig prüfbar · wenig Fehlalarm · für einen Menschen verständlich ·
langfristig wartbar. **Zusammengeführt, was dasselbe Ziel hat; entfernt, was keinen Schutz bringt.**

### K1 · Keine verbotenen Inhalte in Git
Ein Git-Repository enthält **niemals**: Daten **über der Schwelle** (10 MB) · **Artefakte** ·
Modelle · Logs/Zustand/Caches · Abhängigkeitsordner (`.venv`, `node_modules`, `target`, `__pycache__`) ·
komprimierte Archive · Datenbankdateien. **„Artefakt" ist ausdrücklich mitgemeint** (fehlte in v1.2).
**Schwere:** Verstoß (schwer bei Daten > 100 MB)
*Ersetzt: R3, R8, R12. Ein Ziel: „Git ist kein Massenspeicher."*

### K2 · Kein Secret in Git
Keine Schlüssel, Token, Passphrasen, `*.env`, `credentials*.json`.
**Schwere: CRITICAL** — und bei Treffer greift **Pflichtreaktion (Abschnitt 11)**, nicht nur Meldung.
*Ersetzt: R4, aufgewertet. Ein Ziel: „Kompromittierung verhindern."*

### K3 · Pflichtdateien je Klasse
Git-Repo: `README.md` + `.gitignore`. Aktives Projekt zusätzlich `STATUS.md`.
**Wissensartefakt mit Status ≠ `provisional`:** Herkunftskopf vorhanden.
**Schwere:** Verstoß
*Ersetzt: R1, R2, R13 (Provenienz bleibt gefordert, aber nicht im Bootstrap).*

### K4 · Katalog ↔ Realität, bidirektional
Für **jeden** Katalogeintrag: existiert `pfad`? passt `class` zum `bereich`? hat `git: true`
tatsächlich ein `.git`? ist `pin` **genau dann** gesetzt, wenn `extern: true`? (**beide Richtungen** — „extern ohne Pin"
ist ebenso ein Verstoß wie „eigenes Repo mit Pin", F-c)
**Und umgekehrt:** liegt ein vorhandenes Repo vor, das der Katalog **nicht** kennt?
**Bei Abweichung: melden. NIEMALS automatisch reparieren.**
**Schwere:** Verstoß (CRITICAL, wenn `pfad` fehlt)
*NEU — war die größte Lücke in v1.0. Ersetzt R9, R11, R14.*

### K5 · Katalogzeile vollständig und Status gültig
Pflichtfelder: **`schema_version`**, `name`, `class`, `status`, `owner`, `seit`, `bereich`, `pfad`, `git`.
`status` ∈ {`provisional`, `active`, `paused`, `done`, `abandoned`, `archived`}.
`active` **muss** `review_am` haben. `provisional` ist von Vollständigkeitsprüfungen **ausgenommen**
(Abschnitt 12).
**`schema_version` ist Pflichtfeld.** Ohne es ist eine
Migration v1 -> v2 nicht prüfbar. Aktuell: **`schema_version: 1`**.
**Global eindeutig:** `name` **und** `pfad` je **nur einmal** im Katalog. Doppelte = Verstoß.
**Schwere:** Verstoß
*Ersetzt: R9, R15. Enthält den Bootstrap-Ausweg.*

### K6 · Namen und Pfade
Pfad ≤ **255** Zeichen · nur `a-z 0-9 _ -` · Datum bei Neuanlage `YYYY-MM-DD_` vorne ·
**keine Case-Kollision** im selben Ordner (OS-Wechsel!).
**Schwere:** Hinweis (Verstoß bei Pfad > 255 oder Case-Kollision)
*Ersetzt: R5, R6, R7. Ein Ziel: „maschinell lesbar, OS-unabhängig."*

### K7 · Tiefe und Breite — Zählung definiert
**Tiefe: ≤ 5 ab MASTER-Wurzel. Alle Ebenen werden gezählt. KEINE Ausnahmen.**
*Ziel 3–4, harte Grenze 5. Die alte Ausnahme „Projektinhalt zählt nicht" war umgehbar — gestrichen.*
→ `MASTER/20_PROJEKTE/domains/recherche/projekt/01_input/` = **5** ✓ · `…/01_input/details/` = **6** ✗
**Breite:** ≤ **20** Einträge je Ordner.
**Einzige Ausnahme, PFADBASIERT:** der Ordner **`50_INFRA/nodes/`** — verwaltete Ressourcenliste,
darf gruppiert werden (`nodes/<gruppe>/<host>.yaml`); **logische Node-ID steht im Dateiinhalt, nicht im
Pfad**. Ein Ordner, der **irgendwo anders** `nodes` heißt, ist **keine** Ausnahme.
**Kapazität — ehrlich gerechnet (der Prüfer hat meinen Rechenfehler widerlegt):**
Projektordner liegen auf Ebene 4 (`…/domains/<thema>/<projekt>/`) -> **20 × 20 = 400 Projekte**
+ **20 in `standalone/`** = **~420**. *Falsch war die Behauptung „10.000 passen" (Faktor ~24 zu hoch).*
**Reicht das?** Ja, mit Reserve: der echte Bestand umfasst ~50 echte Projekte. **Ehrlich bleibt:**
wer 420 überschreitet, braucht eine andere Ordnung — **nicht** dieses Design.
**Keine Ausweitung der Tiefe, um Zahlen zu retten.**
**Schwere:** Hinweis (Verstoß ab 6 Ebenen bzw. 21 Einträgen außerhalb `50_INFRA/nodes/`)
*Löst T1 (Selbstwiderspruch) und F6 (100 Rechner). Ersetzt R5.*

### K8 · Externe Objekte haben eine Prüfsumme
Jeder Zeiger in `40_DATEN` nennt: **Pfad/URL · Größe · SHA-256 · Datum · Rekonstruktionsweg**.
**Schwelle:** Einzelprüfsumme **nur für Objekte > 10 MB** (und für gepinnte externe Repos).
Kleine Massendaten werden **auf Datensatz-/Manifestebene** abgesichert (eine Prüfsumme für
das Paket, nicht je Datei).
**Obergrenze:** bis **1.500 Zeiger** einzeln; darüber **Aggregation**.
**Aggregation ist ERLAUBT und definiert** (der Widerspruch „fehlende Einzelprüfsumme = Verstoß" vs.
„Aggregationspflicht" ist damit aufgelöst):
> **Datensatz** = **ein Ordner mit `manifest.yaml`**. Geprüft wird **eine** SHA-256 über das
> **Manifest** (das die Einzeldateien mit Größe listet). Ein Zeiger auf einen Datensatz erfüllt K8
> **vollständig** — **keine** Einzelprüfsumme je Datei nötig.
*Gemessen (Verifikation): **3.307** Objekte > 10 MB (die Zahl 3.271 war veraltet);
1.500 × 250–350 B = 375–525 KB -> Budget hält mit Reserve.*
**Ziel: `40_DATEN` bleibt unter 1 MB** — Katalog-, Zeiger- und Manifest-Schicht, **kein Datenberg**.
**Schwere:** Verstoß bei fehlender Prüfsumme für ein Objekt > 10 MB
*Ersetzt: R11, löst F10.*

### Was entfernt wurde — und warum
| Entfernt | Grund |
|---|---|
| R14 (Archiv unverändert) | **Die Git-Historie belegt Unveränderlichkeit bereits.** Eigene Regel ohne Zusatznutzen. |
| R7 (Datums-Hinweis als eigene Regel) | **in K6 aufgegangen** (gleiches Ziel). |
| R15 (review_am) | **in K5 aufgegangen** (gleiches Ziel). |
| Regel für Symlinks | Kein prüfbarer Schutz — Symlinks sind **gemeldet**, nicht regelbar (Abschnitt 20). |

---

## 3 · Gate und Audit — die Trennung

| Begriff | Was es ist | Kann | Kann NICHT |
|---|---|---|---|
| **GATE** | Prüfung vor/mit Commit (Hook) | verhindern | **umgehbar** (`--no-verify`) |
| **AUDIT** | Prüfung nachträglich (Nachtjob) | erkennen | nichts verhindern — ein Secret ist dann draußen |

**Klare Sprache, verbindlich:** Ein **Nachtjob ist ein AUDIT und kein Gate.** Ein Hook ist ein
**weiches Gate**. In v1.1 wird **nie** behauptet, der Nachtjob schließe die Lücke.

**Konsequenz (ehrlich):** Für Secrets gibt es **kein hartes Gate ohne Plattform**.
Deshalb ist bei K2 die **Reaktionskette** (Abschnitt 11) der eigentliche Schutz — nicht die Erkennung.

---

## 4 · Der Prüfer und sein Empfänger

**Ablauf (verbindlich):**
> **Prüfer -> Ergebnis -> bestehender Tagesbericht -> sichtbarer Status**

**Vier Statuswerte:**
| Wert | Bedeutung | Erwartete Reaktion |
|---|---|---|
| **OK** | keine Abweichung | keine |
| **WARNING** | Hinweis (K6, K7) | ansehen, wenn Zeit |
| **ERROR** | Regelverstoß | beheben |
| **CRITICAL** | Secret, fehlender Pfad, Prüfsumme falsch | **sofort** — Reaktionskette |

**Der Prüfer überwacht sich selbst (Pflicht):**
- Er schreibt bei **jedem** Lauf eine **Herzschlag-Datei** (Zeitstempel).
- Der **Toter-Mann-Schalter überwacht Sicherung UND Prüfer**.
- **Oberstes Glied, extern verankert:** ein lokal still sterbender Wächter ist lokal **nicht
  erkennbar** — deshalb **wöchentlicher Kalendertermin** (manuell) + **Wartungslauf 1×/Quartal**.
  Der Kalender ist der **einzige Anker außerhalb** des Systems.
- Herzschlag älter als **26 Stunden** -> Meldung **CRITICAL: „Prüfer ausgefallen — Status UNBEKANNT"**.
- **Ein ausgefallener Prüfer wird NIEMALS als „alles OK" gelesen.**
- Der Prüfer hat einen **Selbsttest** (Fixture mit bekannten Fehlern): findet er die nicht,
  ist **er** defekt -> CRITICAL. *Behebt: „0 Verstöße ≠ 0 gemacht".*

**Ausgabe — mit ECHTEM Träger:**
> **Der in v1.1 vorausgesetzte 07:00-Bericht EXISTIERT NICHT.** Die Dateien um 07:00 stammen aus
> **stündlichen** Jobs (`0 * * * *`) mit Status „silent (empty output)"; der einzige ausgelieferte
> Tagesbericht läuft **10:10** (KI-Radar). `Integrity Watchdog (07:00, deliver: local)` ist der
> lebende Beweis, dass dieses Muster hier schon ausfällt.

**Verbindlich:**
1. **Träger = Telegram** (gegenwärtig der **einzige verbundene externe Kanal**).
2. **Format:** `PRÜFER: OK · 0 Fehler · 2 Hinweise · 12.345 geprüft · Herzschlag 07:03`
3. **Lesenachweis:** `60_RUNTIME/state/quittung` — Zeitpunkt + Status je Lauf. Zustellfehler = **CRITICAL**.
4. **Wiederholung:** **ERROR/CRITICAL täglich erneut**, bis Empfangsbestätigung; **WARNING** einmal.
5. **Ohne Quittung > 7 Tage** -> Status **UNBESTÄTIGT** (nie „OK").

---
## 5 · Der Baum

```text
MASTER/
├── 00_SYSTEM/      Regeln, Katalog, Schemas, Prüfregeln, Herkunftsvorlage, ÜBERNAHME.md
├── 10_AGENT/       Prompts, Skills, Werkzeuge, Konfigs
├── 20_PROJEKTE/    domains/ + standalone/
├── 30_WISSEN/      research/ + dossiers/ + references/
├── 40_DATEN/       catalog/ + pointers/ + manifests/ + checksums/   (unter 1 MB!)
├── 50_INFRA/       nodes/ + services/ + network/ + deployment/
├── 60_RUNTIME/     Zustand, Logs, Cache, Modelle   → NICHT versioniert
├── 70_AUTOMATION/  validation/ + indexing/ + cross-repo/ + maintenance/
├── 80_VORLAGEN/    Projekt-, Dossier-, Node-, Skill-Vorlage
└── 90_ARCHIV/      abgeschlossen, schreibgeschützt
```
**Zehn Bereiche — dabei bleibt es.** (Red-Team: das Deutungsmonopol der Bereiche hat standgehalten.)

**Darüber:** der **Index** — er trägt Beziehungen, nicht der Baum.

## 6 · Die zehn Bereiche — Kurzspezifikation

*Jeder Bereich in 6 Zeilen.*
🔴 **Klarstellung (Verifikationsbefund): Die Bereiche sind ZIEL-Struktur, nicht Bestand.**
Wo ein Bereich **heute nicht existiert**, steht der **reale Ort**.
**`10_AGENT` existiert heute nicht** — realer Bestand: `~/.hermes/` (148 Dateien oberste Ebene,
29 Skill-Ordner); versionierte Skripte in `~/hermes-stable/`.
*`10_AGENT` ist das **Ziel**, sobald Prompts/Skills/Werkzeuge versioniert werden.*

| Bereich | Darf hinein | NIEMALS | Git / Repo | Benennung · Prüfung | Archiv · nach 5 Jahren |
|---|---|---|---|---|---|
| **00_SYSTEM** | Katalog, Schemas, Regeln, Herkunftsvorlage, `ÜBERNAHME.md` | Daten, Modelle, Logs, erzeugte Indizes | **1 dünnes Meta-Repo** | `repos.yaml`, `rules.yaml` · Selbsttest | nie archiviert; Regeln versioniert |
| **10_AGENT** | Prompts, Skills, Werkzeuge, Konfigs (**je mit Version**). **Besitzregel, an der REALITÄT ausgerichtet:** heute ist `~/.hermes/` der Bestand und `~/hermes-stable/` die versionierte Quelle (Symlink-Regel). **Sobald `10_AGENT` angelegt ist:** `10_AGENT` = Quelle, `~/.hermes/` = Laufzeit-Kopie. **Bis dahin keine Behauptung, nur der reale Weg.** | Modellgewichte, Indizes, Session-Logs, **Secrets** (nur Verweis) | **1 Repo** | `SKILL.md`, `name_v3.md` · Zweck+Datum+Modell | alte Versionen ab 10 Stück ins Archiv |
| **20_PROJEKTE** | Code, Text, kleine Testdaten (< 10 MB) | `.venv`,`node_modules`,`target`,`__pycache__` · Daten > 10 MB · Logs | **Domänen-Bündel** + echte Einzelne | `YYYY-MM-DD_name` · K3 | Abschluss → Archiv; **18 Monate ohne Änderung → Flag** |
| **30_WISSEN** | Markdown, kleine PDFs, Zitate **mit Quelle** | große PDF-Sammlungen · kopierte Werke ohne Quelle | **je Thema 1 Repo** | `YYYY-MM-DD_thema.md` · K3 (Herkunftskopf) | Rohmaterial > 3 Jahre ins Archiv; **Link-Rot-Prüfung jährlich** |
| **40_DATEN** | **nur** `yaml`,`json`,`sha256`,`md` | **kein einziges Datenbyte** (Parquet, DBN, CSV, Modelle, `.zip`) | **1 winziges Repo** | `*_pointer.yaml` · K8 · **< 1 MB** | Zeiger bleiben, `status: archiviert`; Prüfsummenlauf zeigt Bit-Rot |
| **50_INFRA** | Node-/Dienst-/Netz-Beschreibungen | Passwörter im Klartext · Laufzeitdaten | **1 Config-Repo** (≠ Code!) | `nodes/<host>.yaml` · K5 | `retired` statt löschen; Datei bleibt |
| **60_RUNTIME** | Zustand, Logs, Cache, Modelle | **— alles Flüchtige ist hier richtig** | **KEIN Repo** | frei · K1 verbietet es in Git | Cache löschen, Zustand sichern, Logs 30 Tage |
| **70_AUTOMATION** | Prüfskripte, Index-Erzeuger, Wartung | **ein Skript, das löscht oder verschiebt** | **1 Repo** | `check_*.sh`, `rebuild_*.sh` · `--dry-run` | abgelöste Skripte ins Archiv; **Jahres-Review** |
| **80_VORLAGEN** | Vorlagen mit Platzhaltern | echte Daten, Namen, Schlüssel | **1 Repo** | Ziel-Benennung · Vorlagen müssen K1–K8 selbst erfüllen | alte Versionen ins Archiv; **stärkster Hebel gegen Verfall** |
| **90_ARCHIV** | fertige Projekte, alte Versionen, ausgemusterte Nodes | aktive Projekte · **nichts wird zurückgeholt und geändert** | Historien-Repos, schreibgeschützt | `YYYY_name` · K4 | **Selektion jährlich** (DCC: nur 4–5 % dauerhaft) |

## 7 · Der Katalog (korrigiert)

**Ort:** `00_SYSTEM/manifest/repos.yaml` · **Schema:** `00_SYSTEM/schemas/repos.schema.json`

| Feld | Pflicht | Regel |
|---|---|---|
| **`schema_version`**, `name`, `class`, `status`, `owner`, `seit`, `bereich`, `pfad`, `git` | ✅ immer | siehe K5 |
| `extern` | ✅ | `true` = **fremdes** Repo |
| `pin` | nur bei `extern: true` | **SHA oder Tag** |
| `remote`, `review_am` | bei `status: active` | `review_am` = +1 Jahr |
| `pruefsumme`, `rekonstruktion` | bei Zeigern (K8) | SHA-256 + Weg zur Wiederherstellung |
| `notfallkontakt`, `passphrase_ort` | ✅ einmalig im Kopf der Datei | **nur Verweis, niemals der Wert** |

**Die neue Pin-Regel:**
> **Fremde externe Abhängigkeit** -> `pin: <SHA|Tag>` — hier ist Pinning richtig und nötig
> (Google `repo`, `west`: Branch-Refs zerstören die Bisektierbarkeit).
> **Eigenes aktives Repo** -> **kein Pin** und **kein Ersatzfeld** (informative Felder ohne
> Prüfwert wurden gestrichen).
> **Begründung:** Ein SHA-Pin auf ein eigenes, aktiv entwickeltes Repo **veraltet bei jedem Commit**
> und erzeugt **falsches Vertrauen**.

**Wahrheitsregel (präzisiert):**
> Der Katalog ist die Wahrheit über die **Absicht** (wo, was, wem gehörend).
> Die **Dateien** sind die Wahrheit über die **Existenz**.
> **Widerspruch ist ein Fehler, kein Vorrang** — K4 meldet ihn, ein Mensch entscheidet.
> *(v1.0 sagte „der Katalog gewinnt" — das war einseitig.)*

## 8 · Automatik

**Erlaubt (Rangfolge nach belegtem Nutzen/Aufwand), alles **Audit**, nicht Gate:**
A1 Toter-Mann-Schalter (**überwacht Sicherung UND Prüfer**) · A2 Sicherung · A3 Prüflauf ·
A4 Index-Neuaufbau · A5 Sicherungsprüfung (monatlich) · A6 Wiederherstellungs-Test (**vierteljährlich**) ·
A7 tote Links/Symlinks melden (**jährlich**) · A8 Dubletten-Report (`--dry-run`, vierteljährlich)

**Verboten:** Auto-Verschieben · Auto-Löschen · Auto-Tagging ohne Korrektur · KI schreibt
unbeaufsichtigt · ein globales Monorepo.

**Zeitplan:** täglich Prüfung + Index + Sicherung · danach **Statuszeile nach Telegram**
(Abschnitt 4 — **nicht** „in einen Bericht", der nicht existiert) · monatlich Sicherungsprüfung ·
**vierteljährlich Restore-Test** · vierteljährlich Dubletten-Report.
*Der frühere jährliche Restore-Test widersprach Abschnitt 9 — jetzt einheitlich.*
`Persistent=true` holt verpasste Läufe nach — **ersetzt aber NICHT die Prüfer-Überwachung**
(`Persistent=true` fängt keinen hängenden Job — Red-Team-Befund).

## 9 · Backup — ehrlich (unverändert kritisch)

> **BACKUP + INTEGRITY CHECK + RESTORE TEST + SECOND LOCATION**

| Stufe | Stand **heute** |
|---|---|
| 1 Sicherung läuft | ✅ (07:00) |
| 2 Integritätsprüfung | ❌ fehlt |
| 3 Restore-Test | ❌ fehlt — **Sicherung ist unbewiesen** |
| 4 zweiter Ort | ❌ fehlt — **Risiko Nr. 1 unverändert: ~95 % ohne Kopie** |

*Kosten (Schätzung, R3): Stufe 2 ~100 GB/Monat Vollread · Stufe 4 60–120 € Platte oder ~72 $/TB/Jahr Cloud · Restore-Test Stunden/Jahr.*
**Backup liegt AUSSERHALB des Baums.**

### 🔴 P0 — Vorbedingung, blockierend
> **Ohne zweite Kopie ist dieses Design nicht schützend — nur ordentlich.**
| Element | Regel |
|---|---|
| **P0** | **zweite Kopie an einem anderen Ort.** Billigster Weg: **externe Platte, 60–120 €** (Schätzung); Alternative Cloud ~72 $/TB/Jahr |
| **Erkennung (neu — vorher fehlte sie)** | Der Prüfer **liest den Kopf/Index des Sicherungsarchivs am zweiten Ort**. Erst nach **erfolgreichem Lesen** gilt `REDUNDANZ: vorhanden`, sonst `FEHLT`. **Kein zweiter Ort = FEHLT** (nicht „unbekannt") |
| **Sichtbarer Status** | Statuszeile führt **`REDUNDANZ: vorhanden ODER FEHLT`**. Bei `FEHLT` steht über jedem „OK": **Schutz nicht vorhanden** |
| **Restore-Test** | **quartalsweise** statt jährlich (verkürzt die 12-Monats-Latenz, R1-Empfehlung) |
**Bewusst akzeptiert:** P0 ist eine **Anschaffung**, keine Designfrage. Das Design kann Redundanz
**nicht ersetzen** — nur **benennen**.

## 10 · Die fünf Datenklassen

| Klasse | Wohin | In Git? | Sichern? | Löschbar? |
|---|---|---|---|---|
| Quelle | Baum im Repo | **JA** | ja | nein |
| Konfiguration | `50_INFRA`, `~/.config` | **JA** | ja | nein |
| Zustand | `60_RUNTIME/state` | **NIEMALS** | **JA** | nein |
| **Artefakt** | `60_RUNTIME/artefakt` | **NIEMALS** | **JA — zwingend!** | **NEIN** |
| Cache | `60_RUNTIME/cache` | **NIEMALS** | nein | **JA** |

**Die Zuordnung Cache ↔ Artefakt — prüfbare Regel statt Gefühl:**
> **Artefakt ist alles, dessen Neuerzeugung (a) länger als 1 Stunde dauert, (b) Geld kostet oder
> (c) fremden Zugriff erfordert. Im Zweifel: Artefakt.**
**Namentlich Artefakt (immer):** **eigene Finetunes/Modellgewichte** · trainierte Indizes ·
Datensätze aus **bezahlten** Schnittstellen · halbfertige Auswertungen · Konfigurationen mit
manuell erarbeitetem Anteil. **Cache (nur):** herunterladbare Fremdmodelle · Zwischenrechnungen aus
vorhandenen Rohdaten in < 1 h · Indizes, die in < 1 h entstehen.
*Red-Team: ein 80-GB-Finetune galt als „Cache" -> Totalverlust. Der alte 5-Minuten-Test war
subjektiv und damit die einzige unprüfbare Regel des Dokuments.*

## 11 · Secrets — Erkennung UND Pflichtreaktion

**Wenn ein Secret gefunden wird, ist Erkennung NICHT genug. Verbindliche Reihenfolge:**

1. **Als kompromittiert behandeln** — ab dem Moment der ersten Erkennung.
2. **Sofort rotieren/widerrufen** — neuer Wert, alter Wert ungültig machen.
3. **Auswirkungen prüfen** — was war mit dem Wert erreichbar? Was ist passiert?
4. **Historienbereinigung nur ZUSÄTZLICH**, wenn sinnvoll (kein Ersatz für Schritt 2).
5. **Annehmen, dass Forks/Klone die alten Werte weiterhin besitzen.**
   `git filter-repo` erreicht **Forks und PR-Refs nicht**.

> **Verbindliche Aussage: „History-Rewrite allein löst das Problem NICHT."**
> Die **Rotation** ist die einzige echte Behebung.

**Für K2 gilt deshalb:** Erkennung -> **CRITICAL** -> **Reaktionskette**. Nicht „gemeldet, fertig".

**Wer führt sie aus?**
| Rolle | Wer |
|---|---|
| **Ausführer** | **David** (eine Person — das wird nicht schöngeredet) |
| **Auslöser** | Telegram-Zeile + tägliche Wiederholung |
| **Eskalation** | unbeantwortet **≥ 3 Tage** -> erneute Meldung mit dem Wort **UNERLEDIGT** |
| **Notfallweg** | wenn David nicht kann: **Notfallkontakt** (Abschnitt 18); die Kette steht in `ÜBERNAHME.md` |

---
## 12 · Bootstrap — `provisional` -> `active`

**Der Zirkel in v1.0:** Ein neues Projekt musste `pinned_sha` (Commit, den es noch nicht gibt),
eine Herkunft (die es noch nicht gibt) und Validatorangaben (die es noch nicht gibt) vorweisen.
**Ergebnis: der Weg des geringsten Widerstands führte in den alten Zustand.**

**Lösung — ein Status, zwei Phasen:**

| Phase | Erforderlich | Nicht erforderlich | Prüfverhalten |
|---|---|---|---|
| **`provisional`** | Ordner existiert · Katalogzeile mit **`schema_version`**, `name`,`class`,`status`,`owner`,`seit`,`bereich`,`pfad`,`git` | `remote`, `pin`, `review_am`, Herkunftskopf | **von Vollständigkeitsprüfungen ausgenommen** (K5). Nur K4 (Pfad existiert) gilt. |
| **`active`** | alles oben **+** `remote` (bei `git:true`) · `review_am` · Herkunftskopf bei Wissensartefakten | — | volle Prüfung |

**Übergang:** nach dem ersten Push (bzw. dem Anlegen der Herkunft) setzt **ein Mensch** den Status
auf `active`. **Keine Automatik.**
**Bremse:** bleibt ein Eintrag länger als **30 Tage** `provisional`, gibt es **WARNING**
(kein ERROR — neu angefangene Dinge dürfen klein sein).

## 13 · Herkunft (Provenienz) — Vorlage, nicht Bremse

**Kernbefund bleibt (Agent B):** Es gibt **keinen Standard** für die Herkunft von
**Wissensartefakten** — alle Standards adressieren Builds (SLSA, in-toto), Datensätze (Croissant),
Medien (C2PA) oder Modelle (Model Cards). Deshalb: **eigener YAML-Kopf**, mit belegten Vorbildern
(`dvc.lock`: Hash von Ein- **und** Ausgaben · OpenLineage: **Git-SHA** als Standardfeld).

**Pflicht (K3) erst ab Status `active`** — für **Wissensartefakte**. Felder:
`artefakt` · `quelle_repo` · `quelle_commit` · `erzeuger` · `modell` · `eingaben` · `workflow` ·
`ausgabe_sha256` · `zeitpunkt`.

**Drei billige Gegenproben — Pflicht, sonst ist Herkunft Fälschung mit 0 Aufwand:**
1. Existiert der genannte **`quelle_commit`** im genannten Repo?
2. Existiert **jede** Datei aus `eingaben`?
3. Stimmt **`ausgabe_sha256`** mit der Datei überein?
Verstößt eine -> **Verstoß** (K3).

**Ehrliche Grenzen:** keine Inhaltswahrheit · keine Satz-Ebene · **kein Schutz gegen Fälschung
ohne externen Anker** (das leistet erst eine Signatur — **Stufe 4, nicht jetzt**).
**Bewusst NICHT aufgenommen:** SLSA/PROV als Format für Wissen (**falscher Zweck**: sie decken Builds ab, nicht Wissen).

## 13b · Der Index

Der **Index** liegt **über** dem Baum, ist **Cache** und beantwortet Fragen — er ist **keine** Wahrheit.
**Ort:** `60_RUNTIME/state/index/` (**nie** in Git). **Aufbau: nächtlich vollständig neu, nicht
gepflegt** *(gemessen: FTS5 über 47.042 `.md` = 5,6 s; 269.018 Dateien = 102,7 s, Abfragen
0,5–6,2 ms)*. **Weil der Neuaufbau billig ist, ist Index-Drift kein Risiko.**
**Pflicht:** Ausschlussliste (`cache`, `models`, `.git`, Abhängigkeitsordner) · **Sperre** ·
**Zeitlimit**. *Freiwillig:* Selbsttest, Frische-Monitor — der Index ist Cache.

## 14 · Maschinen (Nodes) — verwaltete Liste

- **`nodes/` ist von K7 (Breite ≤ 20) AUSGENOMMEN.** Es ist eine **verwaltete Ressourcenliste**.
- Bei großen Mengen **darf gruppiert/projiziert werden** (`nodes/<gruppe>/<host>.yaml`),
  **ohne die logische Node-ID zu ändern**: die **ID steht im Dateiinhalt**, nicht im Pfad.
- **Eine neue Maschine = eine neue Datendatei. KEINE neue Baumebene, keine neue Hauptkategorie.**
- Felder: `name`,`role`,`os`,`status`(`active`/`retired`),`seit`. Ausgemusterte bleiben als `retired`.
- **Belegt:** Ansible `host_vars/<host>.yaml` (1 NUC + 4 Pis) · ArgoCD *"the filesystem IS the
  deployment matrix"* · colmena `deployment.tags`.

## 15 · Neuer Rechner

1. **eine** Datei `50_INFRA/nodes/<host>.yaml` · 2. **eine** Katalogzeile (`class: infra`) ·
3. `git clone` der nötigen Repos · 4. Zustand **aus dem Backup** (nicht aus Git) ·
5. Daten **neu erzeugen/laden** laut Zeigern · 6. Prüfer laufen lassen.
**Was sich NICHT ändert:** keine Baumebene, keine Kategorie, kein Umbau.

## 16 · Neues Projekt — korrigierter Ablauf

1. **Entscheiden:** eigenes Repo? (nur bei eigenem Lebenszyklus **oder** Veröffentlichung) — sonst ins Domänen-Bündel
2. **Ort:** `20_PROJEKTE/domains/<thema>/` oder `standalone/`
3. **Vorlage kopieren** aus `80_VORLAGEN/projekt/`
4. **Benennen:** `YYYY-MM-DD_name`
5. **Katalogzeile mit `status: provisional`** — Pflichtfelder: **`schema_version`**, `name`,`class`,`status`,`owner`,`seit`,`bereich`,`pfad`,`git`
6. **Arbeiten.** Kein Commit-Zwang, keine Herkunft, kein Pin.
7. **Bei Bedarf auf `active`:** ersten Push machen -> `remote` eintragen -> `review_am` setzen ->
   Herkunftskopf anlegen -> Status umstellen. **Vom Menschen, nicht automatisch.**

> **Der Unterschied zu v1.0:** Nichts muss vorweisbar sein, **bevor** es existiert.
> Der Einstieg kostet jetzt **~2 Minuten**, nicht „alle Regeln erfüllen".

## 17 · Über 5 und 10 Jahre

| Zeitpunkt | Was passiert |
|---|---|
| **jährlich** | Review: `review_am` erreicht -> Status prüfen (K5) |
| **18 Monate ohne Änderung** | `status: abandoned` **setzen** (Flag, **keine Löschung**). **Auslöser definiert:** „ohne Änderung" = kein neuer Commit und keine Katalog-Aktualisierung. |
| **danach 90 Tage** | **Entscheidungsfrist:** *pausieren*, *abschließen* oder *archivieren*. Läuft sie ab: Eintrag im Bericht als **UNENTschieden** (ERROR, nicht WARNING). |
| **nach Abschluss** | `STATUS.md` + Datum -> `90_ARCHIV/<jahr>/`, schreibgeschützt |
| **5 Jahre** | Archiv-**Selektion** (DCC: nur 4–5 % dauerhaft erhaltbar) |
| **5 Jahre (Wissen)** | Link-Rot-Prüfung: 25 %–66,5 % der Links tot -> markieren, **nie löschen** |
| **10 Jahre** | Baum bleibt stabil, weil **Ordner Funktionen** sind und **Themen im Katalog** stehen |
| **Erben** | siehe Abschnitt 18 |

## 18 · Testament und Schlüsselübergabe (Freigabe 3a)

**Das Problem aus dem Red-Team:** Verschlüsselte Sicherung + „Secrets nur als Verweis" =
**der Erbe kann nichts öffnen.** Ein Testament ohne Schlüssel ist kein Testament.

**Verbindlich in `00_SYSTEM/`:**

| Element | Regel |
|---|---|
| `passphrase_ort` im Katalogkopf | **nur der Aufbewahrungsort** („verschlossener Umschlag bei X, Adresse Y") — **die Passphrase selbst steht NIE im Git** |
| `notfallkontakt` | Name + Beziehung + Erreichbarkeit | kein Secret, nur Kontakt |
| **verschlossener physischer Umschlag** | Passphrase + kurze Anleitung, bei einer **Vertrauensperson** | außerhalb jeder digitalen Kopie |
| `00_SYSTEM/UEBERNAHME.md` | **eine Seite:** Was ist das? Wo liegen die Daten? Wie entschlüsselt man? Was ist wertvoll? Was kann weg? | für einen Menschen ohne Vorwissen geschrieben |
| `owner` | **genau ein Eigentümer** — wie in v1.0, **aber** mit benanntem Notfallkontakt | |
| **Zweitkopie** | **zwei** Aufbewahrungsorte: Umschlag bei Vertrauensperson **UND** Bankschließfach (oder zweite Person) | ein Umschlag ist ein neuer Single Point of Failure |
| **Pflege-Kadenz** | **jährlich:** lebt die Person? Umzug? Umschlag auffindbar? | sonst veraltet der Ort still |
| **Trockenlauf** | **jährlich:** Vertrauensperson liest `ÜBERNAHME.md` und **erklärt zurück**, was zu tun ist | ein Testament, das niemand versteht, ist keines |
| **Grenze, nicht gelöst** | **gleichzeitiger Ausfall beider Orte** (Umzug, Tod, Streit) ist **nicht** abgedeckt; ein dritter Anker (Notar) ist **nicht** eingerichtet — **ehrlich benannt statt behauptet** | |

**Bewusst NICHT gelöst:** Es gibt **keine Stellvertretung im Betrieb** (eine Person bleibt eine
Person). Das ist kein Designfehler, sondern die Realität — deshalb das **schriftliche Übernahme-Blatt**.

## 19 · Was ausdrücklich NICHT gebaut wird (unverändert)

Auto-Umsortierung · globales Monorepo · Tags als Hauptablage · Backstage/Proxmox/TrueNAS/Docker/
Immich/Nextcloud/Unraid · **Mergify** (kommerziell, nur gleicher Eigentümer) · **repolinter**
(archiviert 02/2026) · **tfsec** (in Trivy aufgegangen) · SLSA für Wissen · **Nix/Devbox jetzt**
(pre-1.0) · **Voll-Automatik jeder Art** · **neue Policy-Engine nur für diesen Fix** ·
**neue KI-Schicht** · **neue Hauptkategorie**.

## 20 · Bewusst akzeptierte Restrisiken (ehrlich)

| Restrisiko | Warum akzeptiert |
|---|---|
| **Ein Secret kann kurzzeitig draußen sein** | Kein hartes Gate ohne Plattform — deshalb **Reaktionskette** statt Gate (Abschnitt 11) |
| **Hook umgehbar** (`--no-verify`) | Hook ist **weiches** Gate; das **Audit** ist der Rückhalt |
| **Prüfer kann hängen** | **überwacht** (26 h Herzschlag) -> CRITICAL „Status unbekannt", **nie OK** |
| **Forks behalten alte Secret-Werte** | technisch nicht behebbar -> **Rotation** als Antwort |
| **Toter Symlink / Pfad > 255** | gemeldet, **nicht** regelbar -> Hinweis, kein Verstoß |
| **18-Monats-Schwelle ist willkürlich** | Studien schwanken 1–36 Monate -> **Flag statt Löschung**, Schaden null |
| **Bit-Rot zwischen zwei Prüfläufen** | Prüfsummen **erkennen**, heilen nicht. **UNGEBUFFERT, solange P0 nicht existiert** (C3: der Ausgleich war als vorhanden behauptet, ist aber nicht gebaut) |
| **Keine empirischen Studien für N=1-Systeme** | nicht behebbar — ehrlich benannt |
| **Monorepo vs. Polyrepo nicht entschieden** | wissenschaftlich unbeantwortet -> Domänen-Bündel als Ausweg |

## 21 · Offene Punkte (unverändert offen)

Multi-Node ohne N=1-Studie · Monorepo/Polyrepo wissenschaftlich offen · Provenienz-Fälschung ohne
Anker · Lehman/Conway widersprüchlich · Abandonment-Schwelle willkürlich · Renovate-Repo-Grenze
unbelegt. **Keine davon blockiert den Prototyp.**

## 22 · Beleg-Anhang

**Wissenschaft:** Bergman (10.1002/asi.21415, 10.1002/asi.22906, 10.1145/1402256.1402259) ·
Whittaker (10.1145/1978942.1979457) · Lehman (10.1002/smr.564) · ESEM 2019
(10.1109/esem.2019.8870181) · Nagappan/Ball (10.1145/1368088.1368160) · Conway (10.1093/icc/dtw027) ·
Erosion (10.1109/ICSA53651.2022.00011) · Struktur-Commits (10.1007/s10664-026-10891-7) ·
Taxonomie-Algebra (arXiv cs/0312059) · Facetedpedia (10.1145/1772690.1772757) ·
Repos-Normierung (arXiv 2605.16701) · Deps (arXiv 1709.04621) · Reproduzierbarkeit
(arXiv 2601.02066) · Navigation (arXiv 2405.06271) · Auto-Ordnen (arXiv 2601.12369)
**Standards:** XDG · FHS · 12-Factor · BagIt RFC 8493 · NARA App. B · ISO 8601
**Praxis (geprüft 21.09.2026):** nixpkgs-vet (CI-erzwungen) · Backstage (JSON Schema + Ajv) ·
check-jsonschema 341★ (Push 2026-09-20) · OpenSSF Scorecard · OPA/Conftest · Renovate 22.550★ ·
multi-gitter 1.231★ · git-xargs 1.125★ · Ansible host_vars · ArgoCD ApplicationSets · restic 36.164★
**Tot/widerlegt:** repolinter (archiviert 02/2026) · tfsec (in Trivy) · Mergifyio/mergify
(Push 2023-09, nur Community-Tracker) · nixos-generators (archiviert) · altes cuelang/cue ·
Roo-Code (archiviert 05/2026) · Dendron · Rewind/Limitless (Shutdown 12/2025)

---

**ENDE v1.3**
**Nächster Schritt:** gezielter Re-Test (`RED_TEAM_v1.1.md`) — alle von v1.0 gerissenen Szenarien
+ Regression. Bewertung: PASS / PASS MIT EINSCHRÄNKUNG / FAIL / CRITICAL FAIL.
Danach Freeze-Entscheidung. **Dann STOP — kein Build ohne Freigabe.**


---

# ANHANG A · PROTOTYP-SCOPE (verbindlich)

**Zweck:** beweisen, dass **Katalog + Prüfer + Statuszeile** funktionieren — **isoliert**.
**Er ändert nichts am produktiven System.**

## A1 · Ort und Isolation
| | Festlegung |
|---|---|
| **MASTER-Wurzel** | **`~/prototyp_git_ordner/MASTER/`** — **nicht** im HAUPTLAGER, **nicht** in `~/.hermes/` |
| **Isolation** | **keine** Symlinks ins lebende System · **kein** Cron-Job · **kein** Zugriff auf `~`, HAUPTLAGER, `.hermes` |
| **Rücknahme** | `rm -rf ~/prototyp_git_ordner` — vollständig, ohne Rückstände |
| **Isolationsnachweis** | nach jedem Lauf: Änderungszeiten prüfen — **außerhalb** der Wurzel darf sich **nichts** geändert haben |

## A2 · Testordner
`~/prototyp_git_ordner/MASTER/` mit **~200 echten, harmlosen Dateien** und **5 eingebauten Verstößen** (A5).

## A3 · Regel-Scope
**Aktiv: K1, K2, K3, K4, K5, K6, K7** (7 von 8). **Nicht aktiv: K8** — der Prototyp enthält **keine**
externen Daten; K8 wird nur als **Schemafeld** vorbereitet.

## A4 · Katalog-Schema — vollständig
```yaml
schema_version: 1
name:      ^[a-z0-9_-]+$        # global eindeutig
pfad:      relativ, ohne ".."   # global eindeutig
class:     [system, agent, project, knowledge, data, infra, automation, template, archive]
bereich:   [00_SYSTEM, 10_AGENT, 20_PROJEKTE, 30_WISSEN, 40_DATEN, 50_INFRA,
            60_RUNTIME, 70_AUTOMATION, 80_VORLAGEN, 90_ARCHIV]
status:    [provisional, active, paused, done, abandoned, archived]
owner:     Pflicht (ein Wert)
seit:      YYYY-MM-DD
git:       true|false
extern:    true|false            # pin NUR wenn extern: true
pin:       ^[0-9a-f]{40}$|^v?[0-9.]+$
remote:    Pflicht wenn git: true UND status: active
review_am: Pflicht wenn status: active
```
**Dateikopf zusätzlich:** `notfallkontakt`, `passphrase_ort` (**nur der Ort, nie der Wert**).

## A5 · Selbsttest-Fixture — 5 bekannte Verstöße
| Nr | Verstoß | erwartet |
|---|---|---|
| 1 | Ordner ohne `README.md` (K3) | 1 Verstoß |
| 2 | Datei mit **12 MB** (K1) | 1 schwerer Verstoß |
| 3 | Datei mit `API_KEY=…` (K2) | 1 **CRITICAL** |
| 4 | Pfad mit **Tiefe 6** (K7) | 1 Hinweis |
| 5 | Katalogzeile auf **nicht existierenden** Pfad (K4) | 1 Verstoß (CRITICAL) |
**Findet der Prüfer nicht alle 5 -> er ist defekt -> CRITICAL „Prüfer defekt".**
Auf der **sauberen** Fixture: **0 Verstöße, 0 Fehlalarme**.

## A6 · Statuszeile — festes Format
```
PRÜFER: <OK|WARNING|ERROR|CRITICAL> · <n> Fehler · <n> Hinweise · <n> geprüft · REDUNDANZ: <vorhanden|FEHLT> · Selbsttest: <ok|DEFEKT> · Herzschlag <ISO-Zeit>
```
Beispiel: `PRÜFER: ERROR · 2 Fehler · 1 Hinweis · 214 geprüft · REDUNDANZ: FEHLT · Selbsttest: ok · Herzschlag 2026-09-21T19:30:04+02:00`
`REDUNDANZ` steht **in der Zeile** (Abschnitt 9 verlangt Sichtbarkeit). **Träger: Telegram**
(belegt vorhanden) + Konsole. **`FEHLT` ist im Prototyp der Normalfall** (nur eine NVMe vorhanden).

## A7 · Quittung und Herzschlag — Format
| Datei | Inhalt je Zeile |
|---|---|
| `60_RUNTIME/state/quittung` | `<ISO-Zeit> <status> <träger> <zugestellt ok|fehler>` |
| `60_RUNTIME/state/herzschlag` | `<ISO-Zeit>` (bei jedem Lauf überschrieben) |
**Wächter:** Herzschlag älter als **26 h** -> `PRÜFER AUSGEFALLEN — Status UNBEKANNT`.
Im Prototyp prüft **ein zweites Skript** den Herzschlag; der äußere Anker bleibt **manuell** (A9).

## A8 · Definition of Done
1. Schema validiert den Katalog (gültig **und** absichtlich ungültig getestet)
2. Prüfer findet **alle 5** Fixture-Verstöße und **0** Fehlalarme auf der sauberen Fixture
3. Statuszeile im festen Format, **zugestellt** (Quittung vorhanden)
4. `herzschlag` + `quittung` geschrieben; Wächter erkennt **simulierten** Ausfall
5. Selbsttest-Lauf grün und **im Bericht sichtbar**
6. **Isolationsnachweis** erbracht (A1)
7. `README.md` im Prototyp, von **einem Fremden** nachvollziehbar
8. Kein Schreibzugriff außerhalb `~/prototyp_git_ordner/` (Nachweis über Änderungszeiten)

## A9 · Der äußere Anker bleibt MANUELL
**Es gibt keinen automatischen Termin-Job** (im System nicht vorhanden, geprüft). Der Anker ist eine
**wöchentliche manuelle Pflicht**, im Prototyp zusätzlich als **Termin in `README.md`** notiert.
**Ehrlich:** ein Wächter über dem Wächter ist im Prototyp **nicht** automatisiert.

## A10 · K4-Scanraum
K4 prüft **ausschließlich** den Baum unter der Prototyp-Wurzel. **Kein** Scan von `~`, HAUPTLAGER
oder `.hermes`. *Ein Scan über den ganzen Bestand wäre teuer und lieferte Fremdbefunde.*

## A11 · Zeitschätzung (mit diesem Anhang)
| Umfang | Stunden |
|---|---|
| **Minimum** (K1–K7, Katalog, Prüfer, Fixture, Statuszeile, DoD 1–3, 6–8) | **25–35 h** |
| **Voll** (+ Quittung/Herzschlag/Wächter, Selbsttest im Bericht, Doku) | **35–60 h** |

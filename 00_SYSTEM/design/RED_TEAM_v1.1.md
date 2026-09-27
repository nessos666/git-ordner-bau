# RED_TEAM v1.1 — Re-Test gegen MASTER_DESIGN v1.1

**Ergebnis: NICHT BESTANDEN. Kein Freeze.**
Vollberichte: `daten/quellen/redteam/RETEST_1/2/3*.md` (16/24/22 KB)

| Gruppe | CRITICAL FAIL | FAIL | PASS mit Einschränkung | PASS |
|---|---|---|---|---|
| **R1** Skalierung/Verlust | **1** (S8) | 0 | 4 (S2,S9,F5,F7) | 3 (S3,F4,F6) |
| **R2** Automatik/Empfänger | **1** | 6 | 9 | 1 |
| **R3** Daten/Mensch/Zeit | **2** | 3 | 13 | 2 |

## Die CRITICAL FAILs
**C1 · S8 — Platte tot ohne zweite Kopie.** §9 unverändert: Stufe 4 ❌, **kein Ausweg**.
Von R1 als „billiges Item" bezeichnet: Stufe 4 + quartalsweiser Restore-Test trennen v1.1 von 0 CRITICAL FAIL.

**C2 · S32 — Modell ist falsche Klasse.** Ein **80-GB-eigenes Finetune** gilt als „Cache / nicht
sichern / jederzeit löschbar" → **Totalverlust ohne Recovery.** Der Punkt war in v1.0 als
Konstruktionsfehler markiert und wurde in v1.1 **nicht angefasst**.

**C3 · §20 kaschiert ein Totalverlust-Risiko.** Das „akzeptierte" Bit-Rot-Risiko beruft sich auf
**Redundanz (Stufe 4)** — die laut §9 **nicht gebaut** ist. Ein akzeptiertes Risiko ohne seinen
Anspruch ist **nicht gemildert, nur als akzeptiert getarnt**.

## 🔴 Der verifizierte Hammer (R2)
> **Der in §4 vorausgesetzte 07:00-Bericht EXISTIERT NICHT.**
> Die Dateien um 07:00 stammen aus **stündlichen** Jobs (`0 * * * *`) mit Status
> **„silent (empty output)"**; der einzige ausgelieferte Tagesbericht läuft **10:10** (KI-Radar).
> Der Job **`Integrity Watchdog (täglich 07:00, deliver: local)`** ist der **lebende Beweis**,
> dass genau dieses Muster hier schon ausfällt.
> **Telegram ist `connected` — im ganzen Dokument nicht genannt.**
> Keine Quittung, kein Lese-Zähler → **die ganze Kette (Audit → K2 → Rotation) hängt an einem
> Leseakt ohne Träger.**

## Die FAILs
| # | Befund | Quelle |
|---|---|---|
| F-a | **Tiefen-Ausweg:** „Projektinhalt zählt nicht" macht K7 in `20_PROJEKTE` **zahnlos**; der Regeltext widerspricht seinem eigenen Beispiel | R1 |
| F-b | **`nodes/`-Ausnahme ist namens- statt pfadbasiert** → **jeder** Ordner namens `nodes/` ist breitenfrei | R1 |
| F-c | **„extern muss Pin haben" wird nicht erzwungen** (nur „Eigene dürfen keinen") | R1 |
| F-d | **Topologie-Deckel:** 20+20²+20³ = **8.420**/Bereich; **10.000 Projekte > 8.000** → Dauer-Verstoß | R1 |
| F-e | **Herkunft nur auf Existenz geprüft** → Fälschung mit 0 Aufwand besteht; 3 billige Gegenproben fehlen | R2 |
| F-f | **Index ungehärtet:** keine Ausschlussliste, keine Sperre, kein Zeitlimit, kein Selbsttest | R2 |
| F-g | **`10_AGENT` ↔ `~/.hermes/` besitzlos** (`config.yaml.bak-20260825` belegt es) | R2 |
| F-h | **`schema_version` wurde ENTFERNT statt geklärt** → v1→v2 unmöglich | R2 |
| F-i | **Reaktionskette ohne Ausführer** — wer rotiert, wenn niemand hinschaut? | R2/R3 |
| F-j | **`provisional` kann Dauerzustand werden** (Bremse ist nur WARNING) | R2 |
| F-k | **Katalog-Eindeutigkeit fehlt:** `name`/`pfad` nicht global eindeutig | R3 |
| F-l | **Schlüsselübergabe = Papier:** ein Umschlag, keine Zweitkopie, keine Kadenz, kein Trockenlauf → **Single Point of Failure ersetzt durch neuen** | R3 |
| F-m | **Wächter-Kette endet unbewacht bei A1** (kein Loop, aber oberstes Glied offen) | R2 |
| F-n | **40_DATEN nur knapp:** 250 B/Zeiger = **818 KB** (78 %), 300 B = **981 KB** (94 %) des 1-MB-Budgets; Break-even ~3.500–5.200 Objekte | R3 |

## Was v1.1 wirklich geleistet hat
- **T1 arithmetisch geschlossen** (nachgerechnet: 3 ✓ / 3 ✓ / 4 ✗)
- **T3 sprachlich ehrlich** (Gate ≠ Audit ohne Hintertür)
- **F11/F12 definiert** (Bootstrap, Abandonment-Auslöser)
- **Szenario 22 strukturell verbessert**; **K4 schließt die bidirektionale Naht**
- **S3, F4, F6 = PASS**; **Rotation/S33 = PASS mit Einschränkung**
- **Case-Kollision live messbar** — R3 fand **46 reale Kollisionen** im Baum; prüfbar mit `casefold`+`uniq -d`

## Eigene Zahlen (R3, gemessen)
**3.849 Dateien > 10 MB** gesamt · **3.271** ohne Abhängigkeiten/Interna (≈ **228 GB**) im realen HAUPTLAGER.

## Antwort auf die Schlussfrage (R3, wörtlich)
> *„Als **Ordnungsstruktur JA** (8 statt 15 Regeln, ehrliche Gate/Audit-Trennung, „Katalog gewinnt"
> entfernt). Als **Betriebssystem NEIN** — die Ausgleiche für die größten Risiken (zweiter Ort,
> Restore-Test, externer Empfänger, geprüfte Übergabe) sind weiter **nicht gebaut**."*

**v1.0 wurde nicht eingefroren. v1.1 wird ebenfalls nicht eingefroren.**

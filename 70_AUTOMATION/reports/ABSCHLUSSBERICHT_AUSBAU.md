# ABSCHLUSSBERICHT — Ausbau des Git-Ordner-Baums (Schritte 1 bis 5)

**Datum:** 2026-09-24 · **Baum:** `~/HAUPTLAGER/03_PROJEKTE/55_Git_Ordner_Prototyp/MASTER`
**Tag:** `v0.2.22-prototyp` · **Suiten:** 0 mit Fehlern · **Einzeltests:** 224 · **Commits:** 40

---

## 1. Was jetzt da ist — in einem Absatz

Ein **Ordner, der sich selbst prueft**. Du legst Dinge nach festen Regeln ab; ein Programm liest sie
und sagt dir in **einer Zeile**, ob alles stimmt: Zahlen, Fehler, Hinweise — und ob die zweite Kopie
noch aktuell ist. Deine echten Projekte liegen **ausserhalb** und haengen nur als **Zeiger** dran:
der Baum bleibt winzig (~500 KB), deine Daten bleiben unangetastet, und du findest sie trotzdem.

## 2. Die neun Befehle (und wann du welchen nimmst)

| Befehl | Wofuer | Beispiel |
|---|---|---|
| `./ordner.sh status` | Kurzer Zustand: Index frisch? Quellen vollstaendig? | taeglicher Blick |
| `./ordner.sh pruefen` | **Vollpruefung** — der wichtigste Befehl | „haelt der Baum noch?" |
| `./ordner.sh suchen "begriff"` | Suche im Baum (Inhalt + Namen) | Notiz wiederfinden |
| `./ordner.sh finden "begriff"` | Suche **im Inhalt der angebundenen Projekte** (Text, PDF, DOCX) | „wo steht das?" |
| `./ordner.sh dateien "muster"` | **Dateinamen** suchen — Baum **und** angebundene Projekte | Datei wiederfinden |
| `./ordner.sh springen "muster"` | Zu einem Projekt/Ordner springen (Pfeiltasten) | schnell hin |
| `./ordner.sh projekt "name"` | Neues Projekt mit **fester Nummer** | neues Vorhaben |
| `./ordner.sh zeiger /Pfad` | Bestand ausserhalb **read-only** anbinden | neues Projekt anschliessen |
| `./ordner.sh neu` | Suchindex neu bauen (nur eine Projektion) | nach groesseren Aenderungen |

## 3. Die fuenf Schritte — Ziel und gemessenes Ergebnis

| # | Ziel | Messung (belegt) | Status |
|---|---|---|---|
| 1 | Baum bleibt ueber Jahre schnell | Repo **1,7 MB -> 544 KB**, lose Objekte 140 -> 0, `git fsck` sauber | fertig |
| 2 | **Redundanz messen** statt behaupten | Statuszeile: vorher `REDUNDANZ: FEHLT` -> jetzt `1 Kopie(n), aktuell — GLEICHE PLATTE (…)`; live bewiesen: Kopie nicht erneuert -> `VERALTET` | fertig |
| 3 | **Feste Nummern** (Umbenennen bricht nichts) | `001_name_JJJJ-MM-TT`; zweites Projekt `002_…`; Doppelvergabe = **ERROR**; bestehende Ordner **nicht** umbenannt | fertig |
| 4 | Schnell finden und springen | **keine Installation noetig** (`fdfind`, `fzf` schon vorhanden); Rueckfall fdfind->rg->find; laeuft auch **ohne PyYAML** | fertig |
| 5 | Inhalte der Aussenprojekte durchsuchbar | Text **+ PDF/DOCX** (pdftotext/libreoffice); echte Probe: 16 PDFs im Island-Dossier, Treffer **im PDF-Text**; **1,5 s -> 0,1 s** beim zweiten Lauf | fertig |

## 4. Was ehrlich NICHT geht (offene Grenzen — nicht schoengeredet)

1. **P0 — zweite Kopie liegt auf DERSELBEN Platte.** Sie schuetzt vor Fehlern (versehentlich
   geloescht/ueberschrieben — einmal bewiesen: Baum war zerstoert und kam vollstaendig zurueck),
   **nicht** vor Plattenausfall, Diebstahl oder Verschluesselungstrojaner. Das steht in **jeder**
   Pruefzeile. Der Ort auf einem zweiten Geraet ist **deine** Entscheidung — keine Kaufempfehlung.
2. **Rollen-Trennung: NICHT VERIFIZIERT.** Wer darf schreiben, wer nur lesen — im Prototyp nicht geprueft.
3. **Angriffs-/Wettlauf-Klasse ist DOCUMENTED LIMIT, nicht geschlossen:** Hardlink 0/100,
   `RENAME_EXCHANGE` 64/200, Pruefer-B-Angriff 20/20. Deshalb ist die Aussage
   „Boundary sicher" **nicht** erlaubt — nur „in diesen Faellen gemessen".
4. **Ein bewusster Hinweis** im Prueflauf: der 94-MB-Zeiger (Island-Dossier) liegt ueber der
   50-MB-Grenze und wird als **Aggregat** geprueft (Pruefsumme ueber alles), nicht Datei fuer Datei.
   Er ist sichtbar gemeldet, nicht verschwiegen.
5. **Recoll ist nicht installiert** — und wird nicht gebraucht (PDF/DOCX laufen ohne).
   Die Installation braucht ein Administrator-Passwort (nur du). Anleitung: `50_INFRA/RECOLL_ANLEITUNG.md`.
6. **Kosmetik:** vier alte Suiten legen Scratch-Ordner **neben** dem Baum an und raeumen nicht auf
   (`tmp_25`, `tmp_gegen`, `tmp_tests`, `tmp_unabh`). Der Baum selbst bleibt sauber (0 Fehler).

## 5. Wartung, die auf Jahre reicht

| Wann | Was | Befehl |
|---|---|---|
| monatlich | aufraeumen/beschleunigen | `git commit-graph write --reachable && git gc` |
| nach Aenderungen | zweite Kopie erneuern | `./sicherung.sh kopie ~/sicherung_git_ordner` |
| bei Zweifel | pruefen | `./ordner.sh pruefen` |
| neues Projekt | anlegen | `./ordner.sh projekt "name"` |

**Kein Cron, kein Dienst, keine Voll-Automatik** — alles auf Zuruf, wie von dir verlangt.

## 6. Selbst nachpruefen (in zwei Minuten)

```bash
cd ~/HAUPTLAGER/03_PROJEKTE/55_Git_Ordner_Prototyp/MASTER
bash 70_AUTOMATION/tests/alle_suiten.sh     # erwartet: "14 Suiten, 0 mit Fehlern"
./ordner.sh pruefen                          # erwartet: 0 Fehler, REDUNDANZ: aktuell — GLEICHE PLATTE
sha256sum -c PRUEFSUMMEN_MASTER.txt --quiet  # erwartet: keine Ausgabe (alles identisch)
```

## 7. Was als Naechstes moeglich waere (nichts davon laeuft von selbst)

1. **Vier alte Suiten aufraeumen lassen** (Scratch-Ordner) — klein, kosmetisch.
2. **P0-Ort waehlen** (USB-Stick / zweiter Rechner / Ort im Netz) — danach trage ich ihn in
   `50_INFRA/redundanz.yaml` ein, und die Pruefzeile sagt dann `auf ANDEREM Geraet (echte Redundanz)`.
3. **Etappe 3** (Einzug in den echten HAUPTLAGER) — bisher im Plan **verboten**, braucht deine Freigabe.
4. **Recoll** — nur wenn du einen Dauerindex ueber sehr grosse Bestaende willst.

## 8. Nutzen (aus der Recherche, mit Quellen)

Der Ansatz ist **nicht exotisch**: DataLad (Forschung, Uni Bonn), git-annex, GitHub-Integrity-Manifeste,
Gatehouse (Regelwerk + Pruefsummen) und Johnny.Decimal (feste Nummern) bauen dasselbe groesser.
Unser Eigenes ist die **Kombination**: klein, ohne Zusatz-Abhaengigkeiten, **Teil-Automatik**,
deutsche Doku — und **er misst sich selbst**. Details: `50_INFRA/RECHERCHE_AEHNLICHE_PROJEKTE.md`.

---

**Nachtrag 27.09.2026 (Fremdpruefung):** Die Zahl „14 Suiten" in diesem Bericht beschreibt den Stand
SEINER Zeit. Heute gemessen: 20 Suiten, 265 Testfunktionen, 16 Befehle.
Historische Zahlen werden nicht ueberschrieben — aber wer den Bericht heute liest, soll die
Differenz sehen. Nachprueffbar mit: `./ordner.sh --hilfe` und `bash 70_AUTOMATION/tests/alle_suiten.sh`.

# Protokoll für David — 23.09.2026

**Was heute am Git-Ordner-Baum passiert ist. Kurz, in normaler Sprache.**

---

## 1. Was der Baum ist (in einem Satz)

Ein **Ort für alles**, der sich selbst überwacht: Er hat feste Regeln, einen Katalog,
Prüfsummen und einen Prüfer. Der Prüfer liest die Festplatte und sagt mir, wenn etwas
nicht stimmt — zum Beispiel wenn Dateien fehlen, etwas zu tief liegt oder ein Geheimnis
im Git liegt.

**Zwei Befehle sind die wichtigsten:**

| Befehl | Was er tut | Wann benutzen |
|---|---|---|
| `./ordner.sh pruefen` | Prüft den ganzen Baum und meldet Fehler/Hinweise | Wenn du wissen willst: „ist alles in Ordnung?" |
| `./ordner.sh zeiger /Pfad` | Nimmt einen **echten** Ordner von außen auf, ohne ihn anzufassen | Wenn ein Projekt **im Baum sichtbar** sein soll, aber dort bleiben soll, wo es ist |

Dazu: `status` (Kurzzustand) · `suchen "begriff"` (im Baum suchen) · `neu` (Suchindex neu bauen).

---

## 2. Was heute gebaut und repariert wurde

### A) Zeiger werden endlich richtig geprüft
Ein „Zeiger" ist ein kleiner Zettel im Baum, der auf einen Ordner **außerhalb** zeigt.
Vorher stand auf so einem Zettel nur die Adresse — **ob die Dateien dort wirklich noch so
sind, hat niemand geprüft.** Ein Zettel, der ins Leere zeigte, galt als „in Ordnung".

Jetzt wird geprüft: **Gibt es das Ziel? Stimmt die Größe? Stimmt die Prüfsumme? Stimmt die
Dateizahl?** Getestet mit Absicht: Zettel ins Leere → **wird erkannt**. Falsche Prüfsumme →
**wird erkannt**. Über 50 MB wird nur die Sammel-Prüfsumme geprüft — und das steht dann
ehrlich in der Meldung.

### B) Projekte mit eigenen Unter-Repos
Ein echtes Projekt brachte 7 eigene Git-Repos mit → **107 Fehler**, unbrauchbar.
Jetzt: die werden **gezählt und gemeldet**, nicht verlangt. Aus 107 Fehlern wurde ein Hinweis.

### C) Drei Fehler, die der große Testlauf (10 echte Projekte) gefunden hat
1. **„Datei" war nicht eindeutig** — die Liste zählte Symlinks anders als der Prüfer →
   Fehlalarm „13064 statt 13067". Jetzt: **eine** Definition für beide.
2. **Prüflisten waren im falschen Ordner** — sie machten `40_DATEN` 5,57 MB groß, erlaubt
   ist unter 1 MB. Jetzt liegen sie in `60_RUNTIME` (nicht in Git, jederzeit neu erzeugbar).
3. **Ein Symlink ließ die Prüfung abstürzen** (CRITICAL). Jetzt wird bei einem Symlink
   bewusst das Ziel gelesen — nur lesen, nie schreiben.

### D) K7: echte Projekte passen nicht unverändert in den Baum
Gemessen: ein echtes Projekt hat **Tiefe 7** (erlaubt 5) und **Breite 23** (erlaubt 20) →
über 100 Fehler. Umbauen wäre „etwas anfassen" und ist verboten.
**Jetzt:** entweder als **Zeiger** anbinden (empfohlen), oder man schreibt ausdrücklich in
den Katalog `inhalt_ausgenommen: true` — dann gibt es **eine** Meldung statt hunderter Fehler.
Ohne diesen Eintrag ändert sich nichts.

---

## 3. Aufgeräumt

- **Altordner `~/prototyp_git_ordner` gelöscht** (170 MB, 25.683 Dateien — nur alte Testkopien).
  Vorher geprüft: kein Programm liest ihn, kein Baum mehr drin. Gerettet: Messergebnisse (32 kB)
  + altes Git-Bündel (279 kB) → beide jetzt **im Git**.
- **Alles Wichtige ist jetzt in Git:** Der Baum hat **78 verfolgte Dateien, 0 unbemerkte**.
  Befunde lagen vorher nur in Testordnern → jetzt in `90_ARCHIV/befunde/`.
- **Zweite Kopie erneuert:** 101 Dateien, Prüfsummen geprüft.
- **Meine eigene Regel hat meinen Fehler gefunden:** ich hatte eine 12,6-MB-Datei in den Baum
  gelegt → K1-Meldung: „Datenobjekt über 10 MB — Git ist kein Massenspeicher." Korrigiert.

---

## 4. Alltagstest: ein echtes Projekt aufnehmen

Beispiel `47_Island_Sprache` (dein Island-Dossier):

```
./ordner.sh zeiger ~/HAUPTLAGER/03_PROJEKTE/47_Island_Sprache
→ Dateien: 312 · Größe: 94,3 MB · Prüfsumme berechnet · 0,2 Sekunden
→ angelegt: 40_DATEN/pointers/47_Island_Sprache.yaml  +  Prüfliste in 60_RUNTIME
```

Danach meldet `./ordner.sh pruefen`: **0 Fehler**, dazu ein **Hinweis**:
„OBERGRENZE 50 MB: Aggregat geprüft, 312 Dateien NICHT einzeln geprüft" — ehrlich statt still.

**Wichtig zu wissen:** Das Projekt selbst bleibt, wo es ist. Man kann es nur **finden**,
nicht im Baum durchsuchen — der Baum kennt den Zettel, den Inhalt nicht. Das ist Absicht
(sonst müssten die Daten in Git, und Git ist kein Massenspeicher).

---

## 5. Was der Baum heute kann — und was nicht

**Kann:**
- 10 Suiten mit allen Tests laufen lassen: `bash 70_AUTOMATION/tests/alle_suiten.sh` → **10/10 grün**
- Prüfen: Katalog, Regeln, Secrets, Symlinks, Zeiger, Tiefe/Breite, Prüfsummen
- Aufnehmen: echte Ordner per Zeiger (ohne sie anzufassen)
- Sichern: `./sicherung.sh kopie <Ziel>` + Wiederherstellen
- Zustand messbar: 0 Fehler · 312 geprüft · Selbsttest ok

**Kann nicht (ehrlich):**
- **P0 halb:** die zweite Kopie liegt auf **derselben** Platte. Stirbt die Platte, sind beide weg.
  Ein Ort außerhalb (USB-Platte, zweiter Rechner) fehlt noch — **du entscheidest**, was passt.
- Echte Projekte werden **nicht** kopiert (Tiefe/Breite) — nur per Zeiger angebunden.
- Der Index ist nur eine **Projektion** — nie die Wahrheit. Wahrheit sind Git + Katalog + Dateien.
- Die Tiefe/Breiten-Regeln sind für den Baum gebaut, nicht für gewachsene Altprojekte.

---

## 6. Wo alles liegt

| Was | Wo |
|---|---|
| Der Baum | `~/HAUPTLAGER/03_PROJEKTE/55_Git_Ordner_Prototyp/MASTER` |
| Bedienung (für dich) | `MASTER/ANLEITUNG.md` |
| Dieser Bericht | `MASTER/PROTOKOLL.md` |
| Zweite Kopie | `~/sicherung_git_ordner` (101 Dateien, geprüft) |
| Testinstanz (10 echte Projekte) | `.../55_Git_Ordner_Prototyp/_TESTLAUF_C` |
| Design-Dokumente | `~/HAUPTLAGER/03_PROJEKTE/54_Selbstorganisierender_Git_Ordner` |
| Stand | 30 Commits · Git sauber · **die aktuellen Zahlen zeigt immer `./ordner.sh pruefen`** (Stand dieses Blattes: Tag `v0.2.15-prototyp`) |

## Nachtrag 25.09.2026 — Zahlkorrekturen (unabhaengige Fremd-Pruefung)

Frueher genannte Zahlen waren Momentaufnahmen aus der Bauzeit und stimmen heute nicht mehr.
Die Historie bleibt stehen; hier die **heute gemessenen** Werte:

| damals genannt | heute gemessen |
|---|---|
| "10/10 gruen" | **19 Suiten, 0 mit Fehlern** |
| "78 verfolgte Dateien" | **113 verfolgte Dateien** |
| "312 geprueft" | **382 geprueft** |
| "achtzehn Befehle" in alten Fassungen | **15 Befehle** |

---

**Nachtrag 27.09.2026 (Fremdpruefung):** „15 Befehle" beschreibt den Stand SEINER Zeit. Heute
gemessen: 16 Befehle (status, pruefen, suchen, neu, zeiger, projekt, finden, dateien, springen,
doppelt, bag, crate, vorlage, spross, summen, formate), 20 Suiten, 265 Testfunktionen.

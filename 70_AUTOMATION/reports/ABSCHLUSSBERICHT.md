# Abschlussbericht — Git-Ordner 2.0, Weg 1

**Stand:** 23.09.2026 · Tag `v0.2.8-prototyp` · Ort: `~/HAUPTLAGER/03_PROJEKTE/55_Git_Ordner_Prototyp/MASTER`
**Vorgeschichte:** Basis `eae641a` + Reparaturen 2.8 (F1–F9). Alle 11 Schritte des `70_AUTOMATION/reports/BAUPLAN_WEG1.md` erledigt.

## Was fertig und gemessen ist

| Schritt | Ergebnis | Beleg |
|---|---|---|
| Verbindungsfehler | EINE Fehlerklasse, EINE Exitcode-Tabelle | 8/8 Suiten |
| F1 unlesbare Pflichtdatei | nie „OK" — sichtbare Meldung + Exit ≠ 0, kein Traceback | 7 Varianten |
| F8 Statusdatei | vollständig (status/exit/geprueft), deckungsgleich mit dem Lauf | 3 Fälle |
| F5 Obergrenze | 5000 wird **gemeldet**, nicht still abgeschnitten | 6002 Dateien |
| F2 Sonderdatei | FIFO/Socket als Index → kein Hänger, klare Meldung | Schärfekontrolle |
| F3 Dateinamen | Nicht-UTF8/Umbruch/Tab/Steuerzeichen → sauber escaped | 5 Namensarten |
| F4 `--json` | nur JSON, auslesbar | 4 Befehle |
| F7 Regressionstests | `test_suite_etappe28.py`, 8 Tests (F1–F6 + Lösch-Schranke) | 196 Tests gesamt (Stand WEG-1-Abschluss; heute 209) |
| Bedienung | `ordner.sh` (5 Befehle) + `ANLEITUNG.md` | alle Befehle ausgeführt |
| Zweite Kopie | `sicherung.sh`: kopieren, prüfen, wiederherstellen | Restore getestet |
| Freeze | `PRUEFSUMMEN_MASTER.txt` + Tag | `sha256sum -c` → alle identisch |
| Umzug | Prototyp → HAUPTLAGER, Sandbox zieht mit (ortsunabhängig) | 8/8 Suiten am neuen Ort |

## Vorfall 23.09.2026 (beim Umzug) — ehrlich dokumentiert
Ein fehlerhafter Ersatztext (Kommentar am Zeilenende) hat in einer Testdatei die Variable `B` auf die
**Sandbox selbst** zeigen lassen. Die Aufräumfunktion der Suite löschte daraufhin den kompletten Baum
(inkl. Laufzeit-Zustand). **Wiederherstellung:** Git-Bündel (`repo.bundle`, Schritt 8) + zweite Kopie
(`sicherung/baum`, Schritt 9) + Artefakt aus den Prüfer-Kopien (byte-identisch, md5 `144129f9`).
**Ergebnis:** Baum vollständig, 8/8 Suiten grün.
**Eingebaute Schutzmaßnahmen:** (1) `nur_scratch()` in `rules.py`, (2) Lösch-Schranke in der Suite,
(3) zwei Dauer-Tests, die beweisen, dass die Schranke Sandbox/Baum verweigert und Testwiesen erlaubt.
**Lehren:** (a) nie Kommentare an ersetzte Codezeilen hängen — erst kompilieren, dann messen;
(b) Testwiesen NIE aus einer einzigen Variable ableiten; (c) Umzug in tiefere Pfade kann
AF_UNIX-Socket-Pfade (≈107 Zeichen) sprengen — Testwiesen dann kürzen.

## Dokumentierte Grenzen (kein Sicherheitsversprechen)
1. Zweite Kopie liegt auf **derselben Platte** — echtes P0 braucht ein zweites Medium (Kaufentscheidung).
2. `ROLLENTRENNUNG: NICHT VERIFIZIERT` (Etappe 3).
3. Angriffs-/Race-Klasse (Parent-Swap) ist bewusst **nicht** Teil dieses Projekts: drei Mechanismen
   gemessen (dirfd, Landlock, tmpfs-Pin), keiner erreichte 0.

## Selbst nachprüfen
```bash
cd ~/HAUPTLAGER/03_PROJEKTE/55_Git_Ordner_Prototyp/MASTER
./ordner.sh status && ./ordner.sh pruefen      # erwartet: OK · 0 Fehler
sha256sum -c PRUEFSUMMEN_MASTER.txt            # alle Zeilen OK = unverändert
./sicherung.sh kopie ~/sicherung_git_ordner    # zweite Kopie + Prüfsummen + Bündel
```

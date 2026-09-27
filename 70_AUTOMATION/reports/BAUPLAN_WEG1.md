# BAUPLAN — Weg 1: Git-Ordner 2.0 fertigstellen

**Ziel in einem Satz:** Ein Ordnerbaum für Davids Festplatte, der sortiert, prüft, wiederfindet,
nichts überschreibt, zweimal ausführbar dasselbe Ergebnis liefert, und bei dem man per Befehl
nachweisen kann, dass er in Ordnung ist.

**Fertig, wenn:** 188+ Tests grün · MASTER-Prüfer 0 Fehler · zweite Kopie + Wiederherstellung
getestet · Tag gesetzt · eine Seite Anleitung vorhanden.

## NICHT im Umfang (Drift-Sperre)
1. Angriffs-/Race-Labor (rename_exchange, Landlock, Mount-Namespace, TOCTOU) — bleibt dokumentierte Grenze, **kein** weiterer Aufwand.
2. Keine neue Architektur, keine neue Datenbank, kein neues Werkzeug, keine neue Ebene.
3. Keine Etappe 3, kein Cron, kein Telegram, kein produktives System anfassen.
4. Keine Prüfer-Runden und keine Delegationen ohne ausdrueckliche Freigabe von David.
5. Kein Paket installieren, kein sudo/root.

## Schritte (jeder endet mit: Suite grün + Commit + EINE sichtbare Zahl)

| # | Schritt | Beweis (Zahl/Test) |
|---|---------|--------------------|
| 1 | F1: unlesbare Pflichtdatei darf NIE "alles OK" ergeben | Selbsttest: unlesbar -> Status UNREADABLE/PARTIAL, Exit != 0 |
| 2 | F8: kein "Status OK" + "KRITISCH" im selben Lauf | Selbsttest: Widerspruch -> Status CRITICAL |
| 3 | F5: Abschneiden ab 5000 Dateien sichtbar melden (und Grenze einstellbar) | Selbsttest: 6000 Dateien -> Meldung "gekuerzt", nicht still |
| 4 | F2: Sonderdatei (FIFO) als Indexdatei -> sauberer Fehler statt Haenger | Selbsttest mit Timeout < 20 s |
| 5 | F3: ungewoehnliche Dateinamen -> keine kaputten Bytes, keine Ausnahme | Selbsttest: 0xff-Datei -> Status CRITICAL, Exit 2 |
| 6 | F4: --json liefert NUR JSON (auslesbar) | Selbsttest: json.loads(stdout) fehlerfrei |
| 7 | F9: dauerhafte Selbsttests fuer F1-F6 in die Suite (Regression) | 6 neue Tests, Suite gesamt > 194 |
| 8 | Anleitung (1 Seite, deutsch) + Startskript ordner.sh mit 4 Befehlen | Startskript laeuft: status / pruefen / suchen / neu |
| 9 | Zweite Kopie + Wiederherstellungs-Test (P0) | Restore-Test: Datei geloescht -> aus Kopie zurueck, Pruefsumme gleich |
| 10 | Freeze: Tag + Pruefsummenliste + Anleitung "so pruefst du Unveraendertheit" | Tag gesetzt, Pruefsummen 54 Dateien dokumentiert |
| 11 | Abschluss: Gesamtlauf 2x + MASTER 2x + Abschlussbericht 1 Seite | zwei Laeufe zeichengleich |

## Drift-Waechter (vor JEDEM Schritt ausfuellen)
1. Behebt der Schritt eine der 7 gemeldeten Stoerungen, oder ist er in der Tabelle oben? **Nein -> STOP.**
2. Bringt er ein neues Konzept/Werkzeug/Dateiformat mit? **Ja -> STOP, eine Frage an David.**
3. Kann ich ihn mit einer Zahl belegen? **Nein -> STOP.**
4. Wird etwas ausserhalb von ~/HAUPTLAGER/03_PROJEKTE/55_Git_Ordner_Prototyp/ veraendert? (damals: ~/prototyp_git_ordner) **Ja -> STOP.**
5. Am Ende: Suite gruen? Commit? Fortschrittsliste aktualisiert? **Sonst nicht "fertig" nennen.**

## Offene Entscheidungen (nur wenn Schritt 9 dran ist)
- Wohin die zweite Kopie soll (andere Platte/Ordner) — David entscheidet.
- Ob der fertige Baum aus dem Prototyp-Ordner in den HAUPTLAGER umziehen soll — David entscheidet.


## Lehren 23.09.2026 (nach dem Umzug, aus einem echten Schaden)
1. **Nie einen Kommentar an eine ersetzte Codezeile hängen.** Ein Textersatz, der `B = "<pfad>" / "x"`
   in `B = <formel>  # Kommentar / "x"` verwandelt, kommentiert den Rest der Zeile weg. Danach:
   kompilieren UND die kritischen Zeilen ausgeben — vor jeder Messung.
2. **Eine Testwiese darf nie aus einer einzigen Variable abgeleitet werden.** Vor jedem Löschen prüfen:
   liegt der Pfad *unter* der Wiese, und ist die Wiese selbst nicht die Sandbox/der Baum?
3. **Umziehen heißt Pfade prüfen.** Tiefere Pfade können AF_UNIX-Sockets (≈107 Zeichen) sprengen —
   Testwiesen dann kürzen (z. B. `<sandbox>/t26`).
4. **Erst messen, ob ein Werkzeug noch tut — dann weiterschreiben.** Nach jedem Umzug: 8/8 Suiten.

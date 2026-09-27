# validation — der Prüfer  ·  PROTOTYPE

```
python3 check_all.py                   # prüft die MASTER-Wurzel (Standard)
python3 check_all.py --json            # maschinenlesbar
python3 check_all.py --no-selftest     # nur ohne Selbstbeweis (nicht empfohlen)
```

**Exitcodes:** `0` OK · `1` WARNING · `2` ERROR · `3` CRITICAL

**Statuszeile** (menschen- und maschinenlesbar, Format aus Anhang A6):
`PRUEFER: <LEVEL> · n Fehler · n Hinweise · n geprüft · REDUNDANZ: vorhanden|FEHLT · Selbsttest: ok|DEFEKT · Herzschlag <ISO>`

**Der Prüfer darf:** lesen · melden · Quittung + Herzschlag in `60_RUNTIME/state/` schreiben.
**Der Prüfer darf NIEMALS:** löschen · verschieben · umbenennen · reparieren · committen · pushen ·
Secrets rotieren. Bei Abweichung: **melden**. Das ist mit einem Test abgesichert
(`tests/weg1/test_suite.py` sucht im Quelltext nach verbotenen Aufrufen).

**Selbsttest:** läuft gegen `fixtures/clean` (muss 0 Befunde ergeben) und `fixtures/broken`
(muss die bekannten Verstöße K1, K2, K3, K4, K5, K7 finden). Ein leeres Ergebnis gilt **nicht**
als Beweis für einen funktionierenden Prüfer.

# Urteil: drei Metadaten-Schichten, ein Rechenweg fuer Pruefsummen

Stand 26.09.2026, v0.2.62-prototyp. Anlass: die Fremdpruefungen nannten "drei ueberlappende
Metadaten-Schichten (BagIt + RO-Crate + Katalog)" als verzichtbar. Hier die Messung statt
Meinung.

## Was jede Schicht beantwortet

| Schicht | Umfang | Felder je Eintrag | Frage |
|---|---|---|---|
| Selbstbeschreibung (RO-Crate) `ro-crate-metadata.json` | 115 Datei-Eintraege | sha256, contentSize, dateModified, name | Was ist im Baum, wie gross, welcher Inhalt, wann geaendert |
| Pruefsummenliste `PRUEFSUMMEN_MASTER.txt` | 116 Zeilen | sha256 + Pfad | Nachweis mit Standardwerkzeugen (sha256sum -c) |
| Katalog (K5) `00_SYSTEM/manifest/repos.yaml` | 11 Eintraege | name, class, status, owner, seit, bereich, pfad, git, remote, pin, extern, review_am | Welche Repositories gibt es, in welchem Zustand, wem gehoeren sie |

Gemessene Ueberschneidung zwischen Katalog und Selbstbeschreibung bei Pruefsummen: KEINE
(der Katalog enthaelt keine Pruefsummen-Felder).

## Entscheidung

1. Die Pruefsummenliste bleibt, ist aber ABGELEITET aus der Selbstbeschreibung
   (`70_AUTOMATION/crate/liste_aus_crate.py`). Vorher rechneten zwei Codewege dieselben Zahlen:
   114 von 114 waren identisch, der einzige Unterschied war die Selbstbeschreibung selbst, die
   sich nicht selbst enthalten kann. Eine Wahrheit, ein Rechenweg, nachgewiesen gleiches
   Ergebnis. Die Liste bleibt, weil sie mit `sha256sum -c` ohne eigenen Code pruefbar ist.

2. Der Katalog bleibt unveraendert. Er beantwortet eine andere Frage (Repos, Status, Besitz)
   und traegt keine Inhaltsangaben — keine Doppelung, also nichts zu entfernen.

3. Der BagIt-Bag (in der Sicherung, AUSSERHALB des Baums) rechnet seine Pruefsummen bewusst
   SELBST (`bagit_bauen.py`, `sicherung.sh`). Das ist kein Rest der Doppelung: BagIt ist die
   genormte Verpackung fuer Weitergabe und Wiederherstellung, und "valid" bedeutet dort, dass
   jede Pruefsumme im Manifest nachgerechnet wurde. Waere das Manifest aus der
   Selbstbeschreibung abgeleitet, koennte eine beschaedigte Kopie einen in sich stimmigen Bag
   erzeugen — beide falsch, auf dieselbe Weise. Getrennt gerechnet ist es eine unabhaengige
   Kontrolle, und genau das soll eine Sicherung sein.

## Was daraus folgt

Zwei Schichten im Baum bleiben (Selbstbeschreibung als Wahrheit, Liste als abgeleiteter
Nachweis), der Katalog bleibt aus anderem Grund, und die getrennte Rechnung liegt nur noch
DORT, wo sie Unabhaengigkeit erzeugt: in der Sicherung. Im Baum gibt es keine zwei Rechenwege
fuer dieselben Pruefsummen mehr.

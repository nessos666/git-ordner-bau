# Wer baut Aehnliches — und ist das hier nutzbar? (Recherche 2026-09-24)

## Kurzantwort

**Ja, der Ansatz ist nutzbar — und er ist nicht exotisch.** Es gibt grosse, anerkannte
Verwandte, vor allem in der Forschung. Unser Baum ist die kleine, abhaengigkeitsfreie
Ausgabe derselben Grundidee — mit einer Zutat, die es dort nicht gibt: er **prueft sich selbst
und nennt Zahlen**.

## Was es schon gibt (Quellen in der Fusszeile)

| # | System | Was es macht | Bezug zu unserem Baum |
|---|---|---|---|
| 1 | **DataLad** (Forschung) | verwaltet Code + Daten jeder Groesse auf Git, **verschachtelte Datensaetze**, Lehre u.a. Uni Bonn | = unser Meta-Repo + Unterrepos/Zeiger, nur groesser und fuer Forschergruppen |
| 2 | **git-annex** (Grundlage von DataLad) | grosse Dateien ohne Git-Blob | unsere 10-MB-Regel (K1) ist die kleine Schwester davon |
| 3 | **Repo Integrity Manifest Action** (GitHub) | "kryptografisch pruefbare Momentaufnahmen von Struktur und Inhalt eines Repos — Governance, Compliance, Security" | = unsere Pruefsummenliste + Freeze/Tag |
| 4 | **Gatehouse** (Go-CLI) | "validiert ein versioniertes Regelwerk, Dateipruefsummen und Grenzen" | = unser Regelwerk K1–K8 + Pruefer |
| 5 | **Policy-as-Code / Checksum-Policy** (JFrog, Sonatype) | dieselbe Idee in der Industrie | bestaetigt: Regeln + Pruefsummen + Grenzen sind Standard |
| 6 | **Johnny.Decimal** | "der Ort folgt einer **festen Landkarte**, die man einmal entwirft — damit sich nichts bewegt" | = unsere festen Projekt-Nummern |
| 7 | **PARA** (Vergleich) | "der Ort folgt dem **Status** und wandert mit dem Leben" | = genau die Unstetigkeit, die David nicht will |

## Was daran wirklich unser eigenes ist

1. **Die Kombination** in einem kleinen Baum ohne Zusatz-Abhaengigkeiten: Regelwerk + Pruefer +
   feste Nummern-Ordnung + **gemessene** Redundanz + verstaendliche deutsche Doku.
2. **Teil-Automatik statt Voll-Automatik** — nichts laeuft unbeaufsichtigt (kein Cron, kein Dienst).
3. **Das Messen selbst**: jede Pruefzeile nennt Zahlen und Grenzen. P0 steht als
   `GLEICHE PLATTE (schuetzt vor Fehlern, NICHT vor Plattenausfall)` **sichtbar** in jeder Zeile —
   eine Behauptung waere billig, eine Messung nicht.
4. **Zeiger statt Kopie**: echte Projekte werden angebunden, nicht einverleibt (Beleg: `666_OSINT`
   109 Fehler -> 0 Fehler + 1 Hinweis; Baum bleibt bei ~500 KB).

## Was das ausdruecklich NICHT ist

- **Keine Erfindung.** Die Bausteine sind etabliert (siehe Tabelle). Wer das Gegenteil behauptet,
  sagt nicht die Wahrheit.
- **DataLad kann mehr** (Verteilung, Container, Veroeffentlichung) — kostet aber Einarbeitung,
  Python-Umgebung und einen anderen Arbeitsstil.
- **Kein Mehrbenutzer-System.** Es ist fuer **einen** Menschen gebaut, der in Jahren noch
  verstehen will, was wo liegt.

## Nutzen-Verdikt

Fuer einen Einzelmenschen mit ~2,6 Mio Dateien ist **genau diese Bauform** richtig:
keine Cloud, keine Datenbank, kein Dienst, dafuer **pruefbar** und in einem Befehl beantwortbar
("haelt der Baum noch?"). Wer verteilte Teams, Versionierung von Terabytes oder
wissenschaftliche Veroeffentlichung braucht, nimmt DataLad. Wer Ordnung **und Nachweis**
in einem will, ohne sich zu binden, nimmt diesen Baum.

## Quellen

- DataLad: https://www.datalad.org/ · https://github.com/datalad/datalad · Lehre Uni Bonn: https://ibots-bonn.de/teaching/research-data-management-with-datalad/
- Repo Integrity Manifest Action: https://github.com/marketplace/actions/repo-integrity-manifest-action
- Gatehouse: https://github.com/1337lean/gatehouse
- Policy-as-Code / Checksummen: https://www.sonatype.com/resources/guides/secure-repository-architecture-blueprint · https://jfrog.com/help/r/what-are-client-checksum-server-checksum-and-checksum-policy-in-local-repositori
- Johnny.Decimal vs PARA: https://help.noteplan.co/article/155-how-to-organize-your-notes-and-folders-using-johnny-decimal-and-para · https://www.clairmind.ai/wiki/para-vs-johnny-decimal · https://www.bigiron.cc/guides/zettelkasten-vs-para-vs-johnny-decimal-organizing-self-hosted-notes


---

# Nachtrag 2026-09-24 — SUCHER-1000-Recherche (40+ Quellen, 5 Läufe, 5156 Treffer archiviert)

Gesucht wurde nach **Git-Ordner-Baum-Systemen** — unter ihren jeweiligen Fachnamen.

## Die Namen, unter denen es das schon gibt

| Wie es heißt | Was es ist | Quelle |
|---|---|---|
| **BagIt (RFC 8493)** | **IETF-Standard** für Ordnerbäume mit Prüfsummen-Manifesten: "hierarchical file layout conventions", "valid = every checksum verified" | rfc-editor.org/info/rfc8493/ |
| **RO-Crate** | Standard für Ordner + Metadaten (`ro-crate-metadata.json`); kann einen BagIt-Bag umhüllen | researchobject.org/ro-crate/specification/1.0/ |
| **DataLad / git-annex** | Git für Daten jeder Größe, verschachtelte Datensätze | datalad.org |
| **Johnny.Decimal** | fester Nummern-Baum (unser Nummernsystem) + fertige Struktur-Vorlagen | johnnydecimal.com · github.com/deathrashed/filesystem-structures |
| **PARA** | Ordner folgen dem Status (Gegenmodell zu fester Nummer) | fortelabs / Vergleichsartikel |
| **SPARC Data Structure** | FAIR-Standard für Ordnerstrukturen in der Biomedizin | doi 10.1101/2021.02.10.430563 |
| **DCH Folder Structure Guidelines** | Ordnerstruktur-Leitlinie | doi 10.5281/zenodo.7452113 |
| **CLEAR-Prinzip** | semantisch klare Datentypen (FAIR) | EuropePMC PMC12570660 |
| **NESTOR-Framework** | Umgang mit hierarchischen Datenstrukturen | doi 10.1007/978-3-642-04346-8_22 |
| **FAIR/RDM-Leitfäden** | Harvard, UBC, Iowa, HKU, CASRAI-Namensregeln, "Data Organization Made Easy" | div. Universitäts-Guides |

**Wichtigster Fund:** Unser Baum ist **BagIt in klein** (Prüfsummen-Manifest + Prüflauf = "valid") und
**RO-Crate-Bruder** (Katalog + STATUS.md = Metadaten). Beide sind **etablierte Standards** — gut so:
wir müssen nichts erfinden, wir können nur **anschlussfähig** werden.

## Was das nützlichste Element zum Einbauen wäre (nach Nutzen geordnet)

| Rang | Element | Nutzen | Aufwand | Nachweis |
|---|---|---|---|---|
| — | **P0: zweite Kopie außer Haus** | schützt gegen Plattenausfall/Diebstahl — das Design nennt es selbst blockierend | Ort wählen (Entscheidung David) | Prüfzeile: "auf ANDEREM Geraet" |
| 1 | **Duplikat-Prüfung (nur lesend)** | gemessen: **114 GB = 32 %** der ~354 GB sind Dubletten — größter konkreter Gewinn | klein (Hash-Prüfung, kein Löschen) | "X GB in Y Doppelgruppen, Z Kandidaten" |
| 2 | **`ro-crate-metadata.json` je Projekt** | Projekte werden **selbstbeschreibend** und standard-kompatibel | klein | Prüfer meldet fehlende Metadatei |
| 3 | **Vorlagen** für neue Projekte | `ordner.sh projekt "x" --vorlage forschung` legt Standard-Unterbau an | sehr klein | Test: Vorlage vollständig |
| 4 | **BagIt-Kennzeichnung** (`bagit.txt`) | macht "valid" zu einem **genormten** Wort | sehr klein | Prüfer + BagIt-Werkzeug lesen es |

**Ehrlich zum Suchlauf:** die Läufe waren ergiebig (33/99/51/39/22 Treffer), aber nicht rauschfrei —
Bing lieferte zu "hierarchy" Fernsehsendungen und zu "duplicate" Wörterbuch-Einträge. Das ist
erwartbar (Mehrdeutigkeit) und wurde von Hand aussortiert.

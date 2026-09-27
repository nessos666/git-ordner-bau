# 00_SYSTEM — Meta-Repository  ·  PROTOTYPE — NOT PRODUCTION

**Zweck:** Regeln, Katalog, Schemas, Prüfregeln, Herkunftsvorlage, Übernahme-Blatt.
Hier steht, **wie** alles andere aussieht.

**Architekturversion:** v1.3 · **Sandbox:** `~/HAUPTLAGER/03_PROJEKTE/55_Git_Ordner_Prototyp/`

**Was hier verwaltet wird:** `manifest/repos.yaml` (Katalog = Absicht), `schemas/`, `policies/`,
`provenance/`, `UEBERNAHME.md`.

**Was hier NIEMALS gespeichert wird:** Daten · Modelle · Logs · Zustand · Caches · Secrets ·
erzeugte Indizes · Projektinhalte.

**Verweis Katalog:** `manifest/repos.yaml` · **Verweis Validator:**
`../70_AUTOMATION/validation/check_all.py`

**Regel:** 00_SYSTEM bleibt klein. Wächst es über ~200 KB, ist etwas falsch einsortiert.

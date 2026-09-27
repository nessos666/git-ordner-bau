# indexing — der Index  ·  PROTOTYPE

**SQLite FTS5.** Kein Server, keine Cloud, keine Vektor-DB, keine zweite DB-Plattform.

**Der Index ist CACHE/PROJEKTION — nie Quelle der Wahrheit.** Quelle der Wahrheit bleiben
**Git + Katalog + reales Dateisystem**. Er darf jederzeit gelöscht und neu gebaut werden.

```
python3 indexer.py build                 # vollständig neu erzeugen
python3 indexer.py search "FTS5"         # suchen (--klasse/--status/--art/--json)
python3 indexer.py status                # Zustand + Veraltet-Prüfung gegen die Quellen
python3 indexer.py drop                  # löscht NUR die Indexdatei
```

**Indexiert:** Katalogfelder · Repo-Metadaten (HEAD/Branch/Remote, read-only) · Pfade · Dateinamen ·
README/Markdown/Textdateien (≤ 256 KB gelesen, ≤ 64 KB je Dokument) · Herkunftsfelder (`ausgabe_sha256`).

**Ausgeschlossen:** `.git`, `.venv`, `node_modules`, `__pycache__`, `cache`, `models`, `logs`,
`state`, `artefakt`, `fixtures`, `tmp_tests` · `60_RUNTIME/**` komplett · Binärdateien
(Endung **oder** Nullbyte im Kopf) · Dateien > 256 KB.

**Secrets:** Zeilen mit Secret-Mustern (`AKIA`, `ghp_`, `sk-`, `PRIVATE KEY`, `api_key`,
`passphrase`, `password`) werden **nicht** in den Index übernommen. Der Zähler steht unter
`meta.uebersprungen`.

**Datei:** `60_RUNTIME/cache/index/suche.db` (innerhalb der Sandbox, jederzeit löschbar).

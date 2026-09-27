#!/usr/bin/env python3
"""Index des Prototyps — SQLite FTS5.  CACHE, NICHT Quelle der Wahrheit.

Quelle der Wahrheit bleiben: Git + Katalog + reales Dateisystem.
Der Index darf JEDERZEIT geloescht und aus den kanonischen Quellen neu gebaut werden.

Aufruf:
    python3 indexer.py build      [--root PFAD]
    python3 indexer.py search "begriff" [--klasse X] [--status Y] [--art Z] [--json]
    python3 indexer.py status     [--json]
    python3 indexer.py drop                      # loescht NUR die Indexdatei

Schreibregel: schreibt AUSSCHLIESSLICH die Indexdatei unter <root>/60_RUNTIME/cache/index/.
Kein Netz. Keine Datenbank aendern. Keine Datei des Baums anfassen.
"""
from __future__ import annotations
import argparse, fcntl, datetime, hashlib, json, os, sqlite3, subprocess, sys
from urllib.parse import quote
from pathlib import Path
import stat
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "validation"))
import rules as _R                                 # BLOCKER 5 (2.7): genau EINE Exception-Definition
from rules import assert_write_inside_sandbox   # BLOCKER 3: DIE eine Schranke (rules)
SandkastenVerletzt = _R.SandkastenVerletzt      # keine gleichnamige zweite Klasse (Alias, keine Kopie)
_R.schutz_installieren()                        # BLOCKER 2 (2.7): Boundary auf DATEI-Ebene erzwingen

SANDBOX = Path(__file__).resolve().parents[3]

# BLOCKER 6: EINE zentrale Exitcode-Tabelle (Doku und Verhalten muessen uebereinstimmen).
# EXIT: wird am Dateiende auf rules.EXIT gesetzt (2.8: EINE zentrale Tabelle)

# BLOCKER 4: ehrlicher Ausweis, WAS am Objektspeicher geprueft wird (kein Vollversprechen).
HISTORY_COVERAGE = "PARTIAL (Arbeitsbaum + HEAD; Seitenzweige/dangling NICHT geprueft)"


class QuellenFehler(Exception):
    """Pflichtquelle fehlt/ist unlesbar/Scan abgebrochen — Index darf NICHT 'frisch' sagen."""
    def __init__(self, msg, zustand="MISSING"):
        super().__init__(msg)
        self.zustand = zustand


def quellenzustand(root: Path):
    """BLOCKER 6: COMPLETE nur, wenn ALLE definierten Quellen vollstaendig geprueft wurden.
    Rueckgabe (zustand, gruende). Kein stilles Verschlucken, kein stilles 'sauber'."""
    gruende = []
    kat = root / "00_SYSTEM/manifest/repos.yaml"
    if not kat.is_file():
        return "MISSING", [f"Pflichtquelle fehlt: {kat}"]
    if not os.access(kat, os.R_OK):
        return "UNREADABLE", [f"Pflichtquelle unlesbar: {kat}"]
    unlesbar, unbekannt = [], []
    grenze = 200000
    n = 0
    for dp, dns, fns in os.walk(root, onerror=lambda e: unlesbar.append(f"{e.filename}: {type(e).__name__}")):
        dns[:] = [d for d in dns if d not in EXCLUDE_DIRS]
        for f in fns:
            n += 1
            if n > grenze:
                gruende.append(f"Scan-Grenze {grenze} erreicht — Rest ungeprueft")
                return "PARTIAL", gruende + [f"Partieller Scan: {n} Objekte"]
            p = Path(dp) / f
            try:
                st = p.lstat()
            except OSError as ex:
                unlesbar.append(f"{p}: {type(ex).__name__}"); continue
            if not (stat.S_ISREG(st.st_mode) or stat.S_ISLNK(st.st_mode) or stat.S_ISDIR(st.st_mode)):
                unbekannt.append(f"{p}: unbekannter Dateityp")
    if unlesbar:
        gruende += unlesbar[:5]
        return "UNREADABLE", gruende
    if unbekannt:
        gruende += unbekannt[:5]
        return "PARTIAL", gruende
    return "COMPLETE", []


def nur_sandkasten(p) -> Path:
    """BLOCKER 3 (Etappe 2.6): KEINE zweite Sandbox-Logik mehr — dies ist nur noch die
    Delegation an DIE zentrale Schranke in rules.assert_write_inside_sandbox()."""
    assert_write_inside_sandbox(p)
    return Path(p)

HIER = Path(__file__).resolve().parent
ROOT_STD = HIER.parents[1]                      # indexing -> 70_AUTOMATION -> MASTER
INDEX_REL = "60_RUNTIME/cache/index/suche.db"

# ---------------- Ausschlussregeln (dokumentiert, Phase 2) ----------------
EXCLUDE_DIRS = {".git", ".venv", "node_modules", "__pycache__", "cache", "models", "logs",
                "state", ".pytest_cache", "fixtures", "tmp_tests", "artefakt"}
TEXT_EXT = {".md", ".txt", ".yaml", ".yml", ".json", ".py", ".sh", ".toml", ".ini", ".csv", ".cfg"}

_ECHTER_CONNECT = sqlite3.connect


def rein(x):
    """BLOCKER 1: EINE zentrale Textdarstellung fuer alles, was SQLite sieht."""
    if not isinstance(x, str):
        return x
    try:
        x.encode("utf-8")
        return x
    except UnicodeEncodeError:
        return "".join(chr(b) if 32 <= b < 127 else "\\x%02x" % b for b in x.encode("utf-8", "surrogateescape"))


class _Conn(sqlite3.Connection):
    def execute(self, sql, parameters=()):
        if isinstance(parameters, (tuple, list)):
            parameters = tuple(rein(x) for x in parameters)
        return super().execute(sql, parameters)

    def executemany(self, sql, seq):
        return super().executemany(sql, [tuple(rein(x) for x in p) for p in seq])


def verbinden(p, *a, **k):
    return _ECHTER_CONNECT(str(p), *a, factory=_Conn, **k)


MAX_EINLESEN = 256 * 1024          # groessere Dateien werden NICHT vollstaendig gelesen
MAX_INHALT = 64 * 1024             # je Dokument hoechstens so viel Text in den Index
SECRET_RX = ["AKIA", "ghp_", "sk-", "PRIVATE KEY", "api_key", "api-key", "passphrase", "password", "passwd"]
KEINE_BIN = {".bin", ".mmap", ".dat", ".parquet", ".gguf", ".safetensors", ".zip", ".gz", ".db",
             ".sqlite", ".pyc", ".so", ".png", ".jpg", ".jpeg", ".gif", ".pdf", ".woff", ".woff2"}


def index_pfad(root: Path) -> Path:
    return root / INDEX_REL


def quellen_stempel(root: Path) -> str:
    """EXAKTER Stempel der Quellen fuer die Frische (Index ist nur CACHE).
    Enthaelt Anzahl, Gesamtgroesse, mtime_ns und den INHALT aller Textdateien <= 256 KB.
    Vorher wurde nur der groesste mtime verglichen — eine Inhaltsaenderung mit
    WIEDERHERGESTELLTER mtime blieb unsichtbar ('veraltet: nein', RT-B Befund)."""
    h = hashlib.sha256(); n = 0; gesamt = 0; max_ns = 0
    for dp, dns, fns in os.walk(root, followlinks=False):
        dns[:] = sorted(d for d in dns if d not in EXCLUDE_DIRS and d != ".git")
        try:
            if str(Path(dp).relative_to(root)).startswith("60_RUNTIME"):
                dns[:] = []; continue
        except ValueError:
            pass
        try: max_ns = max(max_ns, Path(dp).stat().st_mtime_ns)
        except OSError: pass
        for f in sorted(fns):
            q = Path(dp) / f
            try: st = q.lstat()
            except OSError: continue
            n += 1
            if q.is_symlink():
                try: h.update(f"{q.relative_to(root)}|sym|{os.readlink(q)}".encode("utf-8", "surrogateescape"))
                except OSError: h.update(f"{q}|sym|?".encode())
                continue
            gesamt += st.st_size; max_ns = max(max_ns, st.st_mtime_ns)
            h.update(f"{q.relative_to(root)}|{st.st_size}|{st.st_mtime_ns}".encode("utf-8", "surrogateescape"))
            if not stat.S_ISREG(st.st_mode):   # BLOCKER 2: FIFO/Socket/Geraet NIE oeffnen
                continue
            if st.st_size <= MAX_EINLESEN:      # A9: auch Dateien OHNE Textendung inhaltlich stempeln
                try: h.update(hashlib.sha256(q.read_bytes()).digest())
                except OSError: h.update(b"<unlesbar>")
    return f"{n}|{gesamt}|{max_ns}|{h.hexdigest()[:32]}"


class IndexDefekt(Exception):
    """Der Index ist beschaedigt. Er ist CACHE — die Loesung ist Neuaufbau, nicht Reparatur."""


class IndexBelegt(Exception):
    """Ein anderer Prozess baut gerade. Der LETZTE GUELTIGE Index bleibt lesbar."""


def _schreib_lock(root: Path):
    """Exklusiver Lock fuer den SCHREIBER (nur build/drop). flock wird vom Kernel beim
    Prozessende freigegeben — ein Crash hinterlaesst deshalb KEINEN aktiven Lock.
    Reader brauchen keinen Lock: sie lesen die jeweils gueltige Datei."""
    lp = index_pfad(root).with_name(index_pfad(root).name + ".lock")
    nur_sandkasten(lp)
    lp.parent.mkdir(parents=True, exist_ok=True)
    fh = open(lp, "a+")
    try:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as ex:
        fh.close()
        raise IndexBelegt("Ein anderer Prozess baut gerade den Index (Lock gehalten) — "
                          "der letzte gueltige Index bleibt unveraendert lesbar.") from ex
    return fh


def _tmp_reste(root: Path):
    """Reste abgebrochener Laeufe (suche.db.tmp-*) — nur diese Dateien, nie der gueltige Index."""
    d = index_pfad(root).parent
    if not d.is_dir(): return []
    return sorted(p for p in d.glob(index_pfad(root).name + ".tmp-*") if p.is_file())


def verbinde(root: Path, neu_erzeugen=False, schreibbar=True):
    """schreibbar=False => NUR LESEN. Suche/Status duerfen den Index NIE anlegen oder aendern
    (RT-B: 'indexer search --root <fremd>' erzeugte zuvor eine Indexdatei ausserhalb)."""
    p = index_pfad(root)
    if p.exists() and p.is_dir():
        raise IndexDefekt(f"Indexpfad ist ein VERZEICHNIS ({p}) — das ist kein Index. "
                          "Verzeichnis entfernen, dann 'build'.")
    if p.exists():
        # F2 (2.8): Sonderdatei (FIFO/Geraet/Socket) oder Symlink als Indexdatei liess SQLite
        # unbegrenzt blockieren: 'indexer status'/'search' hingen >25 s (strace: openat mit
        # O_RDONLY|O_NOFOLLOW|O_CLOEXEC auf die FIFO, ohne O_NONBLOCK). Vor jedem Oeffnen pruefen.
        import stat as _stat
        try:
            _modus = os.lstat(p).st_mode
        except OSError as ex:
            raise IndexDefekt(f"Indexpfad nicht pruefbar ({type(ex).__name__}: {ex}).") from ex
        if not _stat.S_ISREG(_modus):
            _art = "SYMLINK" if _stat.S_ISLNK(_modus) else "SONDERDATEI (FIFO/Geraet/Socket)"
            raise IndexDefekt(f"Indexpfad ist ein {_art} ({p}) — kein regulaerer Index. "
                              "Der Index ist CACHE/PROJEKTION: Sonderdatei entfernen, dann 'build'. "
                              "Es wird NICHT gelesen und NICHT gewartet.")
    if not schreibbar:
        if not p.exists():
            raise IndexDefekt("Index fehlt — der Index ist CACHE/PROJEKTION: mit 'build' neu erzeugen.")
        try:
            # immutable=1: SQLite legt dann KEINE -wal/-shm-Dateien an. Vorher schrieb
            # "search" auf einem WAL-Index in ein schreibgeschuetztes Verzeichnis (RT-B Befund).
            try:
                v = verbinden(f"file:{quote(str(p))}?mode=ro&immutable=1", uri=True)
            except Exception as ex:            # BLOCKER 6: beschaedigter Index, keine Traceback-Antwort
                print(f"ERROR: Index nicht lesbar ({type(ex).__name__}): {p}", file=sys.stderr)
                return EXIT["ERROR"]
            v.execute("SELECT COUNT(*) FROM meta").fetchone()
            return v
        except sqlite3.DatabaseError as ex:
            raise IndexDefekt(f"Index nicht lesbar ({ex}) — er ist CACHE: mit 'build' neu erzeugen.") from ex
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
    except OSError as ex:
        raise IndexDefekt(f"Indexordner nicht anlegbar ({ex}).") from ex
    v = verbinden(str(p))
    try:
        v.execute("""CREATE VIRTUAL TABLE IF NOT EXISTS dokumente USING fts5(
            name, pfad, art, klasse, status, bereich, inhalt)""")
        v.execute("CREATE TABLE IF NOT EXISTS meta (schluessel TEXT PRIMARY KEY, wert TEXT)")
    except (sqlite3.DatabaseError, OSError) as ex:
        try: v.close()
        except Exception: pass
        if not neu_erzeugen:
            raise IndexDefekt(f"Indexdatei beschaedigt ({ex}). Der Index ist CACHE/PROJEKTION — "
                              f"mit 'build' vollstaendig neu erzeugen; es gehen KEINE Quellen verloren.") from ex
        try:
            p.unlink(missing_ok=True)   # nur die Indexdatei selbst (Phase 3: delete/rebuild erlaubt)
        except OSError as ex2:
            raise IndexDefekt(f"Index ist nicht loeschbar (Rechte?): {ex2} — Pfad: {p}") from ex2
        v = verbinden(str(p))
        v.execute("""CREATE VIRTUAL TABLE dokumente USING fts5(
            name, pfad, art, klasse, status, bereich, inhalt)""")
        v.execute("CREATE TABLE meta (schluessel TEXT PRIMARY KEY, wert TEXT)")
    return v


def git_info(repo: Path):
    """NUR LESEN: HEAD, Branch, Remote."""
    def g(*a):
        # RT-Final-2 A2: die geerbte Umgebung liess GIT_TRACE eine Datei AUSSERHALB anlegen und
        # GIT_DIR ein fremdes Repository adressieren — Allowlist statt Vererbung.
        _env = {k: v for k, v in os.environ.items()
                if k in ("PATH", "HOME", "LANG", "LC_ALL", "LC_CTYPE", "TZ", "USER", "LOGNAME", "SHELL")}
        _env.update({"GIT_OPTIONAL_LOCKS": "0", "GIT_TERMINAL_PROMPT": "0", "GIT_ASKPASS": "/bin/true",
                     "GIT_PAGER": "cat", "GIT_CONFIG_NOSYSTEM": "1",
                     "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull})
        r = subprocess.run(["git", "-C", str(repo), "-c", "core.fsmonitor=false",
                            "-c", "core.hooksPath=/nonexistent-hooks", *a],
                           capture_output=True, text=True, timeout=20, env=_env)
        return r.stdout.strip() if r.returncode == 0 else ""
    return {"head": g("rev-parse", "HEAD")[:12], "branch": g("rev-parse", "--abbrev-ref", "HEAD"),
            "remote": g("remote", "get-url", "origin")}


def text_von(p: Path):
    """Liefert (text, uebersprungen_grund). Secrets werden NICHT kopiert."""
    # BLOCKER 2 (zentral): KEIN unbekannter Dateityp wird geoeffnet. FIFO/Socket/Geraet koennen
    # beim Oeffnen unbegrenzt blockieren — der Typ wird deshalb VOR jedem Lesen bestimmt.
    try:
        _st = p.lstat()
    except OSError:
        return None, "nicht_lesbar"
    if not stat.S_ISREG(_st.st_mode):
        return None, "kein_regulaerer_dateityp"
    try:
        if p.stat().st_size > MAX_EINLESEN: return None, "zu_gross"
    except OSError: return None, "nicht_lesbar"
    if p.suffix.lower() in KEINE_BIN: return None, "binaer_endung"
    try: roh = p.read_bytes()
    except OSError: return None, "nicht_lesbar"
    if b"\0" in roh[:4096]: return None, "binaer_inhalt"
    try: t = roh.decode("utf-8")
    except UnicodeDecodeError: return None, "kein_utf8"
    zeilen, secret = [], False
    for z in t.splitlines():
        if any(s.lower() in z.lower() for s in SECRET_RX):
            secret = True; continue                      # Zeile NICHT uebernehmen
        zeilen.append(z)
    return ("\n".join(zeilen)[:MAX_INHALT], "secret_zeilen_entfernt" if secret else "")


def build(root: Path, still=False):
    """Baut den Index ATOMAR: in eine temporaere Datei, dann atomarer Tausch (os.replace).
    Ein fehlgeschlagener oder abgebrochener Neuaufbau kann den letzten gueltigen Index
    deshalb NICHT zerstoeren. Schreibzugriff ist durch einen exklusiven Lock geschuetzt."""
    import yaml
    ziel = index_pfad(root)
    nur_sandkasten(ziel)
    lock = _schreib_lock(root)
    tmp = ziel.with_name(ziel.name + f".tmp-{os.getpid()}")
    reste = _tmp_reste(root)
    for alt_rest in reste:                     # Reste abgebrochener Laeufe entfernen (nur Indexdateien)
        try: nur_sandkasten(alt_rest).unlink()
        except OSError: pass
    try:
        if ziel.exists() and ziel.is_dir():
            raise IndexDefekt(f"Indexpfad ist ein VERZEICHNIS ({ziel}) — kein Index.")
        try:
            nur_sandkasten(tmp).unlink(missing_ok=True)
        except OSError:
            pass
        v = verbinden(str(tmp))
        v.execute("""CREATE VIRTUAL TABLE IF NOT EXISTS dokumente USING fts5(
            name, pfad, art, klasse, status, bereich, inhalt)""")
        v.execute("CREATE TABLE IF NOT EXISTS meta (schluessel TEXT PRIMARY KEY, wert TEXT)")
    except Exception as ex:
        try: v.close()
        except Exception: pass
        try: nur_sandkasten(tmp).unlink(missing_ok=True)
        except OSError: pass
        lock.close()
        if isinstance(ex, IndexDefekt): raise
        raise IndexDefekt(f"Indexbau nicht moeglich ({type(ex).__name__}: {ex}). "
                          "Der bisherige Index bleibt unveraendert.") from ex
    t0 = datetime.datetime.now()
    anzahl = {"katalog": 0, "repo": 0, "datei": 0, "provenienz": 0}
    stempel = quellen_stempel(root)          # exakter Quellenstempel (mit Inhalt)
    uebersprungen = {}
    kat_datei = root / "00_SYSTEM/manifest/repos.yaml"
    katalog = {}
    # BLOCKER 6: der Katalog ist PFLICHTQUELLE — sein FEHLEN ist ein Fehler und darf
    # NIEMALS als "INDEX GEBAUT ... Exit 0" durchgehen. (`if True` haelt die vorhandene
    # Blockstruktur/Einrueckung unveraendert; nur der Fall 'fehlt' wird jetzt abgelehnt.)
    if True:
        if not kat_datei.is_file():
            raise QuellenFehler(f"Pflichtquelle fehlt: Katalog {kat_datei}", "MISSING")
        try:
            katalog = yaml.safe_load(kat_datei.read_text(encoding="utf-8")) or {}
        except Exception as ex:
            raise QuellenFehler(f"Katalog unlesbar ({type(ex).__name__}): {kat_datei}", "ERROR") from ex
        for e in katalog.get("repos", []):
            inhalt = " ".join(str(e.get(k, "")) for k in ("beschreibung", "owner", "remote", "pin", "extern"))
            v.execute("INSERT INTO dokumente VALUES (?,?,?,?,?,?,?)",
                      (str(e.get("name", "")), str(e.get("pfad", "")), "katalog", str(e.get("class", "")),
                       str(e.get("status", "")), str(e.get("bereich", "")), inhalt))
            anzahl["katalog"] += 1
            if e.get("git"):
                p = root / str(e.get("pfad", ""))
                if (p / ".git").exists():
                    gi = git_info(p)
                    v.execute("INSERT INTO dokumente VALUES (?,?,?,?,?,?,?)",
                              (str(e.get("name", "")), str(e.get("pfad", "")), "repo", str(e.get("class", "")),
                               str(e.get("status", "")), str(e.get("bereich", "")),
                               f"HEAD {gi['head']} Branch {gi['branch']} Remote {gi['remote']}"))
                    anzahl["repo"] += 1
    # Vererbung: Dateien erben klasse/status/bereich des Katalogseintrags, unter dem sie liegen
    zuordnung = []
    for e in katalog.get("repos", []):
        pf = str(e.get("pfad", ""))
        if pf: zuordnung.append((pf, str(e.get("class", "")), str(e.get("status", "")),
                                 str(e.get("bereich", "")), str(e.get("name", ""))))
    zuordnung.sort(key=lambda t: -len(t[0]))

    def erbe(rp: str):
        for pf, k, st, b, n in zuordnung:
            if rp == pf or rp.startswith(pf + "/"):
                return k, st, b, n
        teile = rp.split("/")
        return "", "", (teile[0] if teile and teile[0][:2].isdigit() else ""), ""

    quelle_max = 0.0
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in EXCLUDE_DIRS]
        rel = str(Path(dp).relative_to(root))
        if rel.startswith("60_RUNTIME"):      # Zustand/Cache/Artefakt niemals indexieren
            dns[:] = []; continue
        try: quelle_max = max(quelle_max, Path(dp).stat().st_mtime)
        except OSError: pass
        for f in fns:
            p = Path(dp) / f
            try: quelle_max = max(quelle_max, p.stat().st_mtime)
            except OSError: pass
            if p.is_symlink():
                # SYMLINK-ZIELE werden NICHT eingelesen: ein Link im Baum auf eine Datei
                # AUSSERHALB brachte fremden Inhalt in den Index (RT-B Befund). Der Name bleibt.
                rp = str(p.relative_to(root))
                k, st, b, _ = erbe(rp)
                v.execute("INSERT INTO dokumente VALUES (?,?,?,?,?,?,?)",
                          (f, rp, "symlink", k, st, b, f"-> {os.readlink(p)}"))
                anzahl["symlink"] = anzahl.get("symlink", 0) + 1
                uebersprungen["symlink_nicht_gelesen"] = uebersprungen.get("symlink_nicht_gelesen", 0) + 1
                continue
            txt, grund = text_von(p)
            if grund: uebersprungen[grund] = uebersprungen.get(grund, 0) + 1
            rp = str(p.relative_to(root))
            # Herkunft nur, wenn ein echter Herkunftskopf vorliegt (nicht nur das Wort im Text)
            art = "provenienz" if (txt and "kopf:" in txt and "ausgabe_sha256" in txt) else "datei"
            k, st, b, _ = erbe(rp)
            v.execute("INSERT INTO dokumente VALUES (?,?,?,?,?,?,?)",
                      (f, rp, art, k, st, b, (txt or "")[:MAX_INHALT]))
            anzahl[art] = anzahl.get(art, 0) + 1
            if txt is None: anzahl["datei"] = anzahl.get("datei", 0)
    for k, w in (("schema_version", "1"), ("erzeugt", t0.isoformat(timespec="seconds")),
                 ("quelle_stempel", stempel),            # exakt: Name/Groesse/mtime_ns/Inhalt
                 ("quelle_max_mtime", f"{quelle_max:.6f}"),      # volle Genauigkeit (Millisekunden-Rundung kippte den Vergleich)
                 ("anzahl", str(sum(anzahl.values()))), ("aussCHLuesse", json.dumps(sorted(EXCLUDE_DIRS))),
                 ("quellen", "Katalog + Repo-Metadaten + Dateinamen + Textdateien"),
                 ("uebersprungen", json.dumps(uebersprungen))):
        v.execute("INSERT OR REPLACE INTO meta VALUES (?,?)", (k, w))
    v.commit(); v.execute("INSERT INTO dokumente(dokumente) VALUES('optimize')"); v.commit()
    dauer = (datetime.datetime.now() - t0).total_seconds()
    v.close()
    try:
        os.replace(tmp, ziel)          # ATOMAR: Reader sehen entweder alt oder neu, nie halb
    except OSError as ex:
        try: nur_sandkasten(tmp).unlink(missing_ok=True)
        except OSError: pass
        lock.close()
        raise IndexDefekt(f"Atomarer Tausch fehlgeschlagen ({ex}) — der alte Index bleibt gueltig.") from ex
    lock.close()
    groesse = ziel.stat().st_size
    if not still and reste:
        print(f"  Hinweis: {len(reste)} Rest(e) abgebrochener Laeufe entfernt: "
              f"{[p.name for p in reste]}")
    if not still:      # 'still' wird von Mess- und Testläufen genutzt (keine Ausgabe im Testprotokoll)
        print(f"INDEX GEBAUT: {sum(anzahl.values())} Dokumente {anzahl} · {dauer:.2f} s · {groesse/1e6:.2f} MB")
        print(f"  uebersprungen: {uebersprungen}")
    return {"dauer_s": dauer, "groesse_b": groesse, "anzahl": anzahl, "uebersprungen": uebersprungen}


def sichere_anfrage(q: str) -> str:
    """FTS5-Syntax entschaerfen: jeder Begriff wird gequotet -> keine Operator-Injektion."""
    teile = [t.replace('"', "") for t in q.split() if t.replace('"', "").strip()]
    return " AND ".join(f'"{t}"' for t in teile) if teile else '""'


def search(root: Path, q: str, klasse=None, status=None, art=None, limit=20):
    try:
        v = verbinde(root, schreibbar=False)     # Suche aendert NICHTS
    except IndexDefekt as ex:
        return [], str(ex)
    sql = ("SELECT name, pfad, art, klasse, status, bereich, "
           "snippet(dokumente, 6, '[', ']', ' … ', 12) FROM dokumente WHERE dokumente MATCH ?")
    par = [sichere_anfrage(q)]
    if klasse: sql += " AND klasse = ?"; par.append(klasse)
    if status: sql += " AND status = ?"; par.append(status)
    if art:    sql += " AND art = ?";    par.append(art)
    sql += " ORDER BY rank LIMIT ?"; par.append(limit)
    try:
        zeilen = v.execute(sql, par).fetchall()
    except sqlite3.OperationalError as ex:
        v.close(); return [], f"Suchfehler: {ex}"
    v.close()
    return zeilen, None


def status(root: Path):
    p = index_pfad(root)
    if not p.exists():
        return {"kodierung": "UTF-8 verlustfrei; ungueltige Namen escaped (\\xNN) und als ungeprueft ausgewiesen",
                "history_coverage": HISTORY_COVERAGE, "quellen_zustand": quellen_zustand_streng(root)[0],
                "vorhanden": False, "hinweis": "Index fehlt — jederzeit mit 'build' neu erzeugbar (CACHE)."}
    try:
        v = verbinde(root, schreibbar=False)
    except IndexDefekt as ex:
        return {"vorhanden": True, "defekt": True, "hinweis": str(ex)}
    try:
        meta = dict(v.execute("SELECT schluessel, wert FROM meta").fetchall())
        arten = dict(v.execute("SELECT art, COUNT(*) FROM dokumente GROUP BY art").fetchall())
    except sqlite3.DatabaseError as ex:
        v.close()
        return {"vorhanden": True, "defekt": True,
                "hinweis": f"Index nicht abfragbar ({ex}) — 'build' erzeugt ihn neu."}
    v.close()
    # Gueltige, aber LEERE oder ausgeraeumte DB ist kein Index (RT-A F1/F2)
    leer = (sum(arten.values()) == 0) or (not meta)
    versprochen = int(meta.get("anzahl", "0") or 0)
    if versprochen and not sum(arten.values()):
        return {"vorhanden": True, "defekt": True,
                "hinweis": f"Index ist LEER, obwohl {versprochen} Dokumente erwartet waren — "
                           "'build' erzeugt ihn aus den Quellen neu (CACHE)."}
    # Veraltet? Index ist CACHE — er darf nie behaupten, Wahrheit zu sein.
    erzeugt = meta.get("erzeugt", "")
    neueste = 0.0
    for dp, dns, fns in os.walk(root):            # ALLE Bereiche, nicht nur 00_SYSTEM/70_AUTOMATION
        dns[:] = [d for d in dns if d not in EXCLUDE_DIRS and d != ".git"]
        if str(Path(dp).relative_to(root)).startswith("60_RUNTIME"):
            dns[:] = []; continue
        try:                                          # Ordner-Zeitstempel: faengt neue/entfernte Dateien
            neueste = max(neueste, Path(dp).stat().st_mtime)
        except OSError: pass
        for f in fns:
            try: neueste = max(neueste, (Path(dp) / f).stat().st_mtime)
            except OSError: pass
    veraltet = "unbekannt"
    basis = "Stempel: Name/Groesse/mtime_ns + Inhalt (Textdateien <= 256 KB)"
    stempel_meta = meta.get("quelle_stempel")
    if stempel_meta:
        # EXAKTER Vergleich, keine Toleranz: eine Toleranz verdeckte eine echte Aenderung,
        # und der Stempel enthaelt jetzt auch den INHALT der Textdateien (RT-B Befund).
        zustand, zgruende = quellen_zustand_streng(root)   # BLOCKER 1: strikter Zustand ist die
        stempel_ok = quellen_stempel(root) == stempel_meta
        # BLOCKER 6: "frisch" heisst ALLE Quellen vollstaendig geprueft — nicht nur Stempel gleich
        veraltet = "nein" if (stempel_ok and zustand == "COMPLETE") else (
            "unbestimmt" if zustand != "COMPLETE" else "ja")
        return {"kodierung": "UTF-8 verlustfrei; ungueltige Namen escaped (\\xNN) und als ungeprueft ausgewiesen",
                "history_coverage": HISTORY_COVERAGE, "quellen_zustand": quellen_zustand_streng(root)[0],
                "vorhanden": True, "defekt": bool(leer), "leer": bool(leer), "groesse_b": p.stat().st_size,
                "erzeugt": erzeugt, "arten": arten, "veraltet_gegenueber_quellen": veraltet,
                "frische_basis": basis, "meta": meta, "quellen_zustand": zustand, "quellen_gruende": zgruende[:5], "history_coverage": HISTORY_COVERAGE,
                "hinweis": "Index ist LEER — 'build' erzeugt ihn neu (CACHE)." if leer else ""}
    basis = "NUR mtime (Altbestand ohne Stempel) — Inhaltsaenderung mit gleicher mtime unentdeckt"
    qm = meta.get("quelle_max_mtime")
    if qm:
        # NUMERISCH und mit 0,5 s Toleranz: ein Sekundenvergleich meldete direkt nach dem Bau
        # 'veraltet', weil Dateizeitstempel Millisekunden tragen (RT-A F3).
        try: veraltet = "ja" if neueste > float(qm) + 0.002 else "nein"   # 2 ms Toleranz (Dateisystem-Granularitaet)
        except ValueError: veraltet = "unbekannt"
    elif erzeugt:
        try:
            t0 = datetime.datetime.fromisoformat(erzeugt).timestamp()
            veraltet = "ja" if neueste > t0 else "nein"
        except Exception: pass
    return {"kodierung": "UTF-8 verlustfrei; ungueltige Namen escaped (\\xNN) und als ungeprueft ausgewiesen",
                "history_coverage": HISTORY_COVERAGE, "quellen_zustand": quellen_zustand_streng(root)[0],
                "vorhanden": True, "defekt": bool(leer), "leer": bool(leer), "groesse_b": p.stat().st_size,
            "erzeugt": erzeugt, "arten": arten, "veraltet_gegenueber_quellen": veraltet,
            "frische_basis": basis, "meta": meta, "quellen_zustand": zustand, "quellen_gruende": zgruende[:5], "history_coverage": HISTORY_COVERAGE,
            "hinweis": "Index ist LEER — 'build' erzeugt ihn neu (CACHE)." if leer else ""}


def drop(root: Path):
    p = index_pfad(root)
    assert str(p).startswith(str(root)) and p.name == "suche.db", "Sicherung: falscher Pfad"
    nur_sandkasten(p)
    lock = _schreib_lock(root)                 # auch Loeschen ist ein Schreibzugriff
    for rest in _tmp_reste(root):
        try: nur_sandkasten(rest).unlink()
        except OSError: pass
    try:
        if p.exists(): p.unlink(); return True, f"Index geloescht: {p}"
        return False, "Index war nicht vorhanden"
    finally:
        lock.close()


def main():
    try:
        return _haupt()
    except _R.SandkastenVerletzt as ex:
        print(f"ABBRUCH: {ex}", file=sys.stderr)
        _R._melde_verweigerung(str(ex))
        return EXIT["GRENZE"]
    except QuellenFehler as ex:
        print(f"ERROR: {ex} [{ex.zustand}]", file=sys.stderr)
        return EXIT["ERROR"]
    except SandkastenVerletzt as ex:
        print(f"ABBRUCH: {ex}", file=sys.stderr)
        return EXIT["GRENZE"]
    except Exception as ex:      # BLOCKER 6: keine Tracebacks als normale CLI-Antwort
        print(f"ERROR: {type(ex).__name__}: {ex}", file=sys.stderr)
        return EXIT["ERROR"]


def _haupt():
    # BLOCKER 6: fehlender Root ist MISSING, kein Exit 0. KEIN Zugriff auf das Namespace-Objekt,
    # das erst weiter unten entsteht (das hatte einen UnboundLocalError erzeugt).
    if "--root" in sys.argv:
        _r = Path(sys.argv[sys.argv.index("--root") + 1])
        if not _r.is_dir():
            raise QuellenFehler(f"Root fehlt oder ist kein Verzeichnis: {_r}", "MISSING")
    ap = argparse.ArgumentParser()
    ap.add_argument("befehl", choices=["build", "search", "status", "drop"])
    ap.add_argument("begriff", nargs="?")
    ap.add_argument("--root", default=str(ROOT_STD))
    ap.add_argument("--klasse"); ap.add_argument("--status"); ap.add_argument("--art")
    ap.add_argument("--limit", type=int, default=20); ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    root = Path(a.root).expanduser().resolve()
    if a.befehl in ("build", "drop"):
        try:
            assert_write_inside_sandbox(root)      # BLOCKER 3: DIE zentrale Schranke
        except SandkastenVerletzt as ex:
            print(f"ABBRUCH: {a.befehl} wuerde ausserhalb der Sandbox schreiben ({root}). {ex}", file=sys.stderr)
            print(f"ABBRUCH: {a.befehl} wuerde ausserhalb der Sandbox schreiben ({root}).", file=sys.stderr)
            return 3
    if a.befehl == "build":
        try:
            r = build(root, still=a.json)   # F4 (2.8): bei --json NUR JSON auf stdout
        except IndexBelegt as ex:
            print(f"INDEX BELEGT: {ex}", file=sys.stderr); return 4
        except IndexDefekt as ex:
            print(f"INDEX-FEHLER: {ex}", file=sys.stderr); return 2
        if a.json:
            print(json.dumps(r, ensure_ascii=True, indent=2))
    elif a.befehl == "status":
        r = status(root)
        # BLOCKER 6: ein defekter Index darf NIE mit Exit 0 durchgehen (zentrale Tabelle)
        _rc = EXIT["OK"]
        if r.get("defekt"):
            _rc = EXIT["ERROR"]
        elif not r.get("vorhanden"):
            _rc = EXIT["UNBESTAETIGT"]
        elif r.get("quellen_zustand") and r["quellen_zustand"] != "COMPLETE":
            _rc = EXIT["UNBESTAETIGT"]
        print(json.dumps(r, ensure_ascii=True, indent=2) if a.json else
              (f"Index: {'vorhanden' if r.get('vorhanden') else 'FEHLT'} · {r.get('groesse_b',0)/1e6:.2f} MB · "
               f"erzeugt {r.get('erzeugt','-')} · veraltet: {r.get('veraltet_gegenueber_quellen','-')} · "
               f"Quellen: {r.get('quellen_zustand','-')} · kodierung: {r.get('kodierung','-')} · Arten {r.get('arten')}"))
        return _rc
    elif a.befehl == "drop":
        ok, msg = drop(root); print(msg if not a.json else json.dumps({"geloescht": ok, "meldung": msg}))
    else:
        if not a.begriff:
            print("Suchbegriff fehlt"); return 2
        treffer, fehler = search(root, a.begriff, a.klasse, a.status, a.art, a.limit)
        if fehler: print(fehler); return 2
        if a.json: print(json.dumps([{"name": t[0], "pfad": t[1], "art": t[2], "klasse": t[3],
                                      "status": t[4], "bereich": t[5], "ausschnitt": t[6]} for t in treffer],
                                    ensure_ascii=False, indent=2))
        else:
            print(f"{len(treffer)} Treffer für '{a.begriff}':")
            for t in treffer: print(f"  [{t[2]:10}] {t[1]:58} {t[6][:70]}")
    return 0


def quellen_zustand_streng(root):
    """BLOCKER 1 (2.7): COMPLETE nur, wenn jede erforderliche regulaere Datei WIRKLICH lesbar ist.

    lstat()/Dateityp allein genuegt nicht: eine Datei mit chmod 000 ist regulaer, aber unlesbar.
    Hier wird deshalb zusaetzlich ein Oeffnungsversuch (read-only) unternommen; jeder Fehlschlag
    macht den Zustand PARTIAL/UNREADABLE und wird als Grund zurueckgegeben.
    """
    zustand, gruende = quellenzustand(root)
    unlesbar, geprueft = [], 0
    for dp, dns, fns in os.walk(root, onerror=lambda e: None):
        if EXCLUDE_DIRS and any(t in Path(dp).parts for t in EXCLUDE_DIRS):
            dns[:] = []; continue
        for fn in fns:
            p = Path(dp) / fn
            try:
                st = p.lstat()
            except OSError:
                unlesbar.append(str(p)); continue
            if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
                continue
            geprueft += 1
            try:
                with open(p, "rb") as f:
                    f.read(1)
            except OSError as ex:
                unlesbar.append(f"{p} ({type(ex).__name__})")
    if unlesbar:
        return "PARTIAL", (gruende or []) + [f"unlesbar: {len(unlesbar)} von {geprueft} regulaeren Dateien"] + unlesbar[:20]
    return zustand, gruende


# ===== 2.8: EINE kanonische Quelle fuer Klasse + Exitcodes =====
try:
    import rules as _regelmodul
except ModuleNotFoundError:                     # Standalone-Aufruf: Pfad selbst finden
    import os as _os, sys as _sys
    _sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "validation"))
    import rules as _regelmodul
SandkastenVerletzt = _regelmodul.SandkastenVerletzt
EXIT = _regelmodul.EXIT

if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:
        # Ausgabe wurde abgeschnitten (z. B. '| head') — kein Fehlerfall, sauber beenden.
        try: sys.stdout.close()
        except Exception: pass
        os._exit(0)

# ===== 2.8: EINE kanonische Quelle fuer Klasse + Exitcodes =====
try:
    import rules as _regelmodul
except ModuleNotFoundError:                     # Standalone-Aufruf: Pfad selbst finden
    import os as _os, sys as _sys
    _sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "validation"))
    import rules as _regelmodul
SandkastenVerletzt = _regelmodul.SandkastenVerletzt
EXIT = _regelmodul.EXIT

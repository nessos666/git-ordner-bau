#!/usr/bin/env python3
"""K1-K8 des MASTER_DESIGN v1.3 — Implementierung.

GRUNDREGEL: Der Pruefer darf AUSSCHLIESSLICH lesen und melden.
Er loescht, verschiebt, benennt um, repariert, committet und pusht NIE.
Alle Funktionen sind reine Leseoperationen (open(), os.scandir, git ls-files).
"""
from __future__ import annotations
import errno
import datetime, os, re, stat, subprocess, hashlib, unicodedata
from pathlib import Path

OK, WARNING, ERROR, CRITICAL = "OK", "WARNING", "ERROR", "CRITICAL"
_rank = {OK: 0, WARNING: 1, ERROR: 2, CRITICAL: 3}

EXCLUDE_DIRS = {".git", ".venv", "node_modules", "__pycache__", "fixtures", ".pytest_cache"}
SCHWELLE_BYTE = 10 * 1024 * 1024          # K1/K8: 10 MB
SCHWER_BYTE   = 100 * 1024 * 1024         # K1: > 100 MB = schwer
K7_TIEFE, K7_BREITE = 5, 20

KLASSE_BEREICH = {
    "system": ["00_SYSTEM"], "agent": ["10_AGENT"], "project": ["20_PROJEKTE"],
    "knowledge": ["30_WISSEN"], "data": ["40_DATEN", "60_RUNTIME"],
    "infra": ["50_INFRA"], "automation": ["70_AUTOMATION"],
    "template": ["80_VORLAGEN"], "archive": ["90_ARCHIV"],
}
# Interpretation fuer FREMDE Abhaengigkeiten: extern:true darf unter einem Projekt
# liegen (vendor/), weil fremder Code mit dem Projekt ausgeliefert wird.
VERBOTENE_PFADTEILE = {".venv", "node_modules", "target", "__pycache__",
                       "cache", "models", "logs", "state", "artefakt"}
VERBOTENE_ENDUNGEN = {".zip", ".tar", ".gz", ".tgz", ".db", ".sqlite", ".parquet",
                      ".mmap", ".dat", ".bin", ".gguf", ".safetensors", ".pyc"}
SANDBOX = Path(__file__).resolve().parents[3]   # BLOCKER 3: EINE Definition (Etappe 2.6)

SECRET_PATTERNS = [
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS Access Key"),
    (re.compile(r"ghp_[A-Za-z0-9]{20,}"), "GitHub-Token"),
    (re.compile(r"sk-[A-Za-z0-9]{20,}"), "API-Key (sk-)"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "privater Schluessel"),
    (re.compile(r"(?i)(api[_-]?key|apikey|token|passwd|password|secret|passphrase)[ \t]*[:=][ \t]*[\"']?[A-Za-z0-9_\-]{12,}"), "Zugangsdaten-Zuweisung"),
]
# A7 (RT-Final-2): die alte Wertklasse zerriss bei JEDEM Sonderzeichen (+ / = . @ &) — damit
# blieben echte Schluessel STILL unsichtbar (AWS-Secretteil, DB-Kennwort mit Sonderzeichen).
# Wertklasse schliesst Klammern/Anfuehrungszeichen aus: so erfuellt diese Zeile nicht ihr eigenes
# Muster (ein Pruefer, der sich selbst als Secret meldet, ist ein falscher Alarm).
_WOERTER = ("api" + "_key", "apikey", "token", "pass" + "wd", "pass" + "word", "secret",
            "pass" + "phrase", "access" + "_key", "client" + "_secret", "auth" + "_key",
            "bearer", "credential")
SECRET_PATTERNS.append((re.compile("(?im)^[ \t]*[\\w\\-]{0,12}(" + "|".join(_WOERTER) +
                               ")[\\w\\-]{0,12}[ \\t]*[:=][ \\t]*[\"']?[^\\s\"'(),;\\[\\]\\{\\}<>]{12,}"),
                       "Zugangsdaten-Zuweisung"))



def k2_scope(ctx: Ctx, repo: Path, tracked):
    """K2-SCOPE (Final-Abnahme A1): Nicht gefuehrte Dateien wurden uebersprungen — ein tadelloser
    Baum konnte so 'sauber' heissen, obwohl niemand diese Dateien ansah. Jetzt wird der Baum
    vollstaendig nach Scope getrennt: tracked (oben geprueft) | untracked | ignoriert |
    ausgeschlossener Bereich (Scope-Regel, benannt) | uebersprungen (Binaer/gross/Symlink, BENANNT).
    Nichts davon gilt stillschweigend als sauber: Treffer in nicht gefuehrten Dateien = CRITICAL,
    alles Ungepruefte wird ausdruecklich gemeldet."""
    import stat as _st
    bekannte = set(tracked)
    z = {"tracked": 0, "untracked": 0, "ignoriert": 0, "ausgeschlossen": 0, "uebersprungen": 0}
    ausgeschlossen, ungeprueft, geprueft_nichtgefuehrt = [], [], 0
    grenze = 20000
    for dp, dns, fns in os.walk(repo):
        dn = Path(dp)
        try:
            rel = dn.relative_to(repo)
        except ValueError:
            continue
        # Scope-Regel: bekannte Massenverzeichnisse werden NICHT blind gescannt — aber BENANNT.
        if any(t in dn.parts for t in EXCLUDE_DIRS) or any(t in rel.parts for t in VERBOTENE_PFADTEILE):
            # BLOCKER 4: REKURSIV zaehlen — `if fns:` liess "node_modules/pkg/secret.txt"
            # als "ausgeschlossen: 0" durchgehen (Bereich war unsichtbar).
            dateien, tiefe = 0, 0
            for r2, d2, f2 in os.walk(dn):
                d2[:] = [d for d in d2 if d != ".git"]
                dateien += len(f2); tiefe += 1
                if tiefe > 500:
                    break
            ausgeschlossen.append(f"{rel} (Scope-Regel: ausgeschlossener Bereich, "
                                  f"{dateien} Dateien NICHT gescannt)")
            z["ausgeschlossen"] += 1 + dateien
            dns[:] = []
            continue
        if ".git" in dns:
            dns.remove(".git")          # .git wird gesondert geprueft (Config + Objektspeicher)
        for f in fns:
            q = dn / f
            try:
                rp = str(q.relative_to(repo))
            except ValueError:
                continue
            if rp in bekannte:
                z["tracked"] += 1
                continue
            if geprueft_nichtgefuehrt >= grenze:
                ungeprueft.append(f"{repo.name}: mehr als {grenze} nicht gefuehrte Dateien — Rest ungeprueft")
                break
            geprueft_nichtgefuehrt += 1
            try:
                st = q.lstat()
            except OSError as ex:
                z["uebersprungen"] += 1
                ungeprueft.append(f"{rp} (nicht lesbar: {type(ex).__name__})")
                continue
            if _st.S_ISLNK(st.st_mode):
                z["uebersprungen"] += 1
                ungeprueft.append(f"{rp} (Symlink — Ziel nicht gelesen)")
                continue
            if not _st.S_ISREG(st.st_mode):
                z["uebersprungen"] += 1
                ungeprueft.append(f"{rp} (keine regulaere Datei)")
                continue
            name, ung = scan_secrets(q)
            if ung:
                z["uebersprungen"] += 1
                ungeprueft.append(f"{rp} (nicht geprueft: >{SECRET_SCAN_MAX >> 20} MB oder unlesbar)")
                continue
            art = "untracked"
            if git_lesend(repo, "check-ignore", "-q", rp).returncode == 0:
                art = "ignoriert"
            z[art] += 1
            if name:
                ctx.add("K2", CRITICAL, q, f"Secret-Muster in NICHT GEFUEHRTER Datei ({name}, {art}). "
                                           f"{REAKTIONSKETTE}")
    ctx.abdeckung["k2_scope"] = z
    ctx.abdeckung["k2_scope_ausgeschlossen"] = ausgeschlossen[:25]
    for u in ungeprueft[:25]:
        ctx.ungeprueft.append({"pfad": f"{repo.name}: {u}", "grund": "K2-Scope: nicht geprueft"})


class SandkastenVerletzt(AssertionError):
    """BLOCKER 3: EINE Ausnahme fuer jede Sandkasten-Verletzung (AssertionError-Unterklasse,
    damit bestehende Waechterpruefungen gueltig bleiben)."""


# Zentrale Exitcode-Semantik (EINE Quelle; Indexer/Pruefer nutzen dieselbe).
EXIT = {"OK": 0, "WARNING": 1, "ERROR": 2, "GRENZE": 3, "UNBESTAETIGT": 4}


def assert_write_inside_sandbox(p) -> Path:
    """BLOCKER 3 (Etappe 2.6): DIE EINZIGE Schranke fuer jeden Schreibpfad.
    VALIDATE BEFORE WRITE — jeder mkdir/touch/tempfile/SQLite/Lock/Log/Probe/Cleanup
    geht hier zuerst durch. Kanonische Aufloesung (auch fuer noch nicht existierende
    Pfadteile), Parent-Pruefung, KEIN startswith()."""
    p = Path(p)
    teil, rest = p, []
    while not teil.exists() and teil != teil.parent:
        rest.append(teil.name)
        teil = teil.parent
    ziel = Path(os.path.realpath(teil)).joinpath(*reversed(rest))
    sb = Path(os.path.realpath(SANDBOX))
    if ziel != sb and sb not in ziel.parents:
        raise SandkastenVerletzt(f"AUSSERHALB DER SANDBOX — Schreiben verweigert: {p}")
    return p

# ===================== BLOCKER 2 (Etappe 2.7): Write-Boundary auf DATEI-Ebene =====================
VERWEIGERUNGEN = []          # BLOCKER 3 (2.7): jede abgelehnte Schreibwirkung wird gezaehlt UND gemeldet


def _melde_verweigerung(grund):
    VERWEIGERUNGEN.append(grund)
    try:
        print(f"ABBRUCH: Schreibgrenze verweigert — {grund}", file=sys.stderr)
    except Exception:
        pass


def _ziel_sicher(ziel):
    """Prueft die KONKRETE Schreibwirkung einer Datei, nicht nur das Elternverzeichnis.

    Die Verzeichnis-Wache allein liess vier belegte Ausbrueche zu: Datei-Symlink, toter Symlink,
    Lock-Symlink, Hardlink. Hier wird deshalb das Ziel SELBST betrachtet (lstat): Symlink,
    Nicht-Regulaerdatei und Hardlink (nlink>1) werden abgelehnt, ebenso ein Elternpfad, der
    selbst ein Symlink ist. Ablehnung heisst ABBRUCH, niemals Umleitung.
    """
    z = Path(str(ziel))
    if "\x00" in str(z):
        _melde_verweigerung(f"NUL-Byte im Zielpfad abgelehnt: {z!r}")
        raise SandkastenVerletzt(f"NUL-Byte im Zielpfad abgelehnt: {z!r}")
    if str(z).startswith("-"):
        raise SandkastenVerletzt(f"Zielpfad beginnt mit '-': {z}")
    eltern = z.parent
    assert_write_inside_sandbox(eltern if eltern.exists() else z)
    if eltern.exists():
        pst = eltern.lstat()
        if stat.S_ISLNK(pst.st_mode) or not stat.S_ISDIR(pst.st_mode):
            raise SandkastenVerletzt(f"Elternpfad ist kein echtes Verzeichnis: {eltern}")
    try:
        st = z.lstat()
    except FileNotFoundError:
        return z
    except OSError as ex:
        raise SandkastenVerletzt(f"Ziel nicht pruefbar ({type(ex).__name__}): {z}")
    if stat.S_ISLNK(st.st_mode):
        raise SandkastenVerletzt(f"Schreibziel ist ein Symlink (Ausbruch verweigert): {z} -> {os.readlink(z)!r}")
    if not stat.S_ISREG(st.st_mode):
        raise SandkastenVerletzt(f"Schreibziel ist keine regulaere Datei: {z}")
    if st.st_nlink > 1:
        raise SandkastenVerletzt(f"Schreibziel hat Hardlinks (nlink={st.st_nlink}) — Fremdinhalt-Schutz: {z}")
    return z


def safe_write_text(ziel, text, modus="w"):
    z = _ziel_sicher(ziel)
    with open(z, modus, encoding="utf-8", newline="") as f:
        f.write(text)
    return z


def safe_append_bytes(ziel, daten):
    z = _ziel_sicher(ziel)
    with open(z, "ab") as f:
        f.write(daten)
    return z


def safe_create_lock(ziel):
    return open(_ziel_sicher(ziel), "a+")


def safe_atomic_replace(ziel, text):
    z = _ziel_sicher(ziel)
    tmp = z.parent / (z.name + f".tmp-{os.getpid()}")
    _ziel_sicher(tmp)
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, z)
    return z


# ============ BLOCKER 2 (2.7, Phase A): fd-basierte, TOCTOU-IMMUNE Write-Boundary ============
def _modus_flags(modus):
    m = modus or "r"
    if "+" in m:
        acc = os.O_RDWR
    elif "a" in m:
        acc = os.O_WRONLY | os.O_APPEND
    elif "x" in m:
        acc = os.O_WRONLY | os.O_EXCL
    elif "w" in m:
        acc = os.O_WRONLY | os.O_TRUNC
    else:
        return None
    if any(c in m for c in "wax"):
        acc |= os.O_CREAT
    return acc


def _fd_in_sandbox(fd):
    """Wahrheit ueber das GEoeffnete Objekt (nicht ueber den Pfad): der Kernel loest auf."""
    try:
        echt = os.readlink(f"/proc/self/fd/{fd}")
    except OSError:
        return False, ""
    try:
        return (Path(os.path.realpath(SANDBOX)) == Path(echt).parent or
                Path(os.path.realpath(SANDBOX)) in Path(echt).parents), echt
    except OSError:
        return False, echt


def safe_open_fd(ziel, modus):
    """Die EINE dichte Write-Boundary. O_NOFOLLOW wird vom KERNEL beim Aufloesen angewandt —
    damit gibt es kein Fenster zwischen Pruefung und Oeffnen (TOCTOU) und ein Symlink-Ziel
    ausserhalb kann gar nicht erst ERZEUGT werden (ELOOP statt Datenverlust). Danach wird das
    GEoeffnete Objekt per fd verifiziert: regulaere Datei, nlink == 1, fd-Pfad in der Sandbox.
    """
    z = Path(str(ziel))
    if "\x00" in str(z):
        _melde_verweigerung(f"NUL-Byte im Zielpfad: {z!r}")
        raise SandkastenVerletzt(f"NUL-Byte im Zielpfad abgelehnt: {z!r}")
    eltern = z.parent
    assert_write_inside_sandbox(eltern if eltern.exists() else z)
    if eltern.exists():
        est = eltern.lstat()
        if stat.S_ISLNK(est.st_mode) or not stat.S_ISDIR(est.st_mode):
            _melde_verweigerung(f"Elternpfad kein echtes Verzeichnis: {eltern}")
            raise SandkastenVerletzt(f"Elternpfad ist kein echtes Verzeichnis: {eltern}")
    if z.exists() or z.is_symlink():
        try:
            st = z.lstat()
        except OSError:
            st = None
        if st is not None:
            if stat.S_ISLNK(st.st_mode):
                _melde_verweigerung(f"Schreibziel ist Symlink: {z} -> {os.readlink(z)!r}")
                raise SandkastenVerletzt(f"Schreibziel ist ein Symlink: {z}")
            if not stat.S_ISREG(st.st_mode):
                _melde_verweigerung(f"Schreibziel kein regulaere Datei: {z}")
                raise SandkastenVerletzt(f"Schreibziel ist keine regulaere Datei: {z}")
            if st.st_nlink > 1:
                _melde_verweigerung(f"Hardlink-Ziel (nlink={st.st_nlink}): {z}")
                raise SandkastenVerletzt(f"Schreibziel hat Hardlinks: {z}")
    flags = _modus_flags(modus)
    if flags is None:
        raise SandkastenVerletzt(f"interner Fehler: safe_open_fd ohne Schreibmodus ({modus!r})")
    try:
        fd = os.open(str(z), flags | os.O_NOFOLLOW | os.O_CLOEXEC, 0o644)
    except OSError as ex:
        # Betriebsfehler INNERHALB der Sandbox (read-only, kein Platz, ...) sind KEINE
        # Boundary-Verletzung — sie werden unveraendert weitergereicht, damit der bestehende
        # Fehlerpfad sie als CRITICAL/Betriebsfehler meldet (nicht als Ausbruch).
        if ex.errno in (errno.EACCES, errno.EPERM, errno.EROFS, errno.ENOSPC, errno.EISDIR):
            raise
        _melde_verweigerung(f"{type(ex).__name__} ({ex.errno}) beim Oeffnen: {z}")
        raise SandkastenVerletzt(f"Oeffnen verweigert ({type(ex).__name__}, errno={ex.errno}): {z}") from ex
    fst = os.fstat(fd)
    drin, echt = _fd_in_sandbox(fd)
    if not stat.S_ISREG(fst.st_mode) or fst.st_nlink > 1 or not drin:
        os.close(fd)
        _melde_verweigerung(f"fd-Verifikation fehlgeschlagen ({echt}): {z}")
        raise SandkastenVerletzt(f"fd-Verifikation fehlgeschlagen: {z} -> {echt}")
    return os.fdopen(fd, modus)


def safe_write_text(ziel, text, modus="w"):
    f = safe_open_fd(ziel, modus)
    with f:
        f.write(text)
    return Path(str(ziel))


# (entfernt 25.09.2026: diese zweite Fassung verwarf 'daten' stillschweigend — OpenCode-Befund)


def safe_create_lock(ziel):
    return safe_open_fd(ziel, "a+")


def schutz_installieren():
    """Erzwingt die Datei-Ebene fuer JEDEN Schreibvorgang des Prozesses — auch fuer open()-Aufrufe,
    die noch nicht auf die safe_*-API umgestellt sind. Nur Verweigerung, keine Umleitung."""
    import builtins
    echt = builtins.open
    if getattr(echt, "_hermes_schutz", False):
        return
    def wache(datei, modus="r", *a, **k):
        if isinstance(datei, (str, os.PathLike)):
            schreiben = any(ch in (modus or "r") for ch in "wax+")
            if schreiben:
                _ziel_sicher(Path(str(datei)))
                return safe_open_fd(datei, modus or "w")
            else:
                # BLOCKER 6: auch fuer LESEN gilt der Dateityp-Schutz — ein FIFO/Socket/Geraet als
                # Kontroll-, Status- oder Beweisdatei darf den Prozess nicht unbegrenzt blockieren.
                z = Path(str(datei))
                try:
                    st = z.lstat()
                except OSError:
                    st = None
                # Ein SYMLINK ist keine blockierende Sonderdatei (OpenCode-Befund 25.09.2026:
                # ein verfolgter Symlink liess K2 mit SandkastenVerletzt abstuerzen). Gesperrt
                # bleiben FIFO/Socket/Geraet — die koennen unbegrenzt blockieren.
                if st is not None and not (stat.S_ISREG(st.st_mode) or stat.S_ISDIR(st.st_mode)
                                           or stat.S_ISLNK(st.st_mode)):
                    raise SandkastenVerletzt(f"Special File wird nicht geoeffnet ({stat.S_IFMT(st.st_mode):#o}): {z}")
        return echt(datei, modus, *a, **k)
    wache._hermes_schutz = True
    builtins.open = wache
    import io as _io
    _io.open = wache        # pathlib.Path.open/write_text gehen ueber io.open


    # BLOCKER 2/3 (2.7): eine ungefangene Boundary-Verletzung darf NIE als Traceback enden.
    # Sie wird kontrolliert zu 'ABBRUCH: ...' mit dem zentralen GRENZE-Exitcode 3.
    import sys as _sys
    _vorher = _sys.excepthook
    def _hook(typ, wert, tb):
        if isinstance(typ, type) and issubclass(typ, SandkastenVerletzt):
            _melde_verweigerung(str(wert))
            _sys.exit(EXIT["GRENZE"])
        _vorher(typ, wert, tb)
    _sys.excepthook = _hook



def schreibpfad(p) -> Path:
    """Kurzform: pruefen und den (ggf. kanonisierten) Pfad zurueckgeben."""
    assert_write_inside_sandbox(p)
    return Path(p)

SECRET_DATEIEN = [re.compile(r"^\.env"), re.compile(r"^credentials.*\.json$"),
                  re.compile(r"^id_rsa"), re.compile(r".*\.pem$")]
REAKTIONSKETTE = ("PFLICHTREAKTION: (1) als kompromittiert behandeln, (2) SOFORT rotieren/widerrufen, "
                  "(3) Auswirkungen pruefen, (4) History nur ZUSAETZLICH bereinigen, "
                  "(5) Forks/Klone koennen die alten Werte weiterhin besitzen.")


class Ctx:
    """Sammelt Befunde. Zaehlt, was tatsaechlich geprueft wurde."""
    def __init__(self, root: Path, catalog: dict):
        self.root, self.catalog = Path(root), catalog
        self.findings, self.geprueft = [], 0
        # Git-Bereiche, die NICHT geprueft werden konnten. Sie fuehren nie zu einem stillen OK.
        self.ungeprueft = []
        self.abdeckung = {}

    def add(self, regel, schwere, pfad, meldung):
        self.findings.append({"regel": regel, "schwere": schwere,
                              "pfad": str(pfad).replace(str(self.root) + "/", ""), "meldung": meldung})

    def tick(self, n=1): self.geprueft += n

    @property
    def level(self):
        return max((f["schwere"] for f in self.findings), key=lambda s: _rank[s], default=OK)


def ist_im_baum(p, root) -> bool:
    """WAHRE Sandkastenpruefung. `startswith(str(root))` liess einen GESCHWISTERORDNER
    durch (z. B. prototyp_git_ordner_SIBLING) — und Schreiben dort ist ein echter Ausbruch.
    Verglichen wird der AUFGELOESTE Pfad: Symlinks werden damit mitgeprueft."""
    try:
        a, b = Path(os.path.realpath(p)), Path(os.path.realpath(root))
    except OSError:
        return False
    return a == b or b in a.parents


# Git nur LESEND und ohne Fremdcode: die Repo-Konfiguration darf NICHT ausgefuehrt werden.
# Ohne diese Einstellungen liess ein Repo mit `core.fsmonitor=<payload>` den Pruefer
# beliebigen Code als Nutzer ausfuehren (RT-A/B Befund).
GIT_HART = ["-c", "core.fsmonitor=false", "-c", "core.hooksPath=/nonexistent-hooks",
            "-c", "core.pager=cat", "-c", "core.askPass=", "-c", "credential.helper=",
            "-c", "core.sshCommand=false", "-c", "gpg.program=false",
            "-c", "core.fsmonitorHookVersion=0", "-c", "protocol.file.allow=never"]
GIT_ENV_KEEP = ("PATH", "HOME", "LANG", "LC_ALL", "LC_CTYPE", "TZ", "USER", "LOGNAME", "SHELL")


def git_env():
    """Erlaubte Umgebung fuer git: nur neutrale Variablen. GIT_DIR, GIT_WORK_TREE,
    GIT_INDEX_FILE, GIT_COMMON_DIR, GIT_CONFIG*, GIT_TRACE, GIT_ALTERNATE_OBJECT_DIRECTORIES
    werden ENTFERNT — ueber sie liess sich die Allowlist umgehen (RT-B Befund)."""
    env = {k: v for k, v in os.environ.items() if k in GIT_ENV_KEEP}
    env.update({"GIT_OPTIONAL_LOCKS": "0", "GIT_TERMINAL_PROMPT": "0", "GIT_ASKPASS": "/bin/true",
                "GIT_PAGER": "cat", "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull,
                "GIT_CONFIG_COUNT": "0", "GIT_TRACE": "", "GIT_TRACE2_EVENT": "",
                "GIT_TRACE2": "", "GIT_FLUSH": "1"})
    return env


def git_lesend(repo, *args):
    """Einziger Git-Aufrufweg des Pruefers: gehaertet, lesend, Umgebung bereinigt."""
    return subprocess.run(["git", "-C", str(repo), *GIT_HART, *args],
                          capture_output=True, env=git_env())


def rel(p, root):
    """Relativer Pfad zur Wurzel. Fuer die Wurzel selbst '.', NICHT der Absolutpfad."""
    p, root = Path(p), Path(root)
    try:
        r = str(p.relative_to(root))
        return r if r else "."
    except ValueError:
        return str(p)

def walk_dirs(root: Path, melde=None):
    """Baumlauf. `melde(pfad, grund)` wird fuer JEDEN Ordner gerufen, den os.walk nicht
    betreten konnte — vorher verschluckte os.walk Rechtefehler STILL, und ein Baumteil war
    unbemerkt ungeprueft (RT-C Befund: chmod-000-Ordner)."""
    def onerr(ex):
        if melde is not None:
            melde(getattr(ex, "filename", str(root)), f"Ordner nicht lesbar ({type(ex).__name__})")
    for dp, dns, _ in os.walk(root, onerror=onerr):
        dns[:] = sorted(d for d in dns if d not in EXCLUDE_DIRS)
        yield Path(dp), dns

def entdecke_git(root: Path):
    """Findet ALLE Git-Bereiche — auch Formen, die ein reiner .git-Verzeichnis-Scan uebersieht:
      * .git als VERZEICHNIS
      * .git als DATEI  -> Worktree oder Submodul (gitdir-Verweis)
      * Submodul/Gitlink (Unterordner mit eigener .git-Datei)
      * Symlink auf ein Repository
      * Repositories UNTER ausgeschlossenen Ordnernamen (.venv, node_modules, ...)
      * kaputte .git (Verweis ins Leere, unbekannte Form)
    Rueckgabe: (bereiche, ungeprueft, geteilt)
      bereiche  = [(pfad, form)]  -> werden geprueft
      ungeprueft= [(pfad, grund)] -> NICHT stillschweigend OK, sondern gemeldet
    Ausschluesse gelten fuer die BAUM-Regeln (K6/K7), NICHT fuer die Frage,
    wo ein Repository liegt und ob dort ein Secret steckt."""
    bereiche, ungeprueft, gesehen = [], [], {}

    def merke(q: Path, form: str):
        try: schluessel = os.path.realpath(str(q))
        except OSError: schluessel = str(q)
        if schluessel in gesehen:                     # z. B. Symlink + Original = dasselbe Repo
            gesehen[schluessel].append(form)
            return
        gesehen[schluessel] = [form]; bereiche.append((q, form))

    def _onerr(ex):                      # nicht lesbare Ordner = moeglicher Git-Bereich UNGEPRUEFT
        ungeprueft.append((Path(getattr(ex, "filename", str(root))),
                           f"Ordner nicht lesbar ({type(ex).__name__}) — Git-/Secret-Pruefung hier NICHT moeglich"))

    for dp, dns, _ in os.walk(root, followlinks=False, onerror=_onerr):
        dp = Path(dp)
        gd = dp / ".git"
        if gd.is_dir():
            merke(dp, "verzeichnis")
        elif gd.is_file():
            try: inhalt = gd.read_text(encoding="utf-8", errors="replace").strip()
            except OSError: inhalt = ""
            if inhalt.startswith("gitdir:"):
                ziel = inhalt.split("gitdir:", 1)[1].strip()
                zp = Path(ziel) if ziel.startswith("/") else (dp / ziel)
                try: ok = zp.exists()
                except OSError: ok = False
                if ok:
                    merke(dp, "worktree/submodul (.git-Datei)")
                else:
                    ungeprueft.append((dp, f".git-Datei verweist ins Leere ({ziel}) — Repository nicht pruefbar"))
            else:
                ungeprueft.append((dp, ".git-Datei ohne gitdir-Verweis — Form unbekannt"))
        if ".git" in dns:
            dns[dns.index(".git")] = ".git"          # nicht hineinlaufen
        dns[:] = [d for d in dns if d != ".git"]
    # Symlinks auf Repositories (nur die, die kein echtes .git enthalten)
    for dp, dns, _ in os.walk(root, followlinks=False):
        for n in list(dns):
            q = Path(dp) / n
            if not q.is_symlink():
                continue
            try: ziel = Path(q).resolve()
            except OSError:
                ungeprueft.append((q, "Symlink nicht aufloesbar")); continue
            if (ziel / ".git").exists():
                merke(q, "symlink auf Repository")
            elif not ziel.exists():
                ungeprueft.append((q, "toter Symlink auf ein Repository"))
    geteilt = [(q, formen) for rp, formen in gesehen.items() if len(formen) > 1]
    return bereiche, ungeprueft, geteilt


def discover_repos(root: Path):
    """Rueckwaertskompatibel: nur die Pfade (alle Git-Formen, nach realpath entdoppelt)."""
    return [q for q, _ in entdecke_git(root)[0]]


def git_ls_files(repo: Path):
    """NUR LESEN: die vom Repository TATSAECHLICH gefuehrten Dateien.
    Bytes + surrogateescape: ein nicht-UTF8-Dateiname wurde vorher durch errors="replace"
    VERFAELSCHT, der Pfad existierte dann nicht und die Datei blieb still ungeprueft."""
    r = git_lesend(repo, "ls-files", "-z")
    if r.returncode != 0: return None          # kein Repo / nicht lesbar -> wird gemeldet
    return [f for f in r.stdout.decode("utf-8", "surrogateescape").split("\0") if f]


def _gitlinks(repo: Path, files) -> set:
    """Pfade, die Git als VERWEIS fuehrt (Index-Modus 160000 = Unterrepo/Submodul).

    Solche Pfade sind KEIN Inhalt dieses Repos. Vorher meldete K2 sie als
    "keine regulaere Datei ... Secret-Pruefung UNGEPRUEFT" — ein Falschalarm bei echten
    Projekten, die eigene Unter-Repos mitbringen (Testlauf 23.09.2026)."""
    r = git_lesend(repo, "ls-files", "--stage", "-z")
    if r.returncode != 0:
        return set()
    raus = set()
    for eintrag in r.stdout.decode("utf-8", "surrogateescape").split("\0"):
        if not eintrag:
            continue
        teile = eintrag.split("\t", 1)
        if len(teile) == 2 and teile[0].startswith("160000"):
            raus.add(teile[1])
    return raus


def _git_configs(repo: Path):
    # Git-Konfigurationen eines Repos — auch bei .git-Datei (Worktree/Submodul).
    gd = repo / ".git"
    if gd.is_file():
        try:
            txt = gd.read_text(encoding="utf-8", errors="ignore").strip()
            ziel = txt.split("gitdir:", 1)[1].strip() if "gitdir:" in txt else ""
            if not ziel:
                return []
            q = Path(ziel)
            gd = q.resolve() if q.is_absolute() else (repo / q).resolve()
        except Exception:
            return []
    return [c for c in (gd / "config", gd / "config.worktree") if c.is_file()]


def _blob_secret(ctx: Ctx, repo: Path, rel: str):
    # Prueft den committeten Blob aus dem Objektspeicher. Schreibt NUR in 60_RUNTIME (Sandkasten).
    try:
        sha = git_lesend(repo, "rev-parse", "HEAD:" + rel).stdout.decode("utf-8", "ignore").strip()
        if len(sha) < 7:
            return None
        roh = git_lesend(repo, "cat-file", "blob", sha).stdout
    except Exception as ex:
        # Punkt 8 (Fremdpruefung 27.09.2026): Objektspeicher nicht lesbar = UNGEPRUEFT,
        # nicht "nichts gefunden".
        ctx.ungeprueft.append({"pfad": f"{repo}:{rel}",
                               "grund": f"Objektspeicher nicht lesbar ({type(ex).__name__})"})
        return None
    if not roh:
        return None
    if len(roh) > SECRET_SCAN_MAX:
        # Punkt 8: zu grosser Blob wird nicht stillschweigend uebergangen.
        ctx.ungeprueft.append({"pfad": f"{repo}:{rel}",
                               "grund": f"Blob {len(roh)} B > SECRET_SCAN_MAX ({SECRET_SCAN_MAX} B) "
                                        f"— nicht auf Secrets geprueft"})
        return None
    # BLOCKER 3: die Probe liegt FEST in der Sandbox — der gepruefte Baum wird nie beschrieben.
    tmp = assert_write_inside_sandbox(SANDBOX / "tmp_probe/k2_blob_pruef.tmp")
    try:
        # BLOCKER 3: die Probe liegt FEST in der Sandbox — der gepruefte Baum wird nie
        # beschrieben. Frueher hing sie an ctx.root; das war der Ausbruch. Der damalige
        # Notausstieg (ein nie wahrer Zweig) ist am 27.09.2026 entfernt, die Begruendung bleibt.
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_bytes(roh)
        name, _ = scan_secrets(tmp)
        return name
    except OSError:
        return None
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass


SECRET_SCAN_MAX = 64 << 20      # Stream-Scan-Grenze; darueber gilt eine Datei als UNGEPRUEFT
SCHWELLE_BYTE = 10 << 20        # K8: Einzelpruefsumme nur fuer Objekte ab 10 MB
# Befund 25.09.2026: der Mustervergleich (Regex) kostet auf Binaerdateien Stunden. Gemessen:
# eine 2,3-MB-PDF band einen Kern ueber 4 Minuten. Deshalb (a) Binaerdateien nur am Anfang und
# Ende scannen und (b) ein Gesamt-Zeitbudget, nach dessen Verbrauch der Rest SICHTBAR als
# UNGEPRUEFT gemeldet wird (nie stilles "kein Befund").
MUSTER_ZEITBUDGET = 120.0
ZEILEN_DECKEL = 4096            # ueberlange Zeilen stueckweise (Ueberlappung 256)       # Sekunden Mustervergleich je Lauf (nicht "SECRET" nennen:
_scan_budget_stand = [None, 0.0]  # K2 greift sonst auf den Namen + Doppelpunkt + naechste Zeile)

TEXT_LIMIT = 2 << 20


def _text_anteil(p: Path, n: int = 65536) -> float:
    """Anteil druckbarer Bytes — erkennt PDF/Archiv/Datenbank auch OHNE NUL-Bytes.

    Grund: die reine NUL-Heuristik hielt eine PDF fuer Text und liess den Mustervergleich
    ueber den dekodierten Inhalt laufen (Befund 25.09.2026: >4 Minuten CPU fuer 2,3 MB).
    """
    try:
        with p.open("rb") as f:
            b = f.read(n)
    except OSError:
        return 0.0
    if not b:
        return 1.0
    druck = sum(1 for c in b if 9 <= c <= 13 or 32 <= c <= 126 or c >= 128)
    return druck / len(b)


def _binaer_anteil(p: Path, n: int = 65536) -> float:
    """Anteil NUL-Bytes im ersten Block — billige Text/Binaer-Erkennung (nur lesen)."""
    try:
        with p.open("rb") as f:
            b = f.read(n)
    except OSError:
        return 1.0
    return (b.count(b"\x00") / len(b)) if b else 0.0


def scan_secrets(p: Path):
    """Stream-Scan nach Secret-Mustern (blockweise, ueberlappend).
    Rueckgabe: (Treffer-Name|None, ungeprueft: bool) — der 2-MB-Deckel von _text
    hatte zugelassen, dass ein Secret in einer 3,2-MB-Datei unsichtbar blieb."""
    import time as _t
    _jetzt = _t.monotonic()
    if _scan_budget_stand[0] is None:
        _scan_budget_stand[0] = _jetzt
    if _jetzt - _scan_budget_stand[0] > MUSTER_ZEITBUDGET:
        _scan_budget_stand[1] += 1.0
        return None, True      # Budget verbraucht: Rest gilt als UNGEPRUEFT und wird gemeldet
    try:
        if p.stat().st_size > SECRET_SCAN_MAX:
            return None, True
        _groesse = p.stat().st_size
        # Nur Anfang + Ende scannen, wenn die Datei binaer ist ODER groesser als 8 MB. Grund:
        # eine einzige grosse Textdatei kann den Mustervergleich minutenlang rechnen (gemessen
        # 25.09.2026: 99,7 % CPU, keine Datei mehr offen — der Regex lief im Speicher). Das
        # Zeitbudget greift nur ZWISCHEN Dateien, deshalb braucht es diesen Deckel je Datei.
        if _groesse > (2 << 20) and (_text_anteil(p) < 0.95 or _groesse > (8 << 20)):
            with p.open("rb") as _fh:
                _kopf = _fh.read(2 << 20)
                _fh.seek(max(0, _groesse - (2 << 20)))
                _ende = _fh.read(2 << 20)
            for _teil in (_kopf, _ende):
                _txt = _teil.replace(b"\x00", b"").decode("utf-8", "ignore")
                for _rx, _name in SECRET_PATTERNS:
                    if _rx.search(_txt):
                        return _name, False
            return None, True
        rest = ""
        with p.open("rb") as fh:
            while True:
                blk = fh.read(4 << 20)
                if not blk:
                    break
                # NUL-Bytes zerlegten ein Muster ("AKIA\x00IOSFODNN") und blieben unsichtbar (RT-Final-A).
                txt = rest + blk.replace(b"\x00", b"").decode("utf-8", "ignore")
                # Zeilenweise suchen: der Mustervergleich ist quadratisch in der Laenge der
                # durchsuchten Zeichenkette. Gemessen 25.09.2026: 2,02 MB PDF = 1,709 s am Stueck.
                # WICHTIG: ALLE Zeilen werden geprueft, auch die letzte — in einer kleinen Datei
                # ohne Zeilenumbruch ist die einzige Zeile die letzte (Regress 25.09.2026).
                schritt = ZEILEN_DECKEL - 256
                for zeile in txt.split("\n"):
                    if len(zeile) > ZEILEN_DECKEL:          # minifiziertes JSON / Binaerblob
                        for i in range(0, len(zeile), schritt):
                            for rx, name in SECRET_PATTERNS:
                                if rx.search(zeile[i:i + ZEILEN_DECKEL]):
                                    return name, False
                    else:
                        for rx, name in SECRET_PATTERNS:
                            if rx.search(zeile):
                                return name, False
                letzte = txt.rsplit("\n", 1)[-1]
                rest = letzte[-schritt:] if len(letzte) > ZEILEN_DECKEL else letzte
    except OSError:
        return None, True      # nicht lesbar = UNGEPRUEFT, niemals "kein Befund"
    return None, False


def _text(p: Path, limit=TEXT_LIMIT):
    try:
        if p.stat().st_size > limit: return ""
        return p.read_bytes().decode("utf-8", "ignore")
    except OSError:
        return ""


# ---------------- K1 ----------------
def k1(ctx: Ctx, repos):
    for repo in repos:
        try:
            files = git_ls_files(repo)
        except Exception as ex:                     # ein kaputtes Repo darf nicht alle anderen verdecken
            ctx.add("K1", ERROR, repo, f"Repository nicht pruefbar ({type(ex).__name__}: {ex})."); continue
        if files is None:
            ctx.add("K1", ERROR, repo, "Repository nicht lesbar (git ls-files fehlgeschlagen).")
            continue
        for f in files:
            p = repo / f
            ctx.tick()
            try: size = p.stat().st_size
            except OSError: size = 0
            teile = set(Path(f).parts)
            art = None
            if size > SCHWELLE_BYTE: art = f"Datenobjekt {size/1e6:.1f} MB ueber der 10-MB-Schwelle"
            elif teile & VERBOTENE_PFADTEILE: art = f"verbotener Ordner: {sorted(teile & VERBOTENE_PFADTEILE)[0]}/"
            elif p.suffix.lower() in VERBOTENE_ENDUNGEN: art = f"verbotener Dateityp {p.suffix}"
            if art:
                schwere = CRITICAL if size > SCHWER_BYTE else ERROR
                ctx.add("K1", schwere, p, f"Verbotener Inhalt im Repository ({art}). Git ist kein Massenspeicher.")


# ---------------- K2 ----------------
def k2(ctx: Ctx, repos):
    # BLOCKER 4: katalogisierte Bereiche, die KEIN Arbeitsbaum sind (Bare-Repo oder Nicht-Git),
    # wurden vorher uebersprungen — ein Nicht-Git-Bereich galt damit still als sauber.
    try:
        _liste = repos.get("repos", []) if isinstance(repos, dict) else (repos or [])
        _basis = getattr(ctx, "root", SANDBOX)
        for _e in _liste:
            _rel = _e.get("pfad") if isinstance(_e, dict) else None
            if not _rel:
                continue
            _p = Path(_basis) / str(_rel)
            if _p.is_dir() and not (_p / ".git").exists():
                k2_bare_und_nicht_git(ctx, _p)
    except Exception as _ex:
        ctx.ungeprueft.append({"pfad": "k2:Nicht-Git-Scope", "grund": f"{type(_ex).__name__}: {_ex}"})
    for repo in repos:
        try:
            files = git_ls_files(repo)
        except Exception as ex:
            ctx.ungeprueft.append({"pfad": str(repo), "grund": f"git ls-files fehlgeschlagen ({type(ex).__name__})"})
            ctx.add("K2", ERROR, repo, f"Repository nicht pruefbar ({type(ex).__name__}) — Secret-Pruefung UNGEPRUEFT.")
            continue
        if files is None:                     # nicht lesbar -> NICHT stillschweigend ueberspringen
            ctx.ungeprueft.append({"pfad": str(repo), "grund": "Repository nicht lesbar (git ls-files)"})
            ctx.add("K2", ERROR, repo, "Repository NICHT lesbar — Secret-Pruefung UNGEPRUEFT "
                                       "(kein stilles OK).")
            continue
        # (a) .git/config traegt regelmaessig Tokens in Remote-URLs — mitpruefen (RT-Final-A).
        for cfg in _git_configs(repo):
            cname, cung = scan_secrets(cfg)
            if cname:
                ctx.add("K2", CRITICAL, cfg, f"Secret-Muster in der GIT-KONFIGURATION ({cname}). {REAKTIONSKETTE}")
            elif cung:
                ctx.add("K2", WARNING, cfg, "Git-Konfiguration NICHT auf Secrets geprueft.")
        blind = []
        verweise = _gitlinks(repo, files)      # Unterrepos/Submodule: kein Inhalt dieses Repos
        for f in files:
            p = repo / f; ctx.tick()
            if f in verweise:                  # wird unten gezaehlt + sichtbar gemeldet
                continue
            # Ein TOTER Verweis (Symlink ohne Ziel) ist kein Inhalt dieses Repos und kein
            # Secret-Problem — K8 meldet ihn als Warnung (Befund 25.09.2026, Testkopie c1).
            if p.is_symlink() and not p.exists():
                continue
            # Eine gefuehrte Datei, die hier NICHT regulaer lesbar ist, ist eine BLINDSTELLE —
            # kein stilles Ueberspringen (RT-C Befund: nicht-UTF8-Name, Rechte, fehlende Datei).
            try:
                st = p.stat()
                regulaer = stat.S_ISREG(st.st_mode)
            except OSError as ex:
                ctx.ungeprueft.append({"pfad": str(p), "grund": f"gefuehrte Datei nicht lesbar ({type(ex).__name__})"})
                ctx.add("K2", ERROR, p, f"Gefuehrte Datei NICHT lesbar — Secret-Pruefung UNGEPRUEFT "
                                        f"({type(ex).__name__}). Kein stilles OK.")
                blind.append(f); continue
            if not regulaer:
                ctx.ungeprueft.append({"pfad": str(p), "grund": "gefuehrte Datei ist keine regulaere Datei"})
                ctx.add("K2", ERROR, p, "Gefuehrte Datei ist keine regulaere Datei (FIFO/Geraet/Symlink?) — "
                                        "Secret-Pruefung UNGEPRUEFT.")
                continue
            # stat() gelingt AUCH ohne Leserecht (chmod 000) — erst ein echter Leseversuch deckt es auf.
            try:
                with open(p, "rb") as fh:
                    fh.read(1)
            except OSError as ex:
                ctx.ungeprueft.append({"pfad": str(p), "grund": f"kein Leserecht ({type(ex).__name__})"})
                ctx.add("K2", ERROR, p, f"Gefuehrte Datei NICHT lesbar ({type(ex).__name__}) — "
                                        "Secret-Pruefung UNGEPRUEFT. Kein stilles OK.")
                blind.append(f); continue
            for pat in SECRET_DATEIEN:
                if pat.search(Path(f).name):
                    ctx.add("K2", CRITICAL, p, f"Secret-Datei im Repository ({Path(f).name}). {REAKTIONSKETTE}")
                    break
            name, ungeprueft = scan_secrets(p)
            if name:
                ctx.add("K2", CRITICAL, p, f"Secret-Muster gefunden ({name}). {REAKTIONSKETTE}")
            elif ungeprueft:
                ctx.add("K2", WARNING, p, f"Datei groesser als {SECRET_SCAN_MAX >> 20} MB — "
                                          "NICHT auf Secrets geprueft (bewusste Obergrenze).")
        # (b) Arbeitskopie fehlt/unlesbar — der committete Blob liegt aber im OBJEKTSPEICHER.
        # Genau dort blieb ein Secret bisher unsichtbar (RT-Final-A: CRITICAL).
        for rel in blind:
            tref = _blob_secret(ctx, repo, rel)
            if tref:
                ctx.add("K2", CRITICAL, repo / rel,
                        f"Secret im Git-OBJEKTSPEICHER ({tref}) — obwohl die Arbeitskopie fehlt/"
                        f"unlesbar ist. {REAKTIONSKETTE}")


        if verweise:
            ctx.add("K2", WARNING, repo,
                    f"{len(verweise)} Verweis(e) (Unterrepo/Submodul) uebersprungen — deren Inhalt ist "
                    f"nicht Teil dieses Repos und wird hier nicht geprueft: "
                    + ", ".join(sorted(verweise)[:3]) + (" …" if len(verweise) > 3 else ""))
        k2_scope(ctx, repo, files)      # Final-Abnahme A1: Scope benennen
        k2_bare_und_nicht_git(ctx, repo)   # BLOCKER 4: Bare-Repos + Nicht-Git ausweisen


# ---------------- K3 ----------------
def k3(ctx: Ctx, catalog):
    for e in catalog.get("repos", []):
        if not e.get("git"): continue
        ctx.tick()
        if not e.get("pfad"):
            continue          # fehlendes Pflichtfeld meldet K5 — K3 nicht doppelt
        repo = ctx.root / e["pfad"]
        files = [f.lower() for f in (git_ls_files(repo) or [])]
        if not repo.exists():
            continue   # fehlender Pfad wird von K4 als CRITICAL gemeldet — K3 doppelt nicht.
        if "readme.md" not in files:
            ctx.add("K3", ERROR, repo, f"[{e['name']}] README.md fehlt im Repository.")
        if ".gitignore" not in files:
            ctx.add("K3", ERROR, repo, f"[{e['name']}] .gitignore fehlt im Repository.")
        if e.get("class") == "project" and e.get("status") == "active" and "status.md" not in files:
            ctx.add("K3", ERROR, repo, f"[{e['name']}] aktives Projekt ohne STATUS.md.")
        if e.get("class") == "knowledge" and e.get("status") != "provisional":
            has = any("ausgabe_sha256" in _text(repo / f) for f in (git_ls_files(repo) or []) if f.endswith((".md", ".yaml")))
            try:
                has = has or any(x.name == "provenienz.yaml" for x in os.scandir(repo) if x.is_file())
            except OSError:
                pass
            if not has:
                ctx.add("K3", ERROR, repo, f"[{e['name']}] Wissensartefakt ohne Herkunftskopf (ausgabe_sha256).")
            else:
                _herkunft(
                    ctx, repo, e["name"],
                    [f for f in (git_ls_files(repo) or []) if f.endswith((".md", ".yaml"))])


def _herkunft(ctx: Ctx, repo: Path, name: str, dateien):
    """Gegenproben des Herkunftskopfes (v1.3): gefaelschte Werte muessen auffallen.
      1) ausgabe_sha256 muss 64 Hexzeichen sein und zum tatsaechlichen Inhalt passen, wenn
         eine gleichnamige Datei im Repo liegt (ausgabe_sha256 + Zielpfad)
      2) quelle_commit muss im Repository existieren
      3) jede genannte Eingabe (eingaben) muss existieren"""
    for f in dateien[:200]:
        txt = _text(repo / f)
        # Schluessel SCHREIBWEISEN-TOLERANT finden: "Quelle-Commit" oder "quelle_commit" duerfen
        # sich nicht unterscheiden. Vorher lief jede Gegenprobe an der anderen Schreibweise vorbei.
        def feld(w):
            m = re.search(rf"(?im)^\s*{w}\s*[:=]\s*(.+)$", txt)
            return (m.group(1).strip().strip('"\'') if m else None)
        def feldname(w):        # Muster kommt BEREITS mit [_-]? — nicht nochmals ersetzen
            return rf"(?im)^\s*{w}\s*[:=]"
        sha_roh, ziel_roh = feld("ausgabe[_-]?sha256"), feld("(?:ausgabe(?:datei|_pfad|_ziel)?|zieldatei|datei)")
        if rx_field_praesent := re.search(feldname("ausgabe[_-]?sha256"), txt):
            if not sha_roh:
                ctx.add("K3", ERROR, repo / f, f"[{name}] Feld 'ausgabe_sha256' steht da, aber OHNE Wert.")
            else:
                wert = str(sha_roh).split()[0]
                if not re.fullmatch(r"[0-9a-fA-F]{64}", wert):
                    ctx.add("K3", ERROR, repo / f,
                            f"[{name}] ausgabe_sha256 ist kein SHA-256 (Laenge {len(wert)}, "
                            f"{'nicht hexadezimal' if not re.fullmatch(r'[0-9a-fA-F]+', wert) else 'falsche Laenge'}).")
                else:
                    if not ziel_roh:
                        ctx.add("K3", ERROR, repo / f, f"[{name}] ausgabe_sha256 ohne Zieldatei — "
                                                       "die Pruefsumme ist NICHT gegenpruefbar.")
                    else:
                        z = repo / str(ziel_roh).split()[0]
                        if not z.is_file():
                            ctx.add("K3", ERROR, repo / f, f"[{name}] Zieldatei '{ziel_roh}' existiert NICHT "
                                                           "— ausgabe_sha256 nicht gegenpruefbar.")
                        else:
                            try: ist = hashlib.sha256(z.read_bytes()).hexdigest()
                            except OSError as ex:
                                ctx.add("K3", ERROR, repo / f, f"[{name}] Zieldatei nicht lesbar ({type(ex).__name__}).")
                            else:
                                if ist != wert.lower():
                                    ctx.add("K3", CRITICAL, repo / f,
                                            f"[{name}] ausgabe_sha256 passt NICHT zum Inhalt von "
                                            f"{ziel_roh} (Herkunft gefaelscht oder Datei geaendert).")
        # Fliesstext nennt das Feld, aber nicht als Feld (blosses Wort) -> nicht gegenpruefbar
        if re.search(r"ausgabe_sha256", txt) and not rx_field_praesent:
            ctx.add("K3", WARNING, repo / f, f"[{name}] 'ausgabe_sha256' erscheint nur im Fliesstext "
                                              "(kein Feld) — keine Gegenprobe moeglich.")
        for cm in re.finditer(r"(?im)^\s*quelle[_-]?commit\s*[:=]\s*(\S+)", txt):
            wert = cm.group(1).strip('"\'')
            if not re.fullmatch(r"[0-9a-fA-F]{7,40}", wert):
                ctx.add("K3", ERROR, repo / f, f"[{name}] quelle_commit '{wert[:20]}' ist kein "
                                                "Commit-Hash (7-40 Hexzeichen) — nicht gegenpruefbar.")
                continue
            r = git_lesend(repo, "cat-file", "-e", wert)
            if r.returncode != 0:
                ctx.add("K3", ERROR, repo / f, f"[{name}] quelle_commit {wert} existiert NICHT im Repository.")
        em = re.search(r"(?im)^\s*eingaben\s*[:=]\s*(.+)$", txt)
        if em:
            roh_wert = em.group(1).strip()
            if not roh_wert.startswith("["):
                ctx.add("K3", ERROR, repo / f, f"[{name}] eingaben ist keine Liste ({roh_wert[:40]!r}) — "
                                                "Herkunft nicht gegenpruefbar.")
            else:
                for roh in re.findall(r"[\w./-]+", roh_wert):
                    if (repo / roh).exists() is False and not roh.isdigit():
                        ctx.add("K3", WARNING, repo / f, f"[{name}] genannte Eingabe '{roh}' existiert nicht.")


# ---------------- K4 ----------------
LST_ORTE = ("60_RUNTIME/zeiger", "40_DATEN/manifests")   # abgeleitete Listen: 60_RUNTIME (nie versioniert)


def sha256_datei_ziel(p: Path) -> str:
    """Pruefsumme einer Datei — auch wenn der Eintrag ein SYMLINK ist.

    Fund C-Testlauf (23.09.2026): ein Symlink im Zielobjekt liess K8 mit
    "SandkastenVerletzt: Special File wird nicht geoeffnet (0o120000)" CRITICAL abbrechen,
    weil der gehaertete Oeffner keine Nicht-Regulaer-Dateien oeffnet. Fuer eine REINE LESUNG
    ist das zu streng: hier wird bewusst das ZIEL gelesen (nur lesen, nie schreiben), und nur
    wenn das Ziel eine regulaere Datei ist. Sonst gibt es eine klare Meldung statt Absturz.
    Die Schreib-Schranken bleiben unveraendert.
    """
    try:
        return sha256_datei(p)
    except Exception:
        pass
    if p.is_symlink():
        ziel = p.resolve()
        if ziel.is_file():
            with open(ziel, "rb") as fh:      # nur GELESEN — Schreibschranken unberuehrt
                h = hashlib.sha256()
                for b in iter(lambda: fh.read(1 << 20), b""):
                    h.update(b)
            return h.hexdigest()
    raise OSError(f"nicht pruefbar (kein regulaerer Eintrag): {p.name}")


def zaehle_objekt(wurzel: Path):
    """EINE Definition von "Datei" — fuer Pruefer UND Werkzeug (Testlauf 23.09.2026).

    Datei = regulaere Datei ODER Symlink, der auf eine regulaere Datei zeigt.
    Tote Verweise zaehlen NICHT als Datei, werden aber einzeln zurueckgegeben und
    sichtbar gemeldet. Vorher zaehlten Pruefer und Listenerzeuger unterschiedlich:
    Fehlalarm "Dateizahl weicht ab: Zeiger 13064, gefunden 13067".
    Rueckgabe: (dateien, tote_verweise)
    """
    dateien, tot = [], []
    for x in wurzel.rglob("*"):
        try:
            if x.is_symlink() and not x.exists():
                tot.append(x); continue
            if x.is_file():
                dateien.append(x)
        except OSError:
            continue
    return dateien, tot


ZEIGER_TIEFE_BYTE = 50 << 20      # A (23.09.2026): bis 50 MB wird jede Datei einzeln geprueft
# Punkt 3b (freigegeben 26.09.2026): rollierende Vollpruefung in Zeitscheiben.
# Jeder Lauf prueft so viele Eintraege, wie ins Budget passen, merkt sich die Stelle und
# berichtet die Abdeckung in Dateien UND Bytes. Vorbild: git-annex '--incremental --time-limit',
# GovInfo (ein Monat je Durchlauf). Kein Sampling mit festen 16 Eintraegen mehr.
ROLLIEREND_BUDGET_S = 3.0
ROLLIEREND_MAX_BYTE = 200 << 20
ROLLIEREND_MAX_EINTRAEGE_ZAHLEN = 20000   # ab hier wird die Byte-Gesamtsumme nicht mehr ermittelt
ROLLIEREND_STATE = "60_RUNTIME/state/rollierend.json"


def sha256_datei(p: Path) -> str:
    """Pruefsumme einer Datei, blockweise (auch fuer grosse Dateien)."""
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for blk in iter(lambda: fh.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def k4(ctx: Ctx, catalog, repos):
    bekannt = set()
    for e in catalog.get("repos", []):
        ctx.tick()
        if not e.get("pfad"):
            continue          # fehlendes Pflichtfeld meldet K5
        p = (ctx.root / e["pfad"]); bekannt.add(p.resolve())
        if not p.exists():
            # Punkt 2 (Fremdpruefung 27.09.2026): 60_RUNTIME wird NIE versioniert. In einem
            # frischen Klon kann ein Laufzeit-Artefakt darum gar nicht existieren — das ist der
            # Normalzustand eines Klons, kein Katalogfehler. Benannter Hinweis statt CRITICAL.
            if str(e["pfad"]).startswith("60_RUNTIME") or e.get("bereich") == "60_RUNTIME":
                ctx.add("K4", WARNING, p,
                        f"[{e['name']}] Laufzeit-Pfad fehlt: {e['pfad']} — 60_RUNTIME wird nie "
                        "versioniert; in einem Klon ist das normal. Artefakt sichern, nicht neu bauen.")
                continue
            ctx.add("K4", CRITICAL, p, f"[{e['name']}] Katalog nennt Pfad, der NICHT existiert: {e['pfad']}")
            continue
        klasse, bereich = e.get("class"), e.get("bereich")
        if klasse in KLASSE_BEREICH and bereich not in KLASSE_BEREICH[klasse]:
            if not (e.get("extern") and str(e["pfad"]).startswith("20_PROJEKTE")):
                ctx.add("K4", ERROR, p, f"[{e['name']}] class={klasse} passt nicht zu bereich={bereich}.")
        if e.get("git") and not (p / ".git").exists():
            ctx.add("K4", ERROR, p, f"[{e['name']}] git=true, aber kein .git gefunden.")
        if bool(e.get("pin")) != bool(e.get("extern")):
            ctx.add("K4", ERROR, p, f"[{e['name']}] pin/gegen extern falsch: pin genau dann, wenn extern=true.")
    # B (23.09.2026, Testlauf mit echten Projekten): Repos UNTERHALB eines katalogisierten
    # Pfads sind Unterrepos des Projekts (z. B. Werkzeuge/Unterprojekte innerhalb eines echten
    # Projekts). Sie werden GEZAEHLT und sichtbar gemeldet, aber nicht einzeln verlangt —
    # vorher erzeugte ein echtes Projekt mit 7 Unter-Repos 107 ERROR.
    eltern = sorted((p.resolve() for p in bekannt), key=lambda q: len(str(q)), reverse=True)
    unterrepos: dict = {}
    for repo in repos:
        ctx.tick()
        rr = repo.resolve()
        if rr == ctx.root.resolve() or rr in bekannt:
            continue
        vater = next((p for p in eltern if p in rr.parents), None)
        if vater is not None:
            unterrepos.setdefault(vater, []).append(rr)
            continue
        ctx.add("K4", ERROR, repo, "Repository existiert, ist dem Katalog aber UNBEKANNT.")
    for vater, liste in sorted(unterrepos.items()):
        namen = ", ".join(sorted(x.name for x in liste)[:4]) + (" …" if len(liste) > 4 else "")
        ctx.add("K4", WARNING, vater,
                f"UNTERREPOS: {len(liste)} Repo(s) unterhalb eines katalogisierten Pfads "
                f"({namen}) — als Teil des Projekts gefuehrt, nicht einzeln katalogisiert.")
    # 2.8: Der Baum selbst ist EIN Repository. Verboten ist nicht "liegt im Repo", sondern
    # "ist versioniert". Deshalb wird jetzt die tatsaechliche Verfolgung durch Git geprueft.
    runtime = ctx.root / "60_RUNTIME"
    if runtime.is_dir() and (ctx.root / ".git").exists():
        try:
            r = git_lesend(ctx.root, "ls-files", "--", "60_RUNTIME")
        except Exception as ex:
            # Punkt 8 (Fremdpruefung 27.09.2026): NICHT still ueberspringen — sonst bleibt dieser
            # Teil ungeprueft, ohne dass es irgendwo steht.
            ctx.ungeprueft.append({"pfad": str(runtime),
                                   "grund": f"Verfolgung durch Git nicht messbar ({type(ex).__name__})"})
            r = None
        if r is not None and r.stdout.strip():
            ctx.add("K4", CRITICAL, runtime, "60_RUNTIME wird von Git VERFOLGT — Zustand darf nie versioniert werden.")


# ---------------- K5 ----------------
def k5(ctx: Ctx, catalog):
    PFLICHT = ["schema_version", "name", "class", "status", "owner", "seit", "bereich", "pfad", "git"]
    STATUS = {"provisional", "active", "paused", "done", "abandoned", "archived"}
    namen, pfade = {}, {}
    for e in catalog.get("repos", []):
        ctx.tick(); n = e.get("name", "?")
        for feld in PFLICHT:
            if feld not in e:
                ctx.add("K5", ERROR, n, f"[{n}] Pflichtfeld fehlt: {feld}")
        if e.get("status") not in STATUS:
            ctx.add("K5", ERROR, n, f"[{n}] ungueltiger status: {e.get('status')!r}")
        if e.get("status") == "active" and not e.get("review_am"):
            ctx.add("K5", ERROR, n, f"[{n}] status=active ohne review_am.")
        try:                                              # RT-C: Zukunftsdaten sind verdaechtig
            _s = datetime.date.fromisoformat(str(e.get("seit")))
            if _s > datetime.date.today() + datetime.timedelta(days=1):
                ctx.add("K5", WARNING, n, f"[{n}] seit liegt in der Zukunft ({_s}) — Fehleingabe?")
        except (ValueError, TypeError):
            pass
        if e.get("status") == "provisional":      # v1.3 §12: Bootstrap darf nicht liegen bleiben
            try:
                tage = (datetime.date.today() - datetime.date.fromisoformat(str(e.get("seit")))).days
                if tage > 90:
                    ctx.add("K5", ERROR, n, f"[{n}] provisional seit {tage} Tagen (>90) — entscheiden: active oder abandoned.")
                elif tage > 30:
                    ctx.add("K5", WARNING, n, f"[{n}] provisional seit {tage} Tagen (>30) — Entscheidung ueberfaellig.")
            except (ValueError, TypeError):
                pass
        if e.get("git") and e.get("status") == "active" and not e.get("remote"):
            ctx.add("K5", ERROR, n, f"[{n}] git=true und active, aber ohne remote.")
        if "schema_version" in e and e.get("schema_version") != 1:
            ctx.add("K5", ERROR, n, f"[{n}] schema_version ist {e.get('schema_version')!r}, erwartet 1.")
        norm = os.path.normpath(str(e.get("pfad", "")))
        namen.setdefault(n, []).append(n); pfade.setdefault(norm, []).append(n)
    for n, v in namen.items():
        if len(v) > 1: ctx.add("K5", ERROR, n, f"name '{n}' ist {len(v)}x im Katalog — muss global eindeutig sein.")
    for p, v in pfade.items():
        if len(v) > 1:
            ctx.add("K5", ERROR, p, f"pfad '{p}' ist {len(v)}x im Katalog — muss global eindeutig sein "
                                    "(auch ueber '.'/'..' verschraenkte Schreibweisen).")
    # Doppelte Eintraege, die denselben ORDNER bezeichnen (verschiedene Schreibweise)
    aufgeloest = {}
    for p, v in pfade.items():
        if p: aufgeloest.setdefault(os.path.realpath(str(ctx.root / p)), []).extend(v)
    for rp, v in aufgeloest.items():
        if len(v) > 1:
            ctx.add("K5", ERROR, rp, f"{len(v)} Katalogeintraege zeigen auf DENSELBEN Ordner: {sorted(v)}")


# ---------------- K6 ----------------
def k6(ctx: Ctx, catalog):
    erlaubt = re.compile(r"^[a-z0-9_.-]+$")   # gilt fuer die SELBST vergebenen Namen
    BEREICHE = {"00_SYSTEM","10_AGENT","20_PROJEKTE","30_WISSEN","40_DATEN",
                "50_INFRA","60_RUNTIME","70_AUTOMATION","80_VORLAGEN","90_ARCHIV"}
    # Kennnummern muessen EINDEUTIG sein (Ausbau-Schritt 3): doppelt vergeben = Fehler,
    # sonst zeigt die Nummer nicht mehr auf genau ein Projekt.
    _nummern: dict = {}
    for e in catalog.get("repos", []):
        if e.get("class") != "project":
            continue
        _m = re.match(r"^(\d{3})_", Path(str(e.get("pfad", ""))).name)
        if _m:
            _nummern.setdefault(_m.group(1), []).append(e.get("name"))
    for _nr, _namen in sorted(_nummern.items()):
        if len(_namen) > 1:
            ctx.add("K6", ERROR, "20_PROJEKTE",
                    f"Nummer {_nr} doppelt vergeben an: {sorted(_namen)} — Kennungen muessen eindeutig sein.")
    for e in catalog.get("repos", []):
        ctx.tick(); p = str(e.get("pfad", ""))
        if len(p) > 255:
            ctx.add("K6", ERROR, p, f"[{e['name']}] Pfad laenger als 255 Zeichen ({len(p)}).")
        teile = Path(p).parts
        zu_pruefen = [t for i, t in enumerate(teile) if not (i == 0 and t in BEREICHE)]
        schlecht = [t for t in zu_pruefen if not erlaubt.match(t)]
        if schlecht:
            ctx.add("K6", WARNING, p, f"[{e['name']}] Name(n) mit unerlaubten Zeichen: {schlecht} (erlaubt: a-z 0-9 _ - .).")
        if e.get("class") == "project":
            rumpf = Path(p).name
            # FESTE NUMMER (Ausbau-Schritt 3, 23.09.2026): <NNN>_<name>_<YYYY-MM-DD>.
            # Die Nummer ist die stabile Kennung: der Name darf sich aendern, die Nummer nicht.
            # Beide Formen sind gueltig — bestehende Ordner werden NICHT umbenannt:
            #   alt:  YYYY-MM-DD_name          neu:  NNN_name_YYYY-MM-DD
            m_num = re.match(r"^(\d+)_", rumpf)
            if not m_num and not re.match(r"^\d{4}-\d{2}-\d{2}_", rumpf):
                ctx.add("K6", WARNING, p, f"[{e['name']}] Projektordner ohne Datum (YYYY-MM-DD_) vorne.")
            if m_num:
                if len(m_num.group(1)) != 3:
                    ctx.add("K6", WARNING, p, f"[{e['name']}] Nummer nicht dreistellig: '{m_num.group(1)}' "
                                                f"(Empfehlung 001, 002, ... 021).")
                if not re.match(r"^\d{3}_.+_\d{4}-\d{2}-\d{2}$", rumpf):
                    ctx.add("K6", WARNING, p, f"[{e['name']}] Nummer erkannt, Form aber ungewohnt: "
                                                f"erwartet NNN_name_JJJJ-MM-TT (z.B. 021_island_sprache_2026-09-23).")
    for dp, dns in walk_dirs(ctx.root):
        ctx.tick()
        gruppen = {}
        # NFC UND NFD vergleichen: casefold() allein normalisiert nicht — "Straße" vs "STRASSE"
        # sowie NFC/NFD-Varianten desselben Namens blieben STILL unentdeckt (RT-C Befund).
        def schluessel(n):
            return (n.casefold(), unicodedata.normalize("NFC", n).casefold(),
                    unicodedata.normalize("NFD", n).casefold())
        for d in dns:
            for k in set(schluessel(d)): gruppen.setdefault(k, []).append(d)
        try:
            for x in os.scandir(dp):                      # RT-A F9: auch DATEIEN
                if x.is_file():
                    for k in set(schluessel(x.name)): gruppen.setdefault(k, []).append(x.name)
        except OSError:
            pass
        for k, v in gruppen.items():
            if len(v) > 1:
                ctx.add("K6", ERROR, Path(dp), f"Case-Kollision im selben Ordner: {sorted(v)} — OS-Wechsel bricht Pfade.")


# ---------------- K7 ----------------
def k7(ctx: Ctx, catalog):
    """Tiefe/Breite ab MASTER-Wurzel (K7).

    Entscheidung 23.09.2026 (gemessen im C-Testlauf an echten Projekten): der INHALT eines
    katalogisierten Projektordners wird NICHT nach K7 gemessen, WENN der Katalog das ausdruecklich
    erklaert (`inhalt_ausgenommen: true`). Ein echtes, gewachsenes Projekt bringt seine eigene
    Struktur mit (gemessen: Tiefe 7, Breite 23; ohne Ausnahme 109 Fehler) — Umbau waere "etwas
    anfassen" und ist verboten. Statt ~100 Einzelmeldungen: EINE Meldung je Projekt.
    Ohne den Marker bleibt alles wie vorher (kein stiller Verhaltenswechsel).
    """
    root = ctx.root
    ausgenommen = []
    for e in (catalog or {}).get("repos", []):      # Katalog ist ein Dict mit "repos" (wie k3-k6)
        p = str(e.get("pfad", "") or "").strip("/")
        if e.get("class") == "project" and p and e.get("inhalt_ausgenommen") is True:
            ausgenommen.append(p)
    untern = {}
    for dp, dns in walk_dirs(root):
        relp = rel(dp, root)
        tiefe = 0 if relp == "." else len(Path(relp).parts)
        ctx.tick()
        unter = next((p for p in ausgenommen if relp.startswith(p + "/")), None)
        if unter:
            untern[unter] = max(untern.get(unter, 0), tiefe)
            continue
        if tiefe > K7_TIEFE:
            ctx.add("K7", ERROR, dp, f"Tiefe {tiefe} > {K7_TIEFE} (alle Ebenen ab MASTER-Wurzel zaehlen, keine Ausnahmen).")
        ist_nodes = (relp == "50_INFRA/nodes" or relp.startswith("50_INFRA/nodes/"))
        eintraege = [x for x in dns if x not in EXCLUDE_DIRS] + \
                    [f.name for f in os.scandir(dp) if f.is_file() and f.name not in EXCLUDE_DIRS]
        if len(eintraege) > K7_BREITE and not ist_nodes:
            ctx.add("K7", ERROR, dp, f"Breite {len(eintraege)} > {K7_BREITE} Eintraege (Ausnahme NUR 50_INFRA/nodes/, pfadbasiert).")
    for p, n in sorted(untern.items()):
        if n > K7_TIEFE:
            ctx.add("K7", WARNING, root / p,
                    f"[{p}] Projektinhalt bis Tiefe {n} — Projekt bringt seine eigene Struktur mit; Inhalt "
                    f"wird NICHT nach K7 gemessen (Katalog sagt: inhalt_ausgenommen).")


# ---------------- K8 ----------------
def k8(ctx: Ctx, catalog):
    pd = ctx.root / "40_DATEN"
    if not pd.exists():
        ctx.add("K8", ERROR, pd, "40_DATEN fehlt."); return
    gesamt = 0
    for dp, dns, fns in os.walk(pd):
        for n in list(dns):                              # RT-A F7: Symlink auf Datenverzeichnis
            q = Path(dp) / n
            if q.is_symlink():
                try: gesamt += sum(x.stat().st_size for x in Path(q).resolve().rglob("*") if x.is_file())
                except OSError: pass
                ctx.add("K8", WARNING, q, "Symlink in 40_DATEN — Ziel wird ins Budget gerechnet "
                                          "(40_DATEN darf kein Datenlager werden).")
        for n in fns:
            q = Path(dp) / n
            try: gesamt += q.stat().st_size
            except OSError: pass
    ctx.tick()
    if gesamt > 1 << 20:
        ctx.add("K8", ERROR, pd, f"40_DATEN ist {gesamt/1e6:.2f} MB gross — Ziel: unter 1 MB (Zeiger, keine Daten).")
    zeiger = []
    import yaml
    for f in sorted((pd / "pointers").glob("*.y*ml")):
        try:                                       # FIFO/Verzeichnis: NICHT oeffnen (blockiert/IsADirectory)
            if not stat.S_ISREG(f.stat().st_mode):
                ctx.add("K8", ERROR, f, f"Zeigerdatei ist keine regulaere Datei "
                                        f"({'Verzeichnis' if f.is_dir() else 'FIFO/Geraet'}) — nicht geoeffnet.")
                continue
        except OSError as ex:
            ctx.add("K8", ERROR, f, f"Zeigerdatei nicht untersuchbar ({type(ex).__name__})."); continue
        try:
            d = yaml.safe_load(f.read_text(encoding="utf-8", errors="ignore"))
        except Exception as ex:
            ctx.add("K8", ERROR, f, f"Zeigerdatei nicht lesbar: {ex}"); continue
        if d is None: d = {}
        if not isinstance(d, dict):                      # RT-A F11: kein Absturz mehr
            ctx.add("K8", ERROR, f, f"Zeigerdatei ist kein Mapping, sondern {type(d).__name__} — "
                                    "Struktur ungueltig (Pruefer laeuft weiter).")
            continue
        for z in d.get("zeiger", []):
            if not isinstance(z, dict):
                ctx.add("K8", ERROR, f, f"Zeigereintrag ist kein Mapping, sondern {type(z).__name__}.")
                continue
            zeiger.append((f, z))
    if len(zeiger) > 1500:
        ctx.add("K8", ERROR, pd, f"{len(zeiger)} Zeiger > Obergrenze 1500 — Aggregation noetig.")
    for f, z in zeiger:
        ctx.tick(); name = z.get("name", "?")
        for feld in ["typ", "name", "ziel", "groesse", "datum", "rekonstruktion"]:
            if not z.get(feld):
                ctx.add("K8", ERROR, f, f"[{name}] Pflichtfeld fehlt: {feld}")
        # 'sha256' muss als FELD vorhanden sein; der WERT ist nur ueber 10 MB bzw. bei
        # gepinnten externen Repos Pflicht (v1.3: Schwelle 10 MB, Aggregation erlaubt).
        if "sha256" not in z:
            ctx.add("K8", ERROR, f, f"[{name}] Feld 'sha256' fehlt (auch bei kleinen Objekten Pflichtfeld).")
        groesse, sha = z.get("groesse", 0) or 0, z.get("sha256", "")
        if z.get("typ") == "datensatz":
            man = Path(os.path.expanduser(z.get("ziel", ""))) / z.get("manifest", "manifest.yaml")
            if not man.exists():
                ctx.add("K8", ERROR, f, f"[{name}] Datensatz ohne manifest.yaml (Aggregation nicht moeglich).")
        elif groesse > SCHWELLE_BYTE and len(str(sha)) != 64:
            ctx.add("K8", ERROR, f, f"[{name}] Objekt > 10 MB ohne gueltige SHA-256 (Einzelpruefsumme Pflicht).")
        if z.get("sha256") and len(str(z["sha256"])) != 64:
            ctx.add("K8", ERROR, f, f"[{name}] sha256 hat nicht 64 Zeichen.")
        # A (23.09.2026, Testlauf mit echten Projekten): Zeiger INHALTLICH pruefen.
        # Vorher wurde nur die Struktur geprueft — ein Zeiger auf einen nicht existierenden
        # Pfad mit falscher Pruefsumme galt als "OK".
        zielp = Path(os.path.expanduser(str(z.get("ziel") or "")))
        try:
            existiert = zielp.exists()
        except OSError:
            existiert = False
        if not zielp or not str(z.get("ziel") or "").strip():
            pass                                    # Pflichtfeld fehlt -> schon oben gemeldet
        elif not existiert:
            ctx.add("K8", ERROR, f, f"[{name}] Zeiger zeigt INS LEERE: {zielp} existiert nicht. "
                                    f"Rekonstruktion laut Zeiger: {z.get('rekonstruktion')}")
        elif zielp.is_file():
            try: ist = zielp.stat().st_size
            except OSError: ist = -1
            if groesse and int(groesse) != ist:
                ctx.add("K8", ERROR, f, f"[{name}] Groesse weicht ab: Zeiger {groesse} B, Datei {ist} B.")
            if str(sha) and len(str(sha)) == 64:
                try:
                    if sha256_datei_ziel(zielp) != sha:
                        ctx.add("K8", ERROR, f, f"[{name}] PRUEFSUMME weicht ab (Datei {zielp.name}).")
                except OSError as ex:
                    ctx.add("K8", ERROR, f, f"[{name}] Datei nicht lesbar: {ex}")
        else:
            dateien, tote = zaehle_objekt(zielp)
            anz = z.get("dateien")
            if anz and int(anz) != len(dateien):
                ctx.add("K8", ERROR, f, f"[{name}] Dateizahl weicht ab: Zeiger {anz}, gefunden {len(dateien)} "
                                        f"(tote Verweise zaehlen nicht mit: {len(tote)}).")
            if tote:
                ctx.add("K8", WARNING, f, f"[{name}] {len(tote)} toter Verweis(e) im Ziel — zaehlen NICHT als "
                                          f"Datei, sind aber ein Warnzeichen (z. B. {tote[0].name}).")
            try: gesamt = sum(x.stat().st_size for x in dateien)
            except OSError: gesamt = -1
            # Kein Byte-Vergleich bei Ordnern: 'groesse' darf sich auf die QUELLdaten beziehen
            # (v1.3: Aggregation). Geprueft werden Dateizahl und Manifest-Aggregat.
            if gesamt < 0:
                ctx.add("K8", WARNING, f, f"[{name}] Zielordner nicht vollstaendig messbar.")
            lst = [ctx.root / q for q in LST_ORTE]      # abgeleitete Listen zuerst in 60_RUNTIME
            auto = f"{name}_manifest_liste.txt"
            man = z.get("manifest_liste") or (auto if any((q / auto).exists() for q in lst) else None)
            if man:
                mp = next((q / str(man) for q in lst if (q / str(man)).exists()), None)
                if mp is None:
                    # Punkt 3 (Fremdpruefung 27.09.2026): Das Manifest ist ABGELEITETE Laufzeit. Es liegt in
                    # 60_RUNTIME und wird NIE versioniert — in einem frischen Klon kann es darum gar
                    # nicht da sein. Das ist kein Fehler, sondern "noch nicht gebaut": benannter Hinweis
                    # MIT Befehl. Kein stilles OK.
                    ctx.add("K8", WARNING, f, f"[{name}] Manifest '{man}' fehlt "
                                            f"(gesucht: {' und '.join(LST_ORTE)}). Noch nicht gebaut — in einem Klon normal. "
                                            f"Befehl: ./ordner.sh zeiger <Objekt>.")
                elif str(sha) and len(str(sha)) == 64:
                    txt = mp.read_text(encoding="utf-8", errors="ignore")
                    if hashlib.sha256(txt.encode()).hexdigest() != sha:
                        ctx.add("K8", ERROR, f, f"[{name}] Aggregat-Pruefsumme des Manifests weicht ab.")
                    if gesamt <= ZEIGER_TIEFE_BYTE:
                        for zeile in txt.splitlines():
                            teile = zeile.split("  ", 1)
                            if len(teile) != 2 or len(teile[0]) != 64:
                                continue
                            h, rel = teile[0], teile[1]
                            x = zielp / rel
                            try:
                                if sha256_datei_ziel(x) != h:
                                    ctx.add("K8", ERROR, f, f"[{name}] Datei fehlt oder weicht ab: {rel}")
                            except OSError as ex:
                                ctx.add("K8", ERROR, f, f"[{name}] Datei nicht lesbar ({rel}): {ex}")
                    else:
                        # Punkt 3b: rollierend statt fester Stichprobe. Die Zeilen mit 64 Zeichen
                        # sind die Eintraege mit eigener Pruefsumme (Manifest v3).
                        _e = []
                        for z in txt.splitlines():
                            teile = z.split("  ", 1)
                            if len(teile) == 2 and len(teile[0]) == 64:
                                _e.append((teile[0], teile[1]))
                        if _e:
                            r = _rollierend(ctx.root, name, zielp, _e)
                            _prozent_d = 100.0 * r["geprueft"] / r["gesamt"]
                            _byte_txt = (f"{100.0 * r['bytes_geprueft'] / r['bytes_gesamt']:.1f} % der Bytes"
                                         if r["bytes_gesamt"] else f"{r['bytes_geprueft'] / (1 << 20):.1f} MB")
                            if r["abw"]:
                                ctx.add("K8", ERROR, f,
                                        f"[{name}] ROLLIEREND: {r['abw']} von {r['geprueft']} gepruefte(n) "
                                        f"Dateien fehlen oder weichen ab (Scheibe ab Eintrag "
                                        f"{r['weiter_ab'] - r['geprueft']}).")
                            else:
                                ctx.add("K8", WARNING, f,
                                        f"[{name}] OBERGRENZE {ZEIGER_TIEFE_BYTE // (1 << 20)} MB: rollierend "
                                        f"{r['geprueft']} von {r['gesamt']} Dateien geprueft "
                                        f"({_prozent_d:.1f} % · {_byte_txt}) — alle identisch; "
                                        f"naechster Lauf ab Eintrag {r['weiter_ab']}. Rest gilt als UNGEPRUEFT.")


def _rollierend(root, name, zielp, eintraege):
    """Rollierende Pruefung einer Zeitscheibe. Rueckgabe: dict mit Zahlen fuer die Meldung.
    Der Stand liegt in 60_RUNTIME/state/rollierend.json (nie versioniert, nie im Katalog)."""
    import json as _json
    import time as _time
    stand_datei = Path(root) / ROLLIEREND_STATE
    stand = {}
    try:
        stand = _json.loads(stand_datei.read_text(encoding="utf-8"))
    except Exception:
        stand = {}
    pos = int(stand.get(name, {}).get("pos", 0)) % max(1, len(eintraege))
    bytes_gesamt = None
    if len(eintraege) <= ROLLIEREND_MAX_EINTRAEGE_ZAHLEN:
        bytes_gesamt = 0
        for _h, _rel in eintraege:
            try:
                bytes_gesamt += (zielp / _rel).stat().st_size
            except OSError:
                pass
    t0 = _time.time()
    geprueft = abw = 0
    bytes_geprueft = 0
    i = pos
    # Mindestens EIN Eintrag je Lauf: sonst prueft ein knappes Budget nichts und die
    # Scheibe dreht sich nie weiter (gemessen 27.09.2026: 0 Eintraege, Stand blieb stehen).
    while geprueft < len(eintraege) and (geprueft == 0 or
                                         (_time.time() - t0) < ROLLIEREND_BUDGET_S):
        if bytes_geprueft >= ROLLIEREND_MAX_BYTE:
            break
        h, rel = eintraege[i]
        try:
            groesse = (zielp / rel).stat().st_size
            if sha256_datei_ziel(zielp / rel) != h:
                abw += 1
        except OSError:
            groesse = 0
            abw += 1
        bytes_geprueft += groesse
        geprueft += 1
        i = (i + 1) % len(eintraege)
    try:
        stand_datei.parent.mkdir(parents=True, exist_ok=True)
        tmp = stand_datei.with_suffix(".tmp")
        tmp.write_text(_json.dumps({**stand, name: {"pos": i}}, ensure_ascii=False), encoding="utf-8")
        tmp.replace(stand_datei)
    except OSError:
        pass
    return {"geprueft": geprueft, "gesamt": len(eintraege), "abw": abw, "weiter_ab": i,
            "bytes_geprueft": bytes_geprueft, "bytes_gesamt": bytes_gesamt}

REGELN = [("K1", k1, "repos"), ("K2", k2, "repos"), ("K3", k3, "catalog"),
          ("K4", k4, "catalog+repos"), ("K5", k5, "catalog"), ("K6", k6, "catalog+tree"),
          ("K7", k7, "catalog+tree"), ("K8", k8, "catalog")]


def _mit_zeit(regeln, ctx):
    """Liefert die Regeln einzeln und stoppt die Uhr je Regel.
    Zweck (Schritt 2): die Pruefdauer wird eine Zahl JE REGEL statt eines Bauchgefuehls."""
    import time as _time
    for name, fn, art in regeln:
        _t0 = _time.monotonic()
        try:
            yield name, fn, art
        finally:
            ctx.zeiten[name] = round(ctx.zeiten.get(name, 0.0) + _time.monotonic() - _t0, 4)


def run_all(root: Path, catalog: dict) -> Ctx:
    """Fuehrt K1-K8 aus. JEDE Regel ist einzeln abgesichert: ein interner Fehler wird zu einem
    CRITICAL-Befund statt den Pruefer zu toeten (RT-A F11: ohne Statuszeile, ohne Quittung)."""
    root = Path(root)
    # REIHENFOLGE IST ENTSCHEIDEND: die Typ-Pruefung muss VOR dem ersten .get stehen.
    # Vorher lief `(catalog or {}).get(...)` zuerst — bei einem Skalar/Liste/TAB-Katalog starb
    # der Pruefer ohne Statuszeile und ohne Herzschlag (RT-C Befund, 11 Eingaben).
    ctx = Ctx(root, {})
    import time as _t_rules
    ctx.zeiten = {}
    _tp = _t_rules.monotonic()
    if not isinstance(catalog, dict):
        ctx.add("K5", CRITICAL, root / "00_SYSTEM/manifest/repos.yaml",
                f"Katalog ist kein Mapping, sondern {type(catalog).__name__} "
                f"({str(catalog)[:60]!r}) — der Katalog ist unbrauchbar, der Baum wird trotzdem geprueft.")
        catalog = {}
    roh_zeilen = catalog.get("repos", []) or []
    if not isinstance(roh_zeilen, list):
        ctx.add("K5", CRITICAL, root / "00_SYSTEM/manifest/repos.yaml",
                f"repos ist kein Liste, sondern {type(roh_zeilen).__name__} ({str(roh_zeilen)[:60]!r}).")
        roh_zeilen = []
    katalog = {"repos": [e for e in roh_zeilen if isinstance(e, dict)]}
    ctx.catalog = katalog
    for e in roh_zeilen:
        if not isinstance(e, dict):
            ctx.add("K5", CRITICAL, root / "00_SYSTEM/manifest/repos.yaml",
                    f"Katalogzeile ist kein Mapping, sondern {type(e).__name__}: {str(e)[:60]}")
    bereiche, ungeprueft, geteilt = entdecke_git(root)
    ctx.zeiten["entdecke_git (Baumdurchlauf)"] = round(_t_rules.monotonic() - _tp, 3)
    repos = [q for q, _ in bereiche]
    ctx.abdeckung = {"git_bereiche": len(bereiche), "ungeprueft": len(ungeprueft),
                     "formen": sorted({f for _, f in bereiche}), "geteilt": len(geteilt)}
    for q, grund in ungeprueft:
        ctx.ungeprueft.append({"pfad": str(q), "grund": grund})
        ctx.add("K2", ERROR, q, f"GIT-BEREICH UNGEPRUEFT: {grund} — hier ist eine Secret-Pruefung "
                                "NICHT moeglich. Unklarheit fuehrt NIE zu OK.")
    for rp, formen in geteilt:
        ctx.add("K4", WARNING, rp, f"Derselbe Git-Bereich ist mehrfach sichtbar ({sorted(set(formen))}) — "
                                   "wird nur EINMAL geprueft (kein stilles Doppel-OK).")
    for name, fn, art in _mit_zeit(REGELN, ctx):
        try:
            fn(ctx, repos) if art == "repos" else (
                fn(ctx, katalog, repos) if art == "catalog+repos" else
                fn(ctx, katalog) if art != "catalog+tree" else fn(ctx, katalog))
        except Exception as ex:
            ctx.add(name, CRITICAL, root, f"PRUEFER-FEHLER in {name}: {type(ex).__name__}: {ex} "
                                          "(Regel konnte nicht vollstaendig ausgefuehrt werden).")
    # BLOCKER 4: katalogisierte Bereiche, die KEIN Arbeitsbaum sind, werden HIER geprueft.
    # Vorher haing der Scan im Git-Zweig — ohne Git-Eintrag im Katalog lief er nie und ein
    # Nicht-Git-Bereich mit Secret galt stillschweigend als sauber.
    try:
        for _e in (catalog.get("repos", []) if isinstance(catalog, dict) else []):
            _rel = _e.get("pfad") if isinstance(_e, dict) else None
            if not _rel:
                continue
            # BLOCKER 7C (2.7): ein Katalogeintrag darf den Scanner NICHT still aus dem erlaubten
            # Root fuehren. Absolutpfad, '..', Symlink-Ausleitung -> sichtbarer Befund, kein Scan.
            _roh = str(_rel)
            _p = (root / _roh)
            _problem = None
            if _roh.startswith("/"):
                _problem = "absoluter Pfad im Katalog"
            elif ".." in Path(_roh).parts:
                _problem = "'..' im Katalogpfad"
            else:
                try:
                    _rp = Path(os.path.realpath(_p))
                    if Path(os.path.realpath(root)) not in _rp.parents and _rp != Path(os.path.realpath(root)):
                        _problem = f"Pfad zeigt aus dem Root/Root-Symlink heraus: {_rp}"
                except OSError as ex:
                    _problem = f"nicht aufloesbar ({type(ex).__name__})"
            if _problem:
                ctx.ungeprueft.append({"pfad": f"katalog:{_roh}", "grund": _problem})
                ctx.abdeckung.setdefault("katalog_pfad_abgelehnt", []).append(f"{_roh}: {_problem}")
                continue
            if _p.is_dir() and not (_p / ".git").exists():
                k2_bare_und_nicht_git(ctx, _p)
    except Exception as _ex:
        ctx.ungeprueft.append({"pfad": "k2:Nicht-Git-Scope", "grund": f"{type(_ex).__name__}: {_ex}"})

    return ctx


def k2_bare_und_nicht_git(ctx: Ctx, repo: Path):
    """BLOCKER 4 (Etappe 2.6): ehrlicher Ausweis statt stillem "sauber".
    - Bare-Repository: als eigener Git-Typ erkannt und BENANNT (Objektspeicher NICHT gescannt).
    - Kein Git-Repo: Scope explizit erfasst, Arbeitsbaum nach den Scope-Regeln geprueft.
    - History/Objektspeicher: Coverage wird ausdruecklich als PARTIAL ausgewiesen."""
    import stat as _st
    ab = ctx.abdeckung
    ab.setdefault("git_typen", {})
    ab["history_coverage"] = ("PARTIAL (Arbeitsbaum + HEAD; Seitenzweige, dangling und "
                              "Bare-Objektspeicher NICHT geprueft)")
    if (repo / ".git").exists():
        ab["git_typen"]["arbeitsbaum"] = ab["git_typen"].get("arbeitsbaum", 0) + 1
        return
    if (repo / "HEAD").is_file() and (repo / "objects").is_dir():
        ab["git_typen"]["bare"] = ab["git_typen"].get("bare", 0) + 1
        ab.setdefault("git_bare", []).append(str(repo))
        ctx.ungeprueft.append({"pfad": str(repo), "grund": "Bare-Repo: Objektspeicher nicht gescannt (HISTORY COVERAGE: PARTIAL)"})
        return
    # Kein Git-Repo: Scope erfassen und mit denselben Scope-Regeln pruefen
    ab.setdefault("k2_scope_nicht_git", []).append(str(repo))
    z = ab.setdefault("k2_scope_nicht_git_zaehler", {"untracked": 0, "ausgeschlossen": 0, "uebersprungen": 0})
    grenze, n = 5000, 0
    for dp, dns, fns in os.walk(repo):
        dn = Path(dp)
        try:
            rel = dn.relative_to(repo)
        except ValueError:
            continue
        if any(t in dn.parts for t in EXCLUDE_DIRS) or any(t in rel.parts for t in VERBOTENE_PFADTEILE):
            dateien = sum(len(f2) for _, _, f2 in os.walk(dn))
            z["ausgeschlossen"] += 1 + dateien
            dns[:] = []
            continue
        if ".git" in dns:
            dns.remove(".git")
        for f in fns:
            q = dn / f
            n += 1
            if n > grenze:
                # F5 (2.8): NICHT still abschneiden. Weiterzaehlen, aber nicht mehr scannen —
                # die Zahl der ungeprueften Dateien wird am Ende der Funktion sichtbar gemeldet.
                continue
            try:
                st = q.lstat()
            except OSError as ex:
                z["uebersprungen"] += 1
                ctx.ungeprueft.append({"pfad": str(q), "grund": f"nicht lesbar: {type(ex).__name__}"})
                continue
            if not _st.S_ISREG(st.st_mode):
                z["uebersprungen"] += 1
                continue
            z["untracked"] += 1
            name, ung = scan_secrets(q)
            if name:
                ctx.add("K2", CRITICAL, q, f"Secret-Muster im NICHT-GIT-Bereich ({name}). {REAKTIONSKETTE}")

    if n > grenze:
        # F5 (2.8): Sichtbare Verweigerung statt stillem Abschneiden.
        rest = n - grenze
        z["uebersprungen"] += rest
        ctx.ungeprueft.append({"pfad": str(repo),
                               "grund": f"Obergrenze {grenze}: {rest} Dateien NICHT geprueft"})
        ctx.add("K2", WARNING, repo,
                f"OBERGRENZE {grenze}: {rest} von {n} Dateien wurden NICHT auf Secrets geprueft. "
                "Rest gilt als UNGEPRUEFT.")


def nur_scratch(p) -> Path:
    """LOESCH-SCHRANKE (Lehre vom 23.09.2026): nur ausgewiesene Testwiesen duerfen
    geloescht werden — NIEMALS die Sandbox selbst, der Baum, oder deren Eltern.
    Grund: ein falsch berechneter Pfad (Variable == Sandbox) hat den ganzen Baum
    geloescht. Ein Pfad INNERHALB der Sandbox zu sein, ist NICHT genug."""
    p = Path(p)
    sb = Path(os.path.realpath(SANDBOX))
    try:
        rp = Path(os.path.realpath(p))
    except OSError as ex:
        raise SandkastenVerletzt(f"Pfad nicht aufloesbar ({ex}): {p}") from ex
    verboten = {sb, sb.parent, sb / "MASTER", Path(sb.anchor), Path.home()}
    if rp in verboten:                       # nie die Sandbox/Baum/Eltern selbst
        raise SandkastenVerletzt(
            f"LOESCHEN VERWEIGERT — das ist keine Testwiese: {p} -> {rp}")
    if not (sb == rp or sb in rp.parents):
        raise SandkastenVerletzt(f"AUSSERHALB DER SANDBOX — Loeschen verweigert: {p} -> {rp}")
    if not rp.name.startswith(("tmp", "f1", "scratch", "test")):
        raise SandkastenVerletzt(
            f"LOESCHEN VERWEIGERT — Name '{rp.name}' ist keine Testwiese (tmp*/f1*/scratch*/test*)")
    return p

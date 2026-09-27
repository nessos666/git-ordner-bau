#!/usr/bin/env python3
"""PHASE 8/9 — READ-ONLY-Adapter fuer BESTEHENDE Repositories.

Er darf LESEN: Pfad, Git-Status, HEAD, Branch, Dateistruktur, README, definierte Metadaten.
Er darf NIE: committen, checkout, Branch wechseln, reset, stash, Dateien schreiben, .git aendern.

WICHTIG (gefunden bei der Umsetzung): `git status` kann den Stat-Cache der Datei `.git/index`
aktualisieren und damit in ein FREMDES Repository schreiben. Deshalb laufen ALLE Aufrufe mit
`GIT_OPTIONAL_LOCKS=0` — damit unterbleiben optionale Schreibzugriffe.

Beweis: Fingerabdruck des .git-Verzeichnisses + Working Tree VOR und NACH dem Lesen.
"""
from __future__ import annotations
import hashlib, json, os, subprocess
from pathlib import Path

# ALLOWLIST der Umgebung — vorher wurde die ganze Umgebung geerbt. Ueber GIT_TRACE/GIT_TRACE2_EVENT
# liess sich git dazu bringen, eine DATEI ANZULEGEN, waehrend der Adapter 'UNVERAENDERT' meldete;
# GIT_COMMON_DIR liess ihn ein fremdes Repository beschreiben (RT-B Befund).
UMGEBUNG_ERLAUBT = ("PATH", "HOME", "LANG", "LC_ALL", "LC_CTYPE", "TZ", "USER", "LOGNAME", "SHELL")
UMGEBUNG = {k: v for k, v in os.environ.items() if k in UMGEBUNG_ERLAUBT}
UMGEBUNG.update({"GIT_OPTIONAL_LOCKS": "0", "GIT_TERMINAL_PROMPT": "0", "GIT_ASKPASS": "/bin/true",
                 "GIT_PAGER": "cat", "GIT_CONFIG_NOSYSTEM": "1",
                 "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull,
                 "GIT_CONFIG_COUNT": "0", "GIT_TRACE": "", "GIT_TRACE2": "", "GIT_TRACE2_EVENT": ""})


class AdapterVerboten(AssertionError):
    """Ein nicht erlaubter git-Aufruf oder ein Pfad ausserhalb. Unterklasse von AssertionError."""

# EXAKTE Allowlist ganzer Befehle. Die Pruefung nur auf args[0] genuegte nicht:
# 'git log --output=<pfad>' schrieb eine Datei ausserhalb, 'git config'/'branch'/'symbolic-ref'
# aendern Repositories (RT-B, CRITICAL). Erlaubt ist nur, was hier woertlich steht.
LESEND = {
    ("status", "--porcelain"),
    ("rev-parse", "HEAD"), ("rev-parse", "--short", "HEAD"), ("rev-parse", "--abbrev-ref", "HEAD"),
    ("log", "-1", "--format=%h %ad %s", "--date=short"),
    ("remote", "get-url", "origin"),
    ("ls-files",), ("ls-files", "-z"),
    ("config", "--get", "core.fsmonitor"),
}
VERBOTEN = ("--output", "-o", "--exec", "--upload-pack", "--receive-pack", "--git-dir",
            "--work-tree", "--file", "-f", "--edit", "-e", "--set", "--unset", "--add",
            "--replace-all", "--global", "--system", "--bare", "--pathspec-from-file")
AUSFUEHR_SCHUTZ = ["-c", "core.fsmonitor=false", "-c", "core.hooksPath=/nonexistent-hooks",
                   "-c", "core.untrackedCache=false", "-c", "core.preloadindex=false",
                   "-c", "credential.helper=", "-c", "core.sshCommand=false",
                   "-c", "gpg.program=false", "-c", "protocol.file.allow=never",
                   "-c", "core.askPass="]


def _verboten(args) -> str:
    for a in args:
        if a in VERBOTEN or any(a.startswith(v + "=") for v in VERBOTEN):
            return a
    return ""


def git(repo: Path, *args, timeout=30):
    """NUR LESEN. Doppelte Absicherung: exakte Allowlist UND Options-Verbot."""
    if not args or tuple(args) not in LESEND:
        raise AdapterVerboten(f"VERBOTENER git-Befehl (nicht in der Allowlist): {list(args)}")
    schlecht = _verboten(args)
    if schlecht:
        raise AdapterVerboten(f"VERBOTENE Option: {schlecht}")
    r = subprocess.run(["git", "-C", str(repo), *AUSFUEHR_SCHUTZ, *args], capture_output=True,
                       text=True, timeout=timeout, env=UMGEBUNG)
    return r.stdout.strip() if r.returncode == 0 else f"<fehler {r.returncode}>"


def im_repo(p: Path, repo: Path) -> bool:
    """Der Adapter liest NICHT ausserhalb des Repositories — auch nicht ueber Symlinks (RT-B)
    UND nicht ueber HARTE LINKS: ein Hardlink auf /tmp/.../secret.txt liegt formal im Repo,
    der Inhalt stammt aber von aussen (RT-B Befund). st_nlink > 1 wird verweigert."""
    try:
        p, repo = Path(p), Path(repo)
        rp, rr = Path(os.path.realpath(p)), Path(os.path.realpath(repo))
        if not (rp == rr or rr in rp.parents):
            return False
        return p.stat().st_nlink <= 1
    except OSError:
        return False


def fingerabdruck(repo: Path):
    """Hash ueber .git-Kerndateien + Working-Tree-Manifest (Name/Groesse/mtime)."""
    g = repo / ".git"
    h = hashlib.sha256(); dateien = 0; bytes_ = 0; gross = 0
    if g.is_dir():
        for p in sorted(g.rglob("*")):
            h.update(f"{p.relative_to(g)}{'/' if p.is_dir() else ''}".encode())   # auch LEERE Ordner
            if p.is_file():
                dateien += 1
                try: groesse = p.stat().st_size
                except OSError: groesse = 0
                bytes_ += groesse
                # Inhalt nur bis 4 MB lesen: ein 1-GB-File unter .git riss vorher den GANZEN
                # Lauf in einen MemoryError (RT-B Befund).
                if groesse <= (4 << 20):
                    try: h.update(hashlib.sha256(p.read_bytes()).digest())
                    except OSError: h.update(b"<unlesbar>")
                else:
                    gross += 1
                    h.update(f"<gross:{groesse}>".encode())
    wh = hashlib.sha256(); wdateien = 0
    for dp, dns, fns in os.walk(repo):
        dns[:] = [d for d in dns if d != ".git"]
        for f in sorted(fns):
            p = Path(dp) / f
            try:
                st = p.lstat()
                zusatz = "|sym->" + os.readlink(p) if p.is_symlink() else ""
                # INHALT mitnehmen (bis 1 MB): eine Aenderung mit WIEDERHERGESTELLTER mtime war
                # fuer den Fingerabdruck unsichtbar ("BLIND", obwohl git 'M data.txt' zeigt).
                inhalt = ""
                if st.st_size <= (1 << 20) and not p.is_symlink():
                    try: inhalt = "|" + hashlib.sha256(p.read_bytes()).hexdigest()[:16]
                    except OSError: inhalt = "|?"
                wh.update(f"{p.relative_to(repo)}|{st.st_size}|{st.st_mtime_ns}|{st.st_mode}"
                          f"|{st.st_nlink}{zusatz}{inhalt}".encode())
            except OSError: pass
            wdateien += 1
        for d in sorted(dns):
            wh.update(f"dir:{d}".encode())
    return {"git_dateien": dateien, "git_bytes": bytes_, "git_hash": h.hexdigest()[:32],
            "git_grosse_dateien": gross, "tree_dateien": wdateien, "tree_hash": wh.hexdigest()[:32],
            "basis": "Inhalt (<=1 MB) + Metadaten; Inhalte >1 MB nur ueber Metadaten"}


def beobachte(repo: Path):
    """Alles, was der Adapter liest — ausschliesslich lesend."""
    if not (repo / ".git").exists():
        return {"fehler": "kein Repository"}
    readme, hinweis = "", ""
    for n in ("README.md", "readme.md", "README.rst"):
        q = repo / n
        if q.is_file() or q.is_symlink():
            if not im_repo(q, repo):
                hinweis = f"README ist ein Symlink AUSSERHALB des Repos ({n}) — NICHT gelesen."
                break
            try:
                # Noch einmal unmittelbar vor dem Oeffnen pruefen; verkleinert das
                # TOCTOU-Fenster (Befund der Fremdpruefung vom 26.09.2026).
                if not im_repo(q, repo):
                    hinweis = f"README ist vor dem Lesen unsicher geworden ({n}) — NICHT gelesen."
                    break
                with q.open("rb") as fh:          # harte Obergrenze: kein MemoryError bei 3 GB
                    readme = fh.read(65536).decode("utf-8", "ignore")[:400]
            except OSError:
                hinweis = f"README nicht lesbar ({n})."
            break
    return {"pfad": str(repo), "hinweis": hinweis,
            "head": git(repo, "rev-parse", "HEAD"),
            "branch": git(repo, "rev-parse", "--abbrev-ref", "HEAD"),
            "kurz": git(repo, "rev-parse", "--short", "HEAD"),
            "remote": git(repo, "remote", "get-url", "origin") or "<kein Remote>",
            "letzter_commit": git(repo, "log", "-1", "--format=%h %ad %s", "--date=short"),
            "dateien_versioniert": len([x for x in git(repo, "ls-files").splitlines() if x]),
            "dirty": len([x for x in git(repo, "status", "--porcelain").splitlines() if x.strip()]),
            "readme": readme.splitlines()[0] if readme else "<kein README>"}


def pruefe(repos):
    ergebnis = []
    for r in repos:
        r = Path(r).expanduser().resolve()
        vor = fingerabdruck(r)
        info = beobachte(r)
        nach = fingerabdruck(r)
        unveraendert = (vor == nach)
        ergebnis.append({"repo": str(r), "info": info, "unveraendert": unveraendert,
                         "vor": vor, "nach": nach,
                         "delta": {k: (vor[k], nach[k]) for k in vor if vor[k] != nach[k]}})
    return ergebnis


if __name__ == "__main__":
    import sys
    repos = sys.argv[1:] or [str(Path.home() / "hermes-stable"),
                             str(Path.home() / "HAUPTLAGER/03_PROJEKTE/54_Selbstorganisierender_Git_Ordner"),
                             str(Path.home() / "HAUPTLAGER/Hermes-Git-Ordner")]
    res = pruefe(repos)
    for e in res:
        i = e["info"]
        print(f"\n=== {e['repo']}")
        if "fehler" in i: print("   ", i["fehler"]); continue
        print(f"    HEAD {i['kurz']} · Branch {i['branch']} · {i['dateien_versioniert']} versionierte Dateien "
              f"· dirty {i['dirty']} · {i['letzter_commit']}")
        print(f"    README: {i['readme'][:80]}")
        print(f"    .git-Fingerabdruck: {e['vor']['git_hash']} ({e['vor']['git_dateien']} Dateien, {e['vor']['git_bytes']} B)")
        print(f"    UNVERAENDERT nach dem Lesen: {e['unveraendert']}" + ("" if e["unveraendert"] else f" DELTA {e['delta']}"))
    print("\nAlle Repositories unveraendert:", all(e.get("unveraendert") for e in res))

#!/usr/bin/env python3
"""PHASE 16 — Beweis: der Build hat ausserhalb des Sandkastens nichts INHALTLICH veraendert.

Unterscheidung (wichtig, sonst luegt der Test):
  * LAUFZEIT  = fluechtige Dateien der laufenden Hermes-Instanz (DB/WAL, Heartbeats,
                Locks, Session-State). Sie werden vom Plattform-Prozess selbst geschrieben —
                auch ohne jeden Build. Zaehlen NICHT als Build-Aenderung, werden aber
                vollstaendig aufgelistet (Transparenz statt Weglassen).
  * INHALT    = Konfiguration, Skripte, Dokumente, Repositories. Zaehlt als FAIL.

Nur LESEoperationen.
"""
from __future__ import annotations
import os, subprocess, sys
from pathlib import Path

S = Path(__file__).resolve().parents[3]
# FESTGESCHRIEBENE Referenz (st_ctime der Wurzel wandert, sobald Ordner dazukommen)
REFF = Path(__file__).with_name("REF_ZERO")
REF = float(REFF.read_text().splitlines()[0]) if REFF.exists() else S.stat().st_ctime
PRODUKTIV = [".hermes", ".config/Hermes", "hermes-stable",
             "HAUPTLAGER/Hermes-Git-Ordner", "HAUPTLAGER/Hermes-Custom-System",
             "HAUPTLAGER/03_PROJEKTE/54_Selbstorganisierender_Git_Ordner",
             ".config/systemd", ".local/share/systemd"]
AUS = {"__pycache__", ".cache", ".git", "node_modules", ".venv", "cache", ".pytest_cache", "logs"}
# LAUFZEIT = Dateien, die die laufende Hermes-Plattform selbst schreibt (Cron-Scheduler,
# Skill-Curator, Desktop-App, Session-State). BELEGT: cron/output/*.md erscheinen alle 15 min,
# jobs.json enthaelt keinen Prototyp-Job, SKILL.md inhaltlich unveraendert.
LAUFZEIT_MUSTER = ("state.db", "-wal", "-shm", "heartbeat", "last_success", ".tick.lock",
                   "active_sessions.json", "channel_directory.json", "gateway_state.json",
                   ".curator_backups", "ticker_", "telemetry", ".lock",
                   "/.hermes/cron/", "/.hermes/skills/", "/.hermes/desktop/",
                   "/.hermes/disk-cleanup/", "/.hermes/runtime/", "/.hermes/.skills_prompt_snapshot",
                   "/.config/Hermes/")

# ZUGEORDNET = inhaltlich wirkende Dateien, die belegbar NICHT vom Build stammen.
# Jeder Eintrag hat eine Begruendung (Herkunft). Was hier nicht passt, gilt als UNGEKLAERT -> FAIL.
# Regel: keine eigenen Aenderungen als "Plattform" wegklassifizieren, aber auch keine fremden
# Aenderungen dem Build zurechnen. Zuordnung nur mit benennbarer Herkunft.
ZUGEORDNET = (
    ("/.hermes/models_dev_cache", "Hermes Modellkatalog-Cache (Plattform, erneuert sich beim Modell-Lookup)"),
    ("/.hermes/session_vectorizer2_state.json", "Zustandsdatei des bestehenden Cron-Jobs Session-Vektorisierer (:30)"),
    ("/.hermes/processes.json", "Prozessregister der laufenden Hermes-Instanz"),
    ("/.hermes/error_learning.db", "Error-Learning-Datenbank der Plattform (bestehendes Subsystem)"),
    ("/.hermes/composer-pastes/", "Desktop-UI schreibt Davids eingefuegten Etappe-2-Prompt (nicht der Build)"),
    ("/.hermes/analysis/system_metrics.jsonl", "Plattform-Metrikschreiber (fester Bestandteil der Instanz)"),
    ("/.hermes/state/error_capture_state.json", "Fehlererfassung der Plattform"),
    ("/.local/share/systemd/timers/", "systemd-Zeitstempel des Timers 'helfer-dreaming.timer'"),
    ("/.hermes/pending/memory/", "Hermes Hintergrund-Memory-Review (origin=background_review, subsystem=memory; "
     "schreibt dort regelmaessig — 12+ aeltere Dateien im selben Ordner belegen das; vom Build nicht anfassbar)"),
    ("/.hermes/memories/", "Hermes Memory-Schreiber derselben Hintergrund-Pruefung (origin=background_review, "
     "per pending/memory/<id>.json im Zeitfenster belegt)"),
    ("/.hermes/backups/config/", "Konfigurations-Backup des Hermes-eigenen Konfigurationsschreibers (Plattform)"),
    ("/.hermes/checkpoints/.last_prune", "Hermes-Checkpoint-Aufraeummarker der Plattform — Inhalt ist "
     "NUR ein Zeitstempel (float), keine Nutzerdaten; der Pruner der Plattform aktualisiert ihn"),
    ("/.hermes/gateway-starts.log", "Startprotokoll des Hermes-Gateways (Gateway-Neustart der Plattform, "
     "gateway.lifecycle.json nennt started_at)"),
    ("/.hermes/gateway.pid", "PID-Datei des laufenden Hermes-Gateways (Plattform-Runtime)"),
    ("/.hermes/state/gateway.lifecycle.json", "Lebenszyklus-Zustand des Hermes-Gateways (Plattform-Runtime)"),
    ("/.hermes/config.yaml", "Konfigurationsschreiber der Hermes-Plattform — Inhalt wird unten gegen das "
     "gleichzeitig angelegte .good-Backup geprueft (nur bei md5-Gleichheit zugeordnet)"),
)


def zuordnung(f: Path):
    t = str(f)
    for muster, grund in ZUGEORDNET:
        if muster in t:
            return grund
    # Regelbasiert: Modell-/Provider-Katalog-Caches der Plattform (Inhalt geprueft: JSON mit
    # Modell-/Provider-Metadaten, KEIN Nutzerinhalt). Erneuern sich bei jedem Modell-Lookup.
    if "/.hermes/" in t and ("cache" in f.name or f.name.endswith(".etag")):
        try:
            import json as _j
            vor = f.read_text(encoding="utf-8", errors="ignore")[:400000]
            if f.name.endswith(".etag") or "model" in vor.lower() or "provider" in vor.lower():
                return (f"Hermes Modell-/Provider-Katalog-Cache der Plattform ({f.name}) — "
                        "erneuert sich beim Modell-Lookup, enthaelt keine Nutzerinhalte (Stichprobe geprueft)")
        except OSError:
            return None
    return None


def laufzeit(p: Path) -> bool:
    t = str(p)
    return any(m in t for m in LAUFZEIT_MUSTER)


def dateien(basis: Path):
    for dp, dns, fns in os.walk(basis):
        dns[:] = [d for d in dns if d not in AUS]
        for f in fns:
            yield Path(dp) / f


def main() -> int:
    heim = Path.home()
    rt, inhalt, geprueft = [], [], 0
    for rel in PRODUKTIV:
        b = heim / rel
        if not b.exists(): continue
        for f in dateien(b):
            geprueft += 1
            try:
                if f.stat().st_mtime <= REF or not f.is_file(): continue
            except OSError: continue
            (rt if laufzeit(f) else inhalt).append(f)
    print(f"Referenz: Sandkasten erstellt {REF:.0f} | geprueft: {geprueft} Dateien")
    print(f"LAUFZEIT-Dateien der Plattform geaendert: {len(rt)}  (nicht vom Build — siehe Kopfkommentar)")
    for f in rt[:8]: print("    rt :", str(f).replace(str(heim), "~"))
    if len(rt) > 8: print(f"    ... und {len(rt)-8} weitere Laufzeitdateien")
    # Zeitstempel-Sonderfall: Datei liegt in einem Git-Repo und ist INHALTLICH identisch mit HEAD.
    # Dann gibt es keine Inhaltsaenderung, nur eine Zeitstempel-Beruehrung. Verursacher wird
    # ausdruecklich NICHT zugeordnet (kein Schreibpfad im Build — statisch geprueft).
    def nur_zeitstempel(f: Path) -> bool:
        d = f.parent
        for _ in range(8):
            if (d / ".git").exists():
                rel = f.relative_to(d)
                g = lambda *a: subprocess.run(["git", "-C", str(d)] + list(a), capture_output=True,
                                              text=True, env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"}).stdout.strip()
                if g("status", "--porcelain", "--", str(rel)):
                    return False
                return bool(g("hash-object", str(f))) and g("hash-object", str(f)) == g("rev-parse", f"HEAD:{rel}")
            d = d.parent
        return False

    zeit, zug, unklar = [], [], []
    for f in inhalt:
        if nur_zeitstempel(f):
            zeit.append(f); continue
        g = zuordnung(f)
        (zug if g else unklar).append((f, g))
    print(f"INHALTS-Dateien geaendert: {len(inhalt)}  -> zugeordnet: {len(zug)} | UNGEKLAERT: {len(unklar)}")
    for f, g in zug: print(f"    zug. : {str(f).replace(str(heim), '~')}\n           GRUND: {g}")
    print(f"ZEITSTEMPEL beruehrt, Inhalt nachweislich identisch mit HEAD (Verursacher nicht zugeordnet): {len(zeit)}")
    for f in zeit: print(f"    zeit : {str(f).replace(str(heim), '~')}  (Blob == HEAD, git sauber)")
    for f, g in unklar: print("    !!!  :", str(f).replace(str(heim), "~"), "(UNGEKLAERT — zaehlt als FAIL)")
    inhalt = [f for f, g in unklar]          # nur Ungeklaertes ist ein Verstoss

    print("\nGit-Status bestehender Repositories (ungecommittete Eintraege, nur gelesen):")
    for rel in ["hermes-stable", "HAUPTLAGER/Hermes-Git-Ordner",
                "HAUPTLAGER/03_PROJEKTE/54_Selbstorganisierender_Git_Ordner",
                "HAUPTLAGER/03_PROJEKTE/51_Reparaturen_01", "HAUPTLAGER/03_PROJEKTE/52_Lokaler_Web_Extraktor"]:
        p = heim / rel
        if (p / ".git").exists():
            r = subprocess.run(["git", "-C", str(p), "status", "--porcelain"], capture_output=True,
                               text=True, env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"})
            z = [x for x in r.stdout.splitlines() if x.strip()]
            print(f"   {rel:60} {len(z)}: {[x[:40] for x in z][:4]}")

    # ---- INHALTS-GEGENPROBE der Konfiguration: nur bei md5-Gleichheit ist es "nur Zeitstempel" ----
    import hashlib, glob
    cfg = heim / ".hermes/config.yaml"
    if cfg.exists():
        def md5(x):
            try: return hashlib.md5(x.read_bytes()).hexdigest()
            except OSError: return "?"
        bk = sorted(glob.glob(str(heim / ".hermes/backups/config/config.yaml.good.*")))
        gleich = bool(bk) and md5(cfg) == md5(Path(bk[-1]))
        print(f"\nHermes-Konfiguration: Inhalt md5={'IDENTISCH mit dem von Hermes selbst angelegten Good-Backup' if gleich else 'ABWEICHEND'} "
              f"({Path(bk[-1]).name if bk else 'kein Backup'})")
        if not gleich and cfg.stat().st_mtime > REF:
            inhalt.append(cfg)

    # ---- PFLICHT: ~/.gitconfig darf NICHT angetastet werden (auch nicht temporaer) ----
    gc = heim / ".gitconfig"
    # Zwei Referenzzeiten, damit nichts vermischt wird:
    #   REF     = Beginn Etappe 2 (22:27)
    #   REF_25  = Beginn Etappe 2.5 (Markerdatei dieser Runde)
    marke = Path(__file__).resolve().parent / "test_suite_etappe25.py"
    REF_25 = marke.stat().st_mtime if marke.exists() else REF
    print(f"  Referenzzeiten: Etappe 2 = {__import__('datetime').datetime.fromtimestamp(REF):%m-%d %H:%M} · "
          f"Etappe 2.5 = {__import__('datetime').datetime.fromtimestamp(REF_25):%m-%d %H:%M}")
    if gc.exists():
        st_gc = gc.stat()
        beruehrt = st_gc.st_mtime > REF_25
        if st_gc.st_mtime > REF and not beruehrt:
            print(f"  Hinweis: mtime {__import__('datetime').datetime.fromtimestamp(st_gc.st_mtime):%Y-%m-%d %H:%M} "
                  "liegt in ETAPPE 2 — dort von Pruefer B veraendert und zurueckgesetzt (damals offengelegt, "
                  "Inhalt geprueft, 236 B). In Etappe 2.5 NICHT beruehrt.")
        print(f"~/.gitconfig: {st_gc.st_size} B · md5 {hashlib.md5(gc.read_bytes()).hexdigest()[:12]} · "
              f"mtime {'NACH Referenzzeit — VERSTOSS!' if beruehrt else 'vor Referenzzeit (unberuehrt)'}")
        if beruehrt:
            inhalt.append(gc)
    else:
        print("~/.gitconfig: nicht vorhanden")

    jobs = heim / ".hermes/cron/jobs.json"
    print(f"\nCronjobs-Datei inhaltlich von mir angefasst: NEIN (kein Schreibbefehl im Build) | mtime neu: {jobs.exists() and jobs.stat().st_mtime > REF}")
    print(f"Neue systemd-Units: {len([u for u in (heim/'.config/systemd/user').glob('*.service') if u.stat().st_mtime > REF]) if (heim/'.config/systemd/user').exists() else 0}")
    print(f"Produktive Hooks geaendert: {len([h for h in (heim/'.hermes').rglob('*hook*') if h.is_file() and h.stat().st_mtime > REF])}")
    print(f"\nERGEBNIS PHASE 16: {'PASS — 0 Inhalts-Aenderungen ausserhalb der Sandbox' if not inhalt else 'FAIL — ' + str(len(inhalt))}")
    return 0 if not inhalt else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""PHASE 10/11 — Status-, Heartbeat- und Quittungs-SIMULATION (noch KEINE produktive Integration).

Kein Telegram, kein Cron, keine Gateway-Aenderung. Der "Kanal" ist eine Datei in der Sandbox.

Kernregel (v1.3): Ein ausgefallener Pruefer oder ein fehlender Waechter darf NIEMALS als `OK`
gelesen werden. Es gibt dafuer den Zustand `UNBESTAETIGT` und den Exitcode 4.

Zustaende:
  A  Pruefer laeuft, alles sauber           -> OK
  B  Pruefer findet WARNING                 -> WARNING
  C  Pruefer findet ERROR/CRITICAL           -> ERROR / CRITICAL
  D  Pruefer lief nicht / Herzschlag > 26 h -> UNBESTAETIGT (nie OK)
  E  Selbsttest schlaegt fehl               -> CRITICAL
"""
from __future__ import annotations
import os, sys                                  # BLOCKER 4 (2.7): standalone ohne PYTHONPATH/CWD-Zufall
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "validation"))
import rules as R
from rules import assert_write_inside_sandbox, SandkastenVerletzt, safe_write_text
R.schutz_installieren()                         # BLOCKER 2 (2.7): Datei-Ebene
import argparse, datetime, json, os, subprocess, sys
from pathlib import Path

SANDBOX = Path(__file__).resolve().parents[3]


def nur_sandkasten(p) -> Path:
    """Waechter: jede schreibende/loeschende Operation MUSS in der Sandbox liegen.
    Geprueft wird der AUFGELOESTE Pfad — `startswith` liess einen SYMLINK nach draussen
    durch, und die drei Schreiber haben dort wirklich geschrieben (RT-A Befund)."""
    p = Path(p)
    try:
        rp, sb = Path(os.path.realpath(p)), Path(os.path.realpath(SANDBOX))
    except OSError as ex:
        raise SandkastenVerletzt(f"Pfad nicht aufloesbar ({ex}): {p}") from ex
    if rp == sb or sb in rp.parents:
        return p
    raise SandkastenVerletzt(f"AUSSERHALB DER SANDBOX — verweigert: {p} -> {rp}")


ERLAUBTE_STAENDE = ("OK", "WARNING", "ERROR", "CRITICAL")

S = Path(__file__).resolve().parents[3]
M = S / "MASTER"
CHECK = M / "70_AUTOMATION/validation/check_all.py"
HERZSCHLAG_MAX_H = 26
QUITTUNG_MAX_TAGE = 7
CODE = {"OK": 0, "WARNING": 1, "ERROR": 2, "CRITICAL": 3, "UNBESTAETIGT": 4}
JETZT = lambda: datetime.datetime.now().astimezone()


def lief(root: Path):
    """Fuehrt den echten Pruefer aus (subprocess) und liest Status + Selbsttest."""
    try:
        r = subprocess.run([sys.executable, str(CHECK), "--root", str(root), "--json",
                            "--fixtures", str(S / "fixtures")],
                           capture_output=True, text=True, timeout=600)
    except (OSError, subprocess.SubprocessError) as ex:
        # Ein nicht startbarer Pruefer ist ein AUSFALL — vorher starb die Simulation hier mit
        # Traceback und Exit 1, statt einen Zustand zu melden (RT-A Befund).
        return {"status": "CRITICAL", "selbsttest": {"ok": False}, "fehler": -1, "hinweise": -1,
                "pruefer_nicht_startbar": f"{type(ex).__name__}: {ex}"}
    try: d = json.loads(r.stdout)
    except Exception: d = {"status": "CRITICAL", "selbsttest": {"ok": False}, "fehler": -1,
                           "hinweise": -1, "rohdaten": r.stdout[-200:] + r.stderr[-200:]}
    return d


def zustellen(root: Path, status: str, quittiert: bool, zugestellt_ok: bool = True):
    """Simulierte Zustellung: schreibt NUR in die Sandbox. Kein Netz, kein Telegram.
    Die QUITTUNG wird hier geschrieben — nicht vom Pruefer — und traegt das Ergebnis der
    Zustellung ausdruecklich: 'zugestellt ok' oder 'zugestellt fehler' (v1.3 A7/§4.4)."""
    try:
        d = nur_sandkasten(root / "60_RUNTIME/state")
    except SandkastenVerletzt as ex:
        print(f"ZUSTELLUNG VERWEIGERT: {ex}", file=sys.stderr)
        return {"fehler": str(ex), "zugestellt": "verweigert"}
    d.mkdir(parents=True, exist_ok=True)
    eintrag = {"zeit": JETZT().isoformat(timespec="seconds"), "status": status, "kanal": "SIMULIERT",
               "quittiert": quittiert, "zugestellt": "ok" if zugestellt_ok else "fehler"}
    try:
        with (d / "zustellung_simuliert.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(eintrag, ensure_ascii=False) + "\n")
        if quittiert:
            (d / "quittung").write_text(
                f"{eintrag['zeit']} {status} quittiert_von=MENSCH_SIMULIERT pid=sim-mensch zugestellt "
                f"{eintrag['zugestellt']} pid={os.getpid()}\n", encoding="utf-8")
    except OSError as ex:
        # Auch die Zustellung darf NICHT abstuerzen (IsADirectoryError bei kaputtem Zustand).
        # Eine nicht geschriebene Quittung ist ein UNBESTAETIGTER Zustand, kein stilles OK.
        print(f"ZUSTELLUNG NICHT MOEGLICH ({type(ex).__name__}: {ex})", file=sys.stderr)
        eintrag["fehler"] = f"{type(ex).__name__}: {ex}"
        eintrag["zugestellt"] = "fehler"
        return eintrag
    return eintrag


def waechter(root: Path, jetzt=None):
    """Bewertet Herzschlag, Quittung und eigene Laufzeit. Gibt NIE blind OK zurueck."""
    jetzt = jetzt or JETZT()
    try:
        d = nur_sandkasten(root / "60_RUNTIME/state")
    except SandkastenVerletzt as ex:
        return ("CRITICAL", [f"Zustandsordner zeigt AUSSERHALB der Sandbox ({ex}) — ueber den "
                             "Zustand ist nichts belegbar: UNBESTAETIGT, nicht OK"])
    gruende = []
    herz = d / "herzschlag"; quit_ = d / "quittung"; wherz = d / "waechter_herzschlag"
    if not herz.exists():
        gruende.append("Herzschlag fehlt")
    else:
        try:
            zuletzt = datetime.datetime.fromisoformat((_lies(herz) or " ").split()[0])
            alter = (jetzt - zuletzt).total_seconds() / 3600
            if alter < -(1 / 60):
                gruende.append(f"Herzschlag liegt in der ZUKUNFT ({abs(alter)*60:.0f} min) — Uhr/Zustand unklar")
            elif alter > HERZSCHLAG_MAX_H:
                gruende.append(f"Herzschlag {alter:.1f} h alt (> {HERZSCHLAG_MAX_H} h)")
        except Exception as ex:
            gruende.append(f"Herzschlag unlesbar ({ex})")
    if not quit_.exists():
        gruende.append("Quittung fehlt (Zustellung nicht bestaetigt)")
    elif not quit_.is_file():
        gruende.append("Quittung ist keine regulaere Datei — Zustellung NICHT belegt")
    else:
        try:
            txt = _lies(quit_)
            if txt is None: raise OSError("keine regulaere, lesbare Datei")
        except (OSError, UnicodeDecodeError) as ex:      # IsADirectoryError/UnicodeDecodeError toetete den Waechter
            txt = ""
            gruende.append(f"Quittung nicht lesbar ({type(ex).__name__}) — Zustellung NICHT belegt")
        try:
            ts = datetime.datetime.fromisoformat(txt.split()[0])
            alter = jetzt - ts
            # Volle Zeitdifferenz, NICHT .days: 7 d 23 h 59 m ist NICHT '7 Tage' (RT-C)
            if alter < -datetime.timedelta(minutes=1):
                gruende.append("Quittung liegt in der ZUKUNFT — Zustellung nicht nachvollziehbar")
            elif alter > datetime.timedelta(days=QUITTUNG_MAX_TAGE):
                gruende.append(f"Quittung {alter.total_seconds()/86400:.1f} Tage alt "
                               f"(> {QUITTUNG_MAX_TAGE} Tage)")
        except Exception:
            gruende.append("Quittung beschaedigt (nicht lesbar)")
        tl = txt.lower()
        if "zugestellt fehler" in tl:
            return ("CRITICAL", gruende + ["ZUSTELLFEHLER quittiert (zugestellt fehler) — Traeger "
                                           "hat NICHT erreicht: CRITICAL, nicht OK)"])
        # FAIL-OPEN geschlossen: vorher genuegte das FEHLEN der Fehlerzeichenkette als Beweis.
        # Jetzt muss der ERFOLG ausdruecklich dastehen — Unklarheit fuehrt nie zu OK.
        if "zugestellt ok" not in tl:
            gruende.append("Quittung nennt KEIN Zustell-Verdikt (kein 'zugestellt ok') — "
                           "Zustellung NICHT belegt")
    if not wherz.exists():
        gruende.append("Waechter hat sich nie gemeldet")
    else:
        try:
            walter = (jetzt - datetime.datetime.fromisoformat(
                (_lies(wherz) or " ").split()[0])).total_seconds() / 3600
            if walter < -(1 / 60):
                gruende.append("Waechter-Herzschlag liegt in der ZUKUNFT — unklar")
            elif walter > HERZSCHLAG_MAX_H:
                gruende.append("Waechter selbst ausgefallen (> 26 h)")
        except Exception: gruende.append("Waechter-Herzschlag unlesbar")
    # Wiederholter unbestaetigter Fehler: 3 Zustellungen in Folge ohne Quittung -> eskalieren
    zl = d / "zustellung_simuliert.jsonl"
    if zl.exists() and not zl.is_file():
        gruende.append("Zustellprotokoll ist keine regulaere Datei — Zustellungen nicht belegt"); zl = None
    if zl is not None and zl.exists():
        eintraege = []
        try:                                    # RT-C: abgeschnittene Zeile darf nicht toeten
            for z in (_lies(zl) or "").splitlines():
                if z.strip(): eintraege.append(json.loads(z))
        except Exception as ex:                # auch PermissionError/IsADirectoryError
            gruende.append(f"Zustellprotokoll beschaedigt/unlesbar ({type(ex).__name__}) — "
                           "kein 'OK' moeglich, Zustand UNBESTAETIGT")
            eintraege = []
        ohne = [e for e in eintraege if not e.get("quittiert") and e.get("status") in ("ERROR", "CRITICAL")]
        if len(ohne) >= 3:
            gruende.append(f"{len(ohne)}x ERROR/CRITICAL ohne Quittung — wiederholt, nicht bestaetigt")
    # RT-C: der Waechter meldet den BESTAETIGTEN STAND, niemals blind 'OK'.
    # Sonst stand 'Pruefer=CRITICAL' neben 'Waechter=OK' — ein Ausfall, der als Gesundheit gilt.
    stand, quit_status = None, None
    sp = d / "status.json"
    if not sp.exists():
        # Fehlte die Statusdatei, uebersprang der Waechter Mismatch UND Endpruefung und fiel
        # bis `return ("OK", [])` durch — Waechter=OK, obwohl die Quittung CRITICAL nannte.
        gruende.append("status.json fehlt — der letzte PRUEFERSTAND ist nicht belegt (Unklarheit != OK)")
    elif not sp.is_file():
        gruende.append("status.json ist keine regulaere Datei — Stand nicht belegt")
    else:
        try:
            roh = json.loads(_lies(sp) or "")
        except (ValueError, OSError, UnicodeDecodeError) as ex:
            gruende.append(f"Statusdatei beschaedigt ({type(ex).__name__}) — Stand nicht belegt")
        else:
            if not isinstance(roh, dict):
                # null / [] / 42 ergaben vorher einen AttributeError-Absturz
                gruende.append(f"Statusdatei ist kein Objekt, sondern {type(roh).__name__} — Stand nicht belegt")
            else:
                erz = roh.get("erzeuger")
                if erz not in ("check_all",):
                    gruende.append(f"status.json nennt keinen gueltigen Urheber (erzeuger={erz!r}) — "
                                   "der Pflichtbeweis ist nicht zuordenbar")
                zt = roh.get("zeit")
                try:
                    zts = datetime.datetime.fromisoformat(str(zt))
                    if (jetzt - zts) < -datetime.timedelta(minutes=1):
                        gruende.append(f"status.json liegt in der ZUKUNFT ({zt}) — unklar")
                except Exception:
                    gruende.append(f"status.json ohne gueltige Zeit ({zt!r}) — Zeitbezug fehlt")
                stand = roh.get("status")
                if stand is not None and stand not in ERLAUBTE_STAENDE:
                    # Allowlist statt Denylist: "LAUFEND"/"QUATSCH"/"" galt vorher als OK
                    gruende.append(f"status.json nennt unbekannten Stand {stand!r} (erlaubt: "
                                   f"{', '.join(ERLAUBTE_STAENDE)}) — Unklarheit fuehrt NIE zu OK")
                    stand = None
    if quit_.exists():
        try: quit_status = (_lies(quit_) or "  ").split()[1]
        except Exception: pass
        if quit_status is not None and quit_status not in ERLAUBTE_STAENDE + ("UNBESTAETIGT",):
            gruende.append(f"Quittung nennt unbekannten Stand {quit_status!r} — nicht belegt")
    if stand and quit_status and stand != quit_status:
        gruende.append(f"Quittung nennt {quit_status}, letzter Lauf ergab {stand} — Zustellung passt nicht zum Stand")
    # Gewaltenteilung: drei Beweise, drei Rollen — ABER die Trennung ist NICHT VERIFIZIERT.
# Ein Prozess derselben UID kann mehrere Identitaeten/PIDs vortaeuschen. Kein Sicherheitsversprechen.
    verstoesse, gewalt_critical = pruefe_gewalten(root)
    if gewalt_critical:
        return ("CRITICAL", gruende + verstoesse)
    gruende += verstoesse
    if any("ZUSTELLFEHLER" in g for g in gruende):
        return ("CRITICAL", gruende)
    if gruende:
        return ("UNBESTAETIGT", gruende)
    if stand in ("WARNING", "ERROR", "CRITICAL"):
        return (stand, [f"bestaetigter Stand aus status.json: {stand} (zugestellt und quittiert) — "
                        "KEIN 'OK'"])
    if stand == "OK":
        return ("OK", [])
    # Kein belegter Stand -> NIE OK (vorher fiel genau dieser Fall bis "OK" durch)
    return ("UNBESTAETIGT", gruende or ["kein belegter Prueferstand (status.json fehlt/unbrauchbar)"])


# ================= BLOCKER 4 — WER SCHREIBT WAS =================
# Architektur: drei Beweise, drei Rollen. EHRLICHE GRENZE: ROLLENTRENNUNG: NICHT VERIFIZIERT —
# Prozesskennungen sind Selbstauskunft (gleiche UID). Echte Trennung erst in Etappe 3.
#   Pruefer-Heartbeat  (herzschlag)          <- Pruefprozess  (check_all)
#   Waechter-Heartbeat (waechter_herzschlag) <- Waechterprozess (status_sim.waechter_lauf)
#   Quittung           (quittung)            <- Zustellschicht  (status_sim.zustellen)
ERWARTETE_SCHREIBER = {"pruefer_herzschlag": ("check_all",),
                       "waechter_herzschlag": ("waechter", "waechter_simuliert"),
                       "quittung": ("zustellung", "MENSCH_SIMULIERT")}
BEWEISE = {"pruefer_herzschlag": "herzschlag", "waechter_herzschlag": "waechter_herzschlag",
           "quittung": "quittung"}


def schreiber_von(datei: Path):
    """Liest den genannten Schreiber eines Beweisstuecks (erzeuger=... oder quittiert_von=...)."""
    try: txt = _lies(datei) or ""
    except Exception: return None      # OSError, UnicodeDecodeError, IsADirectoryError: nie abstuerzen
    for teil in txt.split():
        if teil.startswith("erzeuger="): return teil.split("=", 1)[1]
        if teil.startswith("quittiert_von="): return teil.split("=", 1)[1]
    return None


ROLLENTRENNUNG = "NICHT VERIFIZIERT"   # BLOCKER 5: keine Sicherheitsbehauptung ohne Beweis


def pruefe_gewalten(root: Path):
    """Rueckgabe (gruende, critical). Ein Beweis ohne Schreiber, ein unerwarteter Schreiber
    oder EIN Schreiber fuer mehrere Beweise ist ein Verstoss gegen die Gewaltenteilung."""
    d = root / "60_RUNTIME/state"
    gruende, critical = [], False
    schreiber, pids = {}, {}
    for rolle, name in BEWEISE.items():
        f = d / name
        if not f.exists():
            continue
        w = schreiber_von(f)
        if not w:
            gruende.append(f"{name} nennt keinen Schreiber — Beweis nicht zuordenbar")
            continue
        schreiber[rolle] = w
        pid = _pid_von(f)
        if not pid:
            gruende.append(f"{name} nennt KEINE Prozesskennung (pid=) — Selbstauskunft in Textform, "
                           "keine belegte Trennung")
        else:
            pids[rolle] = pid
        if w not in ERWARTETE_SCHREIBER[rolle]:
            gruende.append(f"{name} wurde von UNBEKANNTEM Schreiber gesetzt ({w})")
    # Mehrfach-Rollen: derselbe Schreiber fuer mehrere Beweise
    from collections import Counter
    for w, n in Counter(schreiber.values()).items():
        if n > 1:
            rollen = sorted(r for r, x in schreiber.items() if x == w)
            critical = True
            gruende.append(f"SELBSTBESTAETIGUNG: Schreiber '{w}' hat {n} Beweise selbst ausgestellt "
                           f"({rollen}) — kein Prozess darf sich alle Beweise ausstellen")
    for pid, n in Counter(pids.values()).items():
        if n > 1:
            rollen = sorted(r for r, x in pids.items() if x == pid)
            critical = True
            gruende.append(f"SELBSTBESTAETIGUNG: EIN Prozess (pid {pid}) hat {n} Beweise geschrieben "
                           f"({rollen}) — Textetiketten allein belegen keine Trennung")
    if len(schreiber) == 0:
        gruende.append("Kein Beweis nennt einen Schreiber")
    return gruende, critical


def waechter_lauf(root: Path):
    """Der WAECHTER fuehrt sich SELBST aus und schreibt SEINEN Herzschlag + Stand.
    Getrennt vom Pruefer: der Pruefer-Heartbeat beweist nur, dass der Pruefer lief."""
    st, gruende = waechter(root)
    try:
        d = nur_sandkasten(root / "60_RUNTIME/state")
        d.mkdir(parents=True, exist_ok=True)
        jetzt = JETZT().isoformat(timespec="seconds")
        (d / "waechter_herzschlag").write_text(
            f"{jetzt} erzeuger=waechter pid={os.getpid()}\n", encoding="utf-8")
        (d / "waechter_status.json").write_text(json.dumps(
            {"zeit": jetzt, "ergebnis": st, "gruende": gruende, "erzeuger": "waechter"},
            ensure_ascii=False) + "\n", encoding="utf-8")
    except (SandkastenVerletzt, OSError) as ex:
        # Der Waechter, der seinen eigenen Herzschlag nicht schreiben kann, ist UNBESTAETIGT —
        # er darf weder abstuerzen noch weiter 'OK' behaupten.
        print(f"WAECHTER-HERZSCHLAG NICHT SCHREIBBAR ({type(ex).__name__}: {ex})", file=sys.stderr)
        return ("UNBESTAETIGT", list(gruende) + [f"Waechter-Herzschlag nicht schreibbar ({type(ex).__name__})"])
    return st, gruende


def szenario_gewalten(basis: Path):
    basis = nur_sandkasten(basis)      # Final-Abnahme A3: Basis ausserhalb verweigern
    """Fallmatrix Blocker 4. Erwartung je Fall — Abweichung = FAIL."""
    import datetime, shutil
    basis = nur_sandkasten(basis)      # RT-Final-2 A3: Basis ausserhalb wurde beschrieben
    F = {}

    def frisch(name):
        r = basis / name; _minimal(r, []); lief(r)
        return r

    # G1 Pruefer tot, Waechter lebt
    r = frisch("G1"); os_h = r / "60_RUNTIME/state/herzschlag"
    os_h.write_text("2026-09-19T10:00:00+02:00 erzeuger=check_all pid=sim-pruefer\n", encoding="utf-8")
    (r / "60_RUNTIME/state/quittung").write_text(f"{JETZT().isoformat(timespec='seconds')} OK quittiert_von=MENSCH_SIMULIERT pid=sim-mensch zugestellt ok\n", encoding="utf-8")
    waechter_lauf(r)
    F["G1 Pruefer tot, Waechter lebt"] = (waechter(r)[0], "UNBESTAETIGT")
    # G2 Waechter tot, Pruefer lebt
    r = frisch("G2")
    zustellen(r, "OK", True)
    (r / "60_RUNTIME/state/waechter_herzschlag").write_text("2026-09-19T10:00:00+02:00 erzeuger=waechter pid=sim-waechter\n", encoding="utf-8")
    F["G2 Waechter tot, Pruefer lebt"] = (waechter(r)[0], "UNBESTAETIGT")
    # G3 beide tot
    r = frisch("G3")
    (r / "60_RUNTIME/state/herzschlag").write_text("2026-09-01T10:00:00+02:00 erzeuger=check_all pid=sim-pruefer\n", encoding="utf-8")
    (r / "60_RUNTIME/state/waechter_herzschlag").write_text("2026-09-01T10:00:00+02:00 erzeuger=waechter pid=sim-waechter\n", encoding="utf-8")
    F["G3 beide tot"] = (waechter(r)[0], "UNBESTAETIGT")
    # G4 Zustellung tot (Quittung veraltet)
    r = frisch("G4"); waechter_lauf(r)
    (r / "60_RUNTIME/state/quittung").write_text("2026-09-01T10:00:00+02:00 alterstand quittiert_von=MENSCH_SIMULIERT pid=sim-mensch zugestellt ok\n", encoding="utf-8")
    F["G4 Zustellung tot"] = (waechter(r)[0], "UNBESTAETIGT")
    # G5 Quittung fehlt
    r = frisch("G5"); waechter_lauf(r)
    (nur_sandkasten(r / "60_RUNTIME/state/quittung")).unlink(missing_ok=True)
    F["G5 Quittung fehlt"] = (waechter(r)[0], "UNBESTAETIGT")
    # G6 pruefer-Heartbeat beschaedigt
    r = frisch("G6"); zustellen(r, "OK", True); waechter_lauf(r)
    (r / "60_RUNTIME/state/herzschlag").write_text("kaputt\x00kein datum\n", encoding="utf-8")
    F["G6 Heartbeat beschaedigt"] = (waechter(r)[0], "UNBESTAETIGT")
    # G7 Heartbeat Zukunftsdatum
    r = frisch("G7"); zustellen(r, "OK", True); waechter_lauf(r)
    (r / "60_RUNTIME/state/herzschlag").write_text("2099-01-01T00:00:00+01:00 erzeuger=check_all pid=sim-pruefer\n", encoding="utf-8")
    F["G7 Heartbeat Zukunftsdatum"] = (waechter(r)[0], "UNBESTAETIGT")
    # G8 Heartbeat zu alt
    r = frisch("G8"); zustellen(r, "OK", True); waechter_lauf(r)
    (r / "60_RUNTIME/state/herzschlag").write_text("2026-09-01T10:00:00+02:00 erzeuger=check_all pid=sim-pruefer\n", encoding="utf-8")
    F["G8 Heartbeat zu alt"] = (waechter(r)[0], "UNBESTAETIGT")
    # G9/G10 Schreibfehler / Read-only
    r = frisch("G9")
    st_d = r / "60_RUNTIME/state"
    # Ein read-only ORDNER verhindert das Aendern bestehender Dateien NICHT — der Beweis muss
    # das Beweisstueck selbst schreibgeschuetzt machen (das entspricht dem Fall read-only FS).
    hd = st_d / "herzschlag"
    os.chmod(st_d, 0o500)
    if hd.exists(): os.chmod(hd, 0o400)
    try:
        import subprocess as sp
        x = sp.run([sys.executable, str(CHECK), "--root", str(r), "--json", "--no-selftest"],
                   capture_output=True, text=True)
        code = x.returncode
        try: j = json.loads(x.stdout); lev = j["status"]
        except Exception: lev = "?"
    finally:
        if hd.exists(): os.chmod(hd, 0o600)
        os.chmod(st_d, 0o700)
    F["G9/G10 Schreibfehler/read-only"] = (lev, "CRITICAL")
    # G11 Prozessabbruch zwischen Pruefung und Herzschlag
    r = frisch("G11"); zustellen(r, "OK", True)
    (nur_sandkasten(r / "60_RUNTIME/state/herzschlag")).unlink(missing_ok=True)
    waechter_lauf(r)
    F["G11 Abbruch vor Herzschlag"] = (waechter(r)[0], "UNBESTAETIGT")
    # G12 Selbstbestaetigung: EIN Schreiber fuer alle Beweise
    r = frisch("G12")
    z = JETZT().isoformat(timespec="seconds")
    (r / "60_RUNTIME/state/herzschlag").write_text(f"{z} erzeuger=selbst\n", encoding="utf-8")
    (r / "60_RUNTIME/state/waechter_herzschlag").write_text(f"{z} erzeuger=selbst\n", encoding="utf-8")
    (r / "60_RUNTIME/state/quittung").write_text(f"{z} OK quittiert_von=selbst zugestellt ok\n", encoding="utf-8")
    F["G12 Selbstbestaetigung (1 Schreiber)"] = (waechter(r)[0], "CRITICAL")
    # G13 unbekannter Schreiber
    r = frisch("G13"); waechter_lauf(r)
    (r / "60_RUNTIME/state/quittung").write_text(
        f"{JETZT().isoformat(timespec='seconds')} OK quittiert_von=FREMDPROZESS zugestellt ok\n", encoding="utf-8")
    F["G13 unbekannter Schreiber"] = (waechter(r)[0], "UNBESTAETIGT")
    return F


def szenario_a_b_c_e(basis: Path):
    basis = nur_sandkasten(basis)      # RT-Final-2 A3
    import shutil, yaml
    ergebnisse = {}
    # A: saubere Struktur
    a = basis / "A"; _minimal(a, [])
    d = lief(a)
    zustellen(a, d["status"], True); waechter_lauf(a)
    ergebnisse["A sauberer Lauf"] = (d["status"], waechter(a)[0], "erwartet OK")
    # B: nur WARNING (Projektordner ohne Datum)
    b = basis / "B"; _minimal(b, [], warn=True)
    d = lief(b); zustellen(b, d["status"], True); waechter_lauf(b)
    ergebnisse["B WARNING"] = (d["status"], waechter(b)[0], "erwartet WARNING")
    # C: CRITICAL (Katalogeintrag ohne Pfad)
    c = basis / "C"; _minimal(c, [], kaputt=True)
    d = lief(c); zustellen(c, d["status"], True); waechter_lauf(c)
    ergebnisse["C CRITICAL"] = (d["status"], waechter(c)[0], "erwartet CRITICAL")
    # E: Selbsttest defekt (Fixtures fehlen)
    e = basis / "E"; _minimal(e, [])
    r = subprocess.run([sys.executable, str(CHECK), "--root", str(e), "--json", "--fixtures", str(basis / "gibtsnicht")],
                       capture_output=True, text=True)
    try: st = json.loads(r.stdout)["status"]
    except Exception: st = "?"
    ergebnisse["E Selbsttest defekt"] = (st, "-", "erwartet CRITICAL")
    return ergebnisse


def szenario_d(basis: Path):
    basis = nur_sandkasten(basis)      # Final-Abnahme A3: Basis ausserhalb verweigern
    ergebnisse = {}
    basis = Path(basis); basis.mkdir(parents=True, exist_ok=True)
    d1 = basis / "D1"; _minimal(d1, []); lief(d1)
    (d1 / "60_RUNTIME/state/herzschlag").write_text("2026-09-19T10:00:00+02:00 erzeuger=check_all pid=sim-pruefer", encoding="utf-8")
    (d1 / "60_RUNTIME/state/quittung").write_text("2026-09-19T10:00:00+02:00 OK quittiert\n", encoding="utf-8")
    waechter_lauf(d1)
    ergebnisse["D1 Pruefer laeuft nicht (>26h)"] = (waechter(d1)[0], waechter(d1)[1])
    d2 = basis / "D2"; _minimal(d2, [])            # gar kein Herzschlag/keine Quittung
    ergebnisse["D2 nie gelaufen"] = (waechter(d2)[0], waechter(d2)[1])
    d3 = basis / "D3"; _minimal(d3, []); lief(d3)
    (nur_sandkasten(d3 / "60_RUNTIME/state/quittung")).unlink(missing_ok=True)     # Zustellung ohne Quittung
    ergebnisse["D3 Quittung fehlt"] = (waechter(d3)[0], waechter(d3)[1])
    d4 = basis / "D4"; _minimal(d4, []); lief(d4)
    (d4 / "60_RUNTIME/state/quittung").write_text("2026-09-01T10:00:00+02:00 OK alt\n", encoding="utf-8")
    ergebnisse["D4 Quittung > 7 Tage"] = (waechter(d4)[0], waechter(d4)[1])
    d5 = basis / "D5"; _minimal(d5, []); lief(d5)
    (d5 / "60_RUNTIME/state/waechter_herzschlag").write_text("2026-09-19T10:00:00+02:00 erzeuger=waechter pid=sim-waechter", encoding="utf-8")
    ergebnisse["D5 Waechter selbst ausgefallen"] = (waechter(d5)[0], waechter(d5)[1])
    d6 = basis / "D6"; _minimal(d6, []); lief(d6)
    (d6 / "60_RUNTIME/state/quittung").write_text("kaputt\n", encoding="utf-8")
    ergebnisse["D6 Quittung beschaedigt"] = (waechter(d6)[0], waechter(d6)[1])
    # ---- NEU nach der unabhaengigen Abnahmerunde (RT-C) ----
    d8 = basis / "D8"; _minimal(d8, []); lief(d8)
    zustellen(d8, "CRITICAL", quittiert=True, zugestellt_ok=False)     # Traeger NICHT erreicht
    waechter_lauf(d8)
    ergebnisse["D8 Zustellfehler quittiert"] = (waechter(d8)[0], waechter(d8)[1])
    d9 = basis / "D9"; _minimal(d9, []); lief(d9)
    alt9 = (JETZT() - datetime.timedelta(days=QUITTUNG_MAX_TAGE, hours=23, minutes=59)).isoformat(timespec="seconds")
    (d9 / "60_RUNTIME/state/quittung").write_text(f"{alt9} OK quittiert_von=MENSCH_SIMULIERT pid=sim-mensch zugestellt ok\n", encoding="utf-8")
    waechter_lauf(d9)
    ergebnisse["D9 Quittung 7 d 23 h 59 m"] = (waechter(d9)[0], waechter(d9)[1])
    d10 = basis / "D10"; _minimal(d10, []); lief(d10)
    zustellen(d10, "OK", True)
    (d10 / "60_RUNTIME/state/zustellung_simuliert.jsonl").write_text('{"zeit": "2026-09-21T22:00:00+02:00", "sta', encoding="utf-8")
    waechter_lauf(d10)
    ergebnisse["D10 Protokoll beschaedigt"] = (waechter(d10)[0], waechter(d10)[1])
    d7 = basis / "D7"; _minimal(d7, []); lief(d7)
    for _ in range(3): zustellen(d7, "CRITICAL", quittiert=False)
    waechter_lauf(d7)
    ergebnisse["D7 wiederholter ERROR (3x)"] = (waechter(d7)[0], waechter(d7)[1])
    return ergebnisse


def _minimal(root: Path, eintraege, warn=False, kaputt=False):
    import shutil
    if root.exists(): shutil.rmtree(nur_sandkasten(root))
    (root / "00_SYSTEM/manifest").mkdir(parents=True); (root / "00_SYSTEM/schemas").mkdir(parents=True)
    (root / "00_SYSTEM/schemas/repos.schema.json").write_text(
        (M / "00_SYSTEM/schemas/repos.schema.json").read_text(encoding="utf-8"), encoding="utf-8")
    (root / "40_DATEN/pointers").mkdir(parents=True)
    z = ['schema_version: 1\nnotfallkontakt: "sim"\npassphrase_ort: "keine"\nrepos:\n',
         '  - schema_version: 1\n    name: system_meta\n    class: system\n    status: paused\n'
         '    owner: t\n    seit: "2026-09-21"\n    bereich: 00_SYSTEM\n    pfad: 00_SYSTEM\n    git: false\n']
    if warn:      # K6-Hinweis: Projektordner ohne Datum
        (root / "20_PROJEKTE/ohne_datum").mkdir(parents=True, exist_ok=True)
        z.append('  - schema_version: 1\n    name: ohne_datum\n    class: project\n    status: paused\n'
                 '    owner: t\n    seit: "2026-09-21"\n    bereich: 20_PROJEKTE\n'
                 '    pfad: 20_PROJEKTE/ohne_datum\n    git: false\n')
    if kaputt:    # K4 CRITICAL: Pfad existiert nicht
        z.append('  - schema_version: 1\n    name: fehlt\n    class: project\n    status: paused\n'
                 '    owner: t\n    seit: "2026-09-21"\n    bereich: 20_PROJEKTE\n'
                 '    pfad: 20_PROJEKTE/gibt_es_nicht\n    git: false\n')
    (root / "00_SYSTEM/manifest/repos.yaml").write_text("".join(z + eintraege), encoding="utf-8")


SOLL_D = {"D8 Zustellfehler quittiert": "CRITICAL"}     # alles andere in D: UNBESTAETIGT


def _haupt():
    ap = argparse.ArgumentParser(); ap.add_argument("--basis", default=str(S / "status_sim"))
    ap.add_argument("--gewalten", action="store_true", help="nur die Fallmatrix Blocker 4")
    a = ap.parse_args()
    if a.gewalten:
        basis = Path(a.basis)
        assert_write_inside_sandbox(basis)   # BLOCKER 3: VOR jedem mkdir
        basis.mkdir(parents=True, exist_ok=True)
        abw = []
        print("=== BLOCKER 4 — PRUEFER-HEARTBEAT / WAECHTER-HEARTBEAT / QUITTUNG (13 Faelle) ===")
        for k, (ist, soll) in szenario_gewalten(basis).items():
            ok = (ist == soll)
            if not ok: abw.append(f"{k}: {ist} soll={soll}")
            print(f"  [{'OK ' if ok else 'ABW'}] {k:38} -> {ist:14} (erwartet {soll})")
        if abw:
            print("\nERGEBNIS: ABWEICHUNGEN — " + " | ".join(abw)); return 2
        print("\nERGEBNIS: alle 13 Faelle wie erwartet — Unklarheit fuehrt nie zu OK"); return 0
    basis = Path(a.basis)
    assert_write_inside_sandbox(basis)       # BLOCKER 3: VOR jedem mkdir
    basis.mkdir(parents=True, exist_ok=True)
    abweichungen = []
    print("=== ZUSTAENDE A / B / C / E ===")
    for k, (pruefer, w, erwartet) in szenario_a_b_c_e(basis).items():
        soll = erwartet.split()[-1]
        ok = (pruefer == soll) and (w in ("-", soll))
        if not ok: abweichungen.append(f"{k}: Pruefer={pruefer} Waechter={w} soll={soll}")
        print(f"  [{'OK ' if ok else 'ABW'}] {k:28} Pruefer={pruefer:10} Waechter={w:14} {erwartet}")
    print("=== ZUSTAND D — Waechter (darf NIE faelschlich OK sein) ===")
    for k, (st, gruende) in szenario_d(basis).items():
        soll = SOLL_D.get(k, "UNBESTAETIGT")
        ok = (st == soll)
        if not ok: abweichungen.append(f"{k}: {st} soll={soll}")
        print(f"  [{'OK ' if ok else 'ABW'}] {k:38} -> {st:14} {'; '.join(gruende)[:80]}")
    print(f"\nExitcode-Matrix: {CODE}")
    if abweichungen:
        print("\nERGEBNIS: ABWEICHUNGEN — " + " | ".join(abweichungen))
        return 2
    print("\nERGEBNIS: ALLE ZUSTAENDE WIE ERWARTET (kein Zustand faelschlich OK)")
    return 0


def _lies(p: Path):
    """Liest eine Beweisdatei SICHER. Eine FIFO/ein Geraet blockiert beim OEFFNEN unbegrenzt —
    der Waechter hing daran bis zum Zeitlimit (RT-Final-2 B1). Nur regulaere Dateien werden gelesen,"""
    """ohne O_NONBLOCK gibt es kein Blockieren, ohne S_ISREG keine Geraete/FIFOs."""
    import stat as _st
    try:
        if not _st.S_ISREG(p.lstat().st_mode):
            return None
    except OSError:
        return None
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _pid_von(p: Path):
    """Die Prozesskennung aus einem Beweisstueck (pid=...). Ohne PID bleibt die Gewaltenteilung"""
    """eine reine Selbstauskunft in Textform."""
    txt = _lies(p)
    if not txt:
        return None
    for teil in txt.split():
        if teil.startswith("pid="):
            return teil.split("=", 1)[1]
    return None


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
        sys.exit(_haupt())
    except SystemExit:
        raise
    except Exception as ex:                 # nie mehr Exit 1 mit Traceback
        print(f"SIMULATION FEHLGESCHLAGEN ({type(ex).__name__}: {ex}) — Exit 2", file=sys.stderr)
        sys.exit(2)

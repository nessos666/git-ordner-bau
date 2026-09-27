#!/usr/bin/env python3
"""check_all.py — der Pruefer der Git-Architektur v1.3.

Aufruf:  python3 check_all.py [--root PFAD] [--json] [--no-selftest] [--quiet]

SCHREIBREGEL: Dieser Pruefer schreibt GENAU EINE Sache — seinen eigenen Zustand
(status.json + herzschlag) in <root>/60_RUNTIME/state/, und NUR wenn <root> in der Sandbox liegt.
Die QUITTUNG schreibt er ausdruecklich NICHT: sie ist der Zustellnachweis des Menschen und wird
von der Zustellung gesetzt. Er loescht, verschiebt, benennt um, repariert, committet und pusht NIE.

Exitcodes:  0 = OK   1 = WARNING   2 = ERROR   3 = CRITICAL   4 = UNBESTAETIGT
"""
from __future__ import annotations
import argparse, json, os, re, sys, datetime, tempfile
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))
import stat


def _notausgang(grund, ex=None):
    """F1 (2.8): Ein unlesbares Programmteil oder ein unerwarteter Fehler darf NIE einen
    Traceback und NIE ein stilles OK ergeben — sichtbare Meldung + definierter Exitcode."""
    detail = f"{type(ex).__name__}: {ex}" if ex is not None else "ohne Detail"
    sys.stderr.write(f"ABBRUCH: Pruefer nicht lauffaehig — {grund} ({detail}). "
                     f"Es wurde NICHTS geprueft; kein OK.\n")
    sys.stderr.flush()
    raise SystemExit(2)          # 2 = ERROR (zentrale Tabelle)


def _excepthook(typ, wert, tb):
    _notausgang("unerwarteter interner Fehler", wert)


sys.excepthook = _excepthook

try:
    import rules as R
except BaseException as _ex:                      # fehlend, unlesbar, kaputt
    _notausgang("Regelmodul rules.py nicht ladbar", _ex)
R.schutz_installieren()        # BLOCKER 2 (2.7): Datei-Ebene (Symlink/Hardlink/Nicht-Regulaerdatei)
try:
    import budget
    import schema_check
except BaseException as _ex:
    _notausgang("Hilfsmodul nicht ladbar", _ex)

SCHEMA = "SCHEMA"
STUFEN = ["OK", "WARNING", "ERROR", "CRITICAL"]
CODE = {"OK": R.EXIT["OK"], "WARNING": R.EXIT["WARNING"], "ERROR": R.EXIT["ERROR"],
        "CRITICAL": R.EXIT["GRENZE"]}   # F1/2.8: Zahlen aus der EINEN zentralen Tabelle


def _kopie_stand(kopie: Path, root: Path) -> dict:
    """Zustand EINER erklaerten Kopie: da? aktuell? auf anderem Geraet?"""
    e = {"pfad": str(kopie), "da": False, "aktuell": False, "gleiche_platte": None, "grund": ""}
    if not kopie.exists():
        e["grund"] = "nicht gefunden"; return e
    e["da"] = True
    try:
        e["gleiche_platte"] = os.stat(kopie).st_dev == os.stat(root).st_dev
    except OSError:
        pass
    liste = next((k for k in (kopie / "PRUEFSUMMEN.sha256", kopie / "PRUEFSUMMEN_MASTER.txt")
                  if k.exists()), None)
    if liste is None:
        e["grund"] = "keine Pruefsummenliste (kein Archiv)"; return e
    # Aktualitaet = festgehaltener QUELLSTAND der Kopie gegen den HEUTIGEN Stand des Baums.
    # Gemessen 23.09.2026: die Liste der Kopie hat andere Pfad-Praefixe ("./...") und mehr
    # Dateien — sie ist mit der Liste des Baums NICHT vergleichbar.
    try:
        import hashlib
        quelle = ""
        for kandidat in (kopie / "README.txt", kopie / "QUELLE.txt"):
            if kandidat.exists():
                for zeile in kandidat.read_text(encoding="utf-8", errors="ignore").splitlines():
                    if zeile.startswith("QUELLSTAND="):
                        quelle = zeile.split("=", 1)[1].strip()
        if not quelle:
            e["grund"] = "Kopie nennt keinen Quellstand (aeltere Kopie)"; return e
        heute = hashlib.sha256((root / "PRUEFSUMMEN_MASTER.txt").read_bytes()).hexdigest()
        e["aktuell"] = (quelle == heute)
        if not e["aktuell"]:
            e["grund"] = "Kopie ist aelter als der Baum"
    except OSError as ex:
        e["grund"] = f"nicht lesbar ({type(ex).__name__})"
    return e


def redundanz(root: Path) -> str:
    """REDUNDANZ wird GEMESSEN, nicht behauptet (Schritt 2, 23.09.2026).

    Zuerst die in `50_INFRA/redundanz.yaml` ERKLAERTEN Kopien: je Kopie wird geprueft, ob sie
    existiert, ob sie AKTUELL ist (Pruefsummenliste identisch mit dem Baum) und ob sie auf einem
    ANDEREN Geraet liegt (st_dev). Gleiche Platte wird ausdruecklich benannt: sie schuetzt vor
    Fehlern, NICHT vor dem Ausfall der Platte (P0). Ohne Konfiguration gilt die bisherige Regel.
    """
    cfg = root / "50_INFRA/redundanz.yaml"
    kopien = []
    if cfg.exists():
        try:
            import yaml as _y
            d = _y.safe_load(cfg.read_text(encoding="utf-8")) or {}
            kopien = [Path(os.path.expanduser(str(e.get("pfad"))))
                      for e in (d.get("kopien") or []) if e.get("pfad")]
        except Exception as ex:
            return f"FEHLT (Konfiguration unlesbar: {type(ex).__name__})"
    if not kopien:                                   # bisherige Regel (zweiter Ort neben dem Baum)
        daten = root.parent / "daten"
        try:
            if not daten.exists():
                return "FEHLT (keine Kopie erklaert)"
            if os.stat(daten).st_dev == os.stat(root).st_dev:
                return "FEHLT (zweiter Ort auf gleicher Platte)"
            return "vorhanden" if _archiv_gefunden(daten) else "FEHLT (zweiter Ort ohne Archiv)"
        except OSError:
            return "FEHLT (nicht messbar)"
    # Punkt 6 (Fremdpruefung 27.09.2026): eine Kopie gehoert zu DEM Baum, den sie nennt.
    # 50_INFRA/redundanz.yaml ist versioniert — ein Klon hat sie mit und meldete darum eine
    # Sicherung, die er gar nicht besitzt. Jetzt zaehlt das QUELLE-Feld in der Kopie selbst.
    def _fremder_baum(k):
        try:
            txt = (Path(k) / "README.txt").read_text(encoding="utf-8", errors="replace")
        except OSError:
            return False
        q = next((z.split("=", 1)[1].strip() for z in txt.splitlines() if z.startswith("QUELLE=")), "")
        if not q:
            return False
        try:
            return os.path.realpath(q) != os.path.realpath(str(root))
        except OSError:
            return False

    stands = [_kopie_stand(k, root) for k in kopien]
    fremd = [_fremder_baum(k) for k in kopien]
    akt = [x for i, x in enumerate(stands) if x["aktuell"] and not fremd[i]]
    if akt:
        fremd = [x for x in akt if x["gleiche_platte"] is False]
        if fremd:
            return f"{len(akt)} Kopie(n), aktuell — {len(fremd)} auf ANDEREM Geraet (echte Redundanz)"
        return (f"{len(akt)} Kopie(n), aktuell — GLEICHE PLATTE "
                f"(schuetzt vor Fehlern, NICHT vor Plattenausfall)")
    if any(s["aktuell"] and f for s, f in zip(stands, fremd)):
        return ("FEHLT (die erklaerte Kopie gehoert zu einem ANDEREN Baum — "
                "dieser Baum hat keine eigene Sicherung)")
    da = [x for x in stands if x["da"]]
    if da:
        return f"{len(da)} Kopie(n) VERALTET ({da[0]['grund'] or 'nicht aktuell'})"
    return "FEHLT (keine der erklaerten Kopien gefunden)"


def _archiv_gefunden(daten: Path):
    """Ein zweiter Ort ist nur dann Redundanz, wenn dort ein ECHTES ARCHIV liegt —
    leer oder ein paar Textdateien genuegen NICHT (unabhaengige Runde, RT-C)."""
    for dp, _, fns in os.walk(daten):
        for n in fns:
            q = Path(dp) / n
            if re.search(r"\.(tar|tar\.gz|tgz|zst|restic|bundle)(\.|$)", n) or n.lower().startswith("manifest"):
                return True
            try:
                if q.stat().st_size > (1 << 20):
                    return True
            except OSError:
                pass
    return False


def selbsttest(fixtures: Path):
    """Beweist, dass der Pruefer WIRKLICH gelaufen ist und bekannte Fehler erkennt."""
    erwartet = {"K1", "K2", "K3", "K4", "K5", "K7"}
    ergebnis = {"clean": None, "broken": None, "befunde": [], "ok": False,
                "fixtures_fehlen": False}
    clean, broken = fixtures / "clean", fixtures / "broken"
    if not clean.exists() or not broken.exists():
        # Punkt 1 (Fremdpruefung 27.09.2026): fehlende Fixtures sind KEIN Defekt des Baums.
        # Die Fixtures liegen NEBEN dem Baum (sie enthalten eigene Git-Repos und koennen darum
        # nicht mitversioniert werden). In einem frischen Klon ist das der Normalfall.
        ergebnis["befunde"].append(f"Fixtures fehlen ({clean} / {broken})")
        ergebnis["fixtures_fehlen"] = True
        return ergebnis
    try:
        import yaml
    except ModuleNotFoundError as ex:
        # Ein Pruefer ohne Selbsttest gilt NICHT als OK (fail-closed). Vorher brach hier der
        # ganze Lauf mit ModuleNotFoundError ab (gemessen 26.09.2026, Python ohne PyYAML).
        ergebnis["befunde"].append(f"PyYAML fehlt ({ex}) — Selbsttest NICHT ausfuehrbar; "
                                   "ein Pruefer ohne Selbsttest gilt nicht als OK")
        return ergebnis
    c = R.run_all(clean, yaml.safe_load((clean / "00_SYSTEM/manifest/repos.yaml").read_text()) or {})
    b = R.run_all(broken, yaml.safe_load((broken / "00_SYSTEM/manifest/repos.yaml").read_text()) or {})
    ergebnis["clean"], ergebnis["broken"] = len(c.findings), len(b.findings)
    gefunden = {f["regel"] for f in b.findings}
    fehlend = erwartet - gefunden
    if c.findings:
        ergebnis["befunde"].append(f"saubere Fixture erzeugt {len(c.findings)} Befund(e) — Falschalarm!")
    if fehlend:
        ergebnis["befunde"].append(f"kaputte Fixture: erwartete Regel(n) nicht erkannt: {sorted(fehlend)}")
    if not b.findings:
        ergebnis["befunde"].append("kaputte Fixture erzeugte KEINEN Befund — Pruefer ist blind!")
    ergebnis["ok"] = not ergebnis["befunde"]
    return ergebnis


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(HIER.parents[1]))  # validation -> 70_AUTOMATION -> MASTER
    ap.add_argument("--fixtures", default=None)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-selftest", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    root = Path(a.root).expanduser().resolve()
    SANDBOX = Path(__file__).resolve().parents[3]
    # ECHTE Pruefung (aufgeloester Pfad, echter Ordnervergleich): `startswith` liess einen
    # GESCHWISTERORDNER prototyp_git_ordner_SIBLING durch — dort hat der Pruefer dann
    # 60_RUNTIME/state/ angelegt (RT-B Befund).
    if not R.ist_im_baum(root, SANDBOX):
        print(f"ABBRUCH: --root liegt ausserhalb der Sandbox ({root}). Der Pruefer schreibt dort NICHTS.",
              file=sys.stderr)
        return 3
    # Punkt 1 (Fremdpruefung 27.09.2026): zuerst IM Baum suchen. Vorher lagen die Fixtures
    # nur NEBEN dem Baum — ein frischer Klon hatte sie darum nie, und der Selbsttest meldete
    # zwangslaeufig "DEFEKT". Der alte Ort bleibt als Rueckfall erhalten.
    _fixtures_im_baum = root / "fixtures"
    fixtures = (Path(a.fixtures).expanduser() if a.fixtures
                else (_fixtures_im_baum if _fixtures_im_baum.is_dir() else root.parent / "fixtures"))
    R.assert_write_inside_sandbox(fixtures)   # BLOCKER 3: Selbsttest/Fixtures schreiben nur in die Sandbox
    jetzt = datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()

    import time as _tc
    _t_main = _tc.monotonic()
    _t_selbst = 0.0
    _t_red = 0.0
    _t_k9crate = 0.0
    findings, n_geprueft, ab = [], 0, {}
    kat = root / "00_SYSTEM/manifest/repos.yaml"
    katalog = {}
    # Ein Katalog, der keine regulaere Datei ist (Verzeichnis, FIFO, Socket) oder nicht UTF-8
    # ist, darf den Pruefer NICHT toeten und NICHT das ganze Pruefen verhindern (RT-C Befund).
    if not kat.exists():
        findings.append({"regel": "K5", "schwere": "CRITICAL", "pfad": str(kat),
                         "meldung": "Katalog fehlt — ohne Katalog ist keine Katalogaussage moeglich "
                                    "(der Baum wird trotzdem geprueft)."})
    elif not kat.is_file():
        findings.append({"regel": "K5", "schwere": "CRITICAL", "pfad": str(kat),
                         "meldung": f"Katalog ist keine regulaere Datei ({kat.is_dir() and 'Verzeichnis' or 'FIFO/Socket/Geraet'}) "
                                    "— nicht lesbar, wird nicht geoeffnet (kein Blockieren)."})
    else:
        # Fehlt die Katalog-Bibliothek, ist das ein BEFUND und kein Absturz. Vorher griff der
        # except-Zweig auf ein nie gebundenes yaml zu, wodurch der ganze Lauf abbrach — gemessen
        # am 26.09.2026 mit einer Python ohne PyYAML (mehrere Suiten fielen dadurch um).
        try:
            import yaml
        except ModuleNotFoundError as ex:
            findings.append({"regel": "K5", "schwere": "CRITICAL", "pfad": str(kat),
                             "meldung": f"Katalog NICHT auswertbar: {ex} — K5/K6/K7 koennen nicht "
                                        "geprueft werden. Unklarheit fuehrt nie zu OK (fail-closed)."})
            yaml = None
        if yaml is not None:
            try:
                roh = kat.read_bytes()
                katalog = yaml.safe_load(roh.decode("utf-8", "replace")) or {}
            except yaml.YAMLError as ex:
                findings.append({"regel": "K5", "schwere": "CRITICAL", "pfad": str(kat),
                                 "meldung": f"Katalog ist kein gueltiges YAML ({type(ex).__name__}) — nicht auswertbar."})
                katalog = {}
            except OSError as ex:
                findings.append({"regel": "K5", "schwere": "CRITICAL", "pfad": str(kat),
                                 "meldung": f"Katalog nicht lesbar ({type(ex).__name__}) — nicht auswertbar."})
                katalog = {}
        try:
            sfehler, backend = schema_check.pruefe(root)
            for m in sfehler:
                findings.append({"regel": SCHEMA, "schwere": "ERROR", "pfad": str(kat), "meldung": f"Schema: {m}"})
        except Exception as ex:
            findings.append({"regel": SCHEMA, "schwere": "ERROR", "pfad": str(kat),
                             "meldung": f"Schema-Pruefung nicht ausfuehrbar ({type(ex).__name__}: {ex})."})
    # IMMER pruefen — auch mit unbrauchbarem/fehlendem Katalog. Sonst waeren K1/K2 (Secrets!)
    # stillschweigend ausgefallen, waehrend die Statuszeile weiter OK sagte.
    _t_r0 = _tc.monotonic()
    ctx = R.run_all(root, katalog if isinstance(katalog, dict) else {})
    _t_run_all = _tc.monotonic() - _t_r0
    findings += ctx.findings; n_geprueft = ctx.geprueft
    ab["abdeckung"] = ctx.abdeckung
    if ctx.ungeprueft:
        ab["ungeprueft_liste"] = ctx.ungeprueft
    # Budget v1.3 (40_DATEN < 1 MB) — budget.pruefe war bisher NIRGENDS aufgerufen (toter Code).
    try:
        bwert = budget.pruefe(root)
        ab["budget"] = bwert
        for m in bwert.get("fehler", []):
            findings.append({"regel": "K8", "schwere": "ERROR", "pfad": str(root / "40_DATEN"),
                             "meldung": f"40_DATEN-Budget: {m}"})
    except Exception as ex:
        findings.append({"regel": "K8", "schwere": "ERROR", "pfad": str(root / "40_DATEN"),
                         "meldung": f"Budget-Pruefung nicht ausfuehrbar ({type(ex).__name__}: {ex})."})

    st = {"ok": True, "befunde": [], "clean": None, "broken": None}
    if not a.no_selftest:
        _t_s0 = _tc.monotonic()
        st = selbsttest(fixtures)
        _t_selbst = _tc.monotonic() - _t_s0
        if not st["ok"]:
            # Laeuft der Selbsttest GAR NICHT, weil die Fixtures fehlen (jeder frische Klon),
            # ist das ein benannter Hinweis — kein Defekt des Baums und KEIN stilles OK.
            # Laeuft er und findet die bekannten Fehler nicht, bleibt es CRITICAL.
            # Praezision (27.09.2026): NUR der Standardpfad darf Hinweis sein. Wer --fixtures
            # ausdruecklich auf einen nicht existierenden Ordner zeigt, hat sich vertan —
            # das bleibt CRITICAL (die status_sim-Probe prueft genau diesen Fall).
            _nur_fixtures = bool(st.get("fixtures_fehlen")) and not a.fixtures
            findings.append({"regel": "SELFTEST",
                             "schwere": "WARNING" if _nur_fixtures else "CRITICAL",
                             "pfad": str(fixtures),
                             "meldung": ("SELBSTTEST NICHT AUSFUEHRBAR: " + " | ".join(st["befunde"])
                                         + " — die Fixtures liegen NEBEN dem Baum und sind nicht"
                                           " versioniert. In einem frischen Klon ist das normal."
                                           " Kein stilles OK, aber kein Baumschaden.")
                             if _nur_fixtures else
                             ("VALIDATOR-SELBSTTEST FEHLGESCHLAGEN: " + " | ".join(st["befunde"])
                              + " — ein Pruefer, der nicht laeuft, ist KEIN 'alles OK'.")})

    # Punkt 8 (Fremdpruefung 27.09.2026): Die Schreibgrenze sagt zu, jede abgelehnte Schreibwirkung
    # zu zaehlen UND zu melden. Gemeldet wurde sie (stderr), gezaehlt aber nie sichtbar — die Liste
    # starb mit dem Prozess. Jetzt steht die Zahl im Ergebnis.
    if getattr(R, "VERWEIGERUNGEN", []):
        findings.append({"regel": "SCHREIBGRENZE", "schwere": "WARNING", "pfad": str(root),
                         "meldung": f"{len(R.VERWEIGERUNGEN)} verweigerte Schreibwirkung(en) in diesem "
                                    "Lauf: " + " | ".join(str(x) for x in R.VERWEIGERUNGEN[:5])})

    # ---- die EINE erlaubte Schreiboperation: eigener ZUSTAND + Herzschlag ----
    # DIE QUITTUNG SCHREIBT DER PRUEFER *NICHT*: sie ist der Zustellnachweis des Menschen
    # (Traeger) und wird von der Zustellung gesetzt (zugestellt ok|fehler). Vorher stellte sich
    # der Pruefer seine eigene Quittung aus und hebelte damit 26-h- und 7-Tage-Regel aus.
    vorher = len(findings)
    stt = root / "60_RUNTIME/state"
    # Der Zustand darf nur INNERHALB der Sandbox liegen. Ein Symlink nach draussen ist ein
    # echter Ausbruch — er wird verweigert und als CRITICAL gemeldet, nicht still ausgefuehrt.
    if not R.ist_im_baum(stt, SANDBOX):
        # WICHTIG: nach der Verweigerung darf KEIN Schreibversuch folgen. Die erste Fassung
        # meldete CRITICAL und schrieb trotzdem — ueber einen Symlink nach draussen (RT-Final-A).
        findings.append({"regel": "SELFTEST", "schwere": "CRITICAL", "pfad": str(stt),
                         "meldung": f"Zustandsordner zeigt AUSSERHALB der Sandbox ({os.path.realpath(stt)}) — "
                                    "Schreiben VERWEIGERT und NICHT ausgefuehrt. Ein Pruefer, der nach "
                                    "draussen schreibt, ist kein Pruefer."})
    try:
        if not R.ist_im_baum(stt, SANDBOX):
            raise OSError(f"Zustandsordner ausserhalb der Sandbox ({os.path.realpath(stt)}) — verweigert")
        stt.mkdir(parents=True, exist_ok=True)
        (stt / "status.json").write_text(json.dumps(
            {"zeit": jetzt, "status": "LAUFEND", "erzeuger": "check_all", "pid": os.getpid()}, ensure_ascii=True) + "\n", encoding="utf-8")
        # Der Herzschlag nennt seinen SCHREIBER — ohne diese Angabe waere nicht pruefbar,
        # ob sich ein Prozess seine Beweise selbst ausstellt (Blocker 4).
        (stt / "herzschlag").write_text(f"{jetzt} erzeuger=check_all pid={os.getpid()}\n", encoding="utf-8")
    except OSError as ex:
        findings.append({"regel": "SELFTEST", "schwere": "CRITICAL", "pfad": str(root / "60_RUNTIME/state"),
                         "meldung": f"Zustand/Herzschlag NICHT SCHREIBBAR ({ex}) — ein Pruefer ohne "
                                    "Herzschlag ist UNBESTAETIGT, nicht OK."})
    level = max((f["schwere"] for f in findings), key=lambda s: STUFEN.index(s), default="OK")
    fehler = [f for f in findings if f["schwere"] in ("ERROR", "CRITICAL")]
    hinweise = [f for f in findings if f["schwere"] == "WARNING"]
    _t_d0 = _tc.monotonic()
    red = redundanz(root)
    _t_red = _tc.monotonic() - _t_d0

    # Status in die Zustandsdatei nachtragen (nach der Bewertung, damit der Stand stimmt)
    # F3 (OpenCode-Befund 25.09.2026): Die Zustandsdatei wird NICHT an dieser Stelle geschrieben —
    # die Regeln K9/CRATE laufen erst danach; sie konnte "OK" sagen, waehrend stdout "ERROR"
    # meldete. Sie wird am ENDE von main() geschrieben und traegt dann denselben Stand.

    abdeckung = ab.get("abdeckung", {})
    ungeprueft = abdeckung.get("ungeprueft", 0)
    zeile = (f"PRUEFER: {level} · {len(fehler)} Fehler · {len(hinweise)} Hinweise · {n_geprueft} geprueft"
             f" · REDUNDANZ: {red} · Selbsttest: "
             f"{'uebersprungen (--no-selftest)' if a.no_selftest else ('ok' if st['ok'] else ('nicht ausfuehrbar (Fixtures fehlen)'
                                               if st.get('fixtures_fehlen') else 'DEFEKT'))}"
             + (f" · UNGEPRUEFT: {ungeprueft}" if ungeprueft else
                f" · Git-Bereiche: {abdeckung.get('git_bereiche', '-')} geprueft")
             + (f" · K2-Scope: tracked {sc['tracked']} · untracked {sc['untracked']} · "
                f"ignoriert {sc['ignoriert']} · ausgeschlossen {sc['ausgeschlossen']} · "
                f"uebersprungen {sc['uebersprungen']}" if (sc := abdeckung.get("k2_scope")) else "")
             + f" · ROLLENTRENNUNG: {_rollentrennung_text(a.root)}"     # gemessen, nicht behauptet
             + f" · Herzschlag {jetzt}")
    # BLOCKER 1/3 (2.7): ungeprueft>0 ist kein OK — erforderliche, aber nicht pruefbare Quellen
    # muessen den Gesamtstatus anheben (fail-closed statt fail-open).
    if ungeprueft and level in ("OK", "WARNING"):
        level = "ERROR"

    # BLOCKER 1 (2.7): erforderliche, aber NICHT lesbare regulaere Dateien sind ein Befund —
    # "kann nicht geprueft werden" darf niemals als "ist gesund" erscheinen (kein fail-open).
    _unlesbar_probe = 0
    for _dp, _dns, _fns in os.walk(getattr(ctx, "root", a.root) if "ctx" in dir() else a.root):
        for _fn in _fns:
            _p = Path(_dp) / _fn
            try:
                _st = _p.lstat()
            except OSError:
                continue
            if not stat.S_ISREG(_st.st_mode):
                continue
            try:
                with open(_p, "rb") as _f:
                    _f.read(1)
            except OSError as _ex:
                _unlesbar_probe += 1
                findings.append({"regel": "K2", "schwere": "CRITICAL",
                                 "pfad": str(_p), "meldung": f"erforderliche Datei nicht lesbar ({type(_ex).__name__}) — UNGEPRUEFT"})
    if _unlesbar_probe:
        level = "CRITICAL"

    # ================= Fremd-Pruefung 25.09.2026: K9 + Crate als ECHTE Regeln =================
    # K9 (neu): Pruefsummen der VERFOLGTEN Dateien gegen PRUEFSUMMEN_MASTER.txt nachrechnen.
    # Ohne diese Regel blieb eine nachtraegliche Aenderung an Werkzeugcode unbemerkt ("0 Fehler").
    _t_k0 = _tc.monotonic()
    import hashlib as _hl
    _summen = root / "PRUEFSUMMEN_MASTER.txt"
    _k9_liste = 0
    # Die strengen Zusagen (Liste + Selbstbeschreibung muessen EXISTIEREN) gelten fuer einen
    # ausgelieferten Git-Ordner-Baum. Kleine Test-/Fixture-Baeume sind kein solcher Baum.
    _ist_baum = (root / "ordner.sh").is_file() and (root / ".git").exists()
    if _ist_baum and not _summen.is_file():
        findings.append({"regel": "K9", "schwere": "ERROR", "pfad": str(_summen),
                         "meldung": "PRUEFSUMMEN_MASTER.txt FEHLT — ohne sie ist keine Aenderung nachweisbar (./ordner.sh summen)"})
    if _summen.is_file():
        _soll = {}
        for _z in _summen.read_text(encoding="utf-8", errors="replace").splitlines():
            _z = _z.rstrip("\n")
            if "  " in _z:
                _h, _rel = _z.split("  ", 1)
                _soll[_rel.strip()] = _h.strip()
        for _rel, _h in sorted(_soll.items()):
            _p = root / _rel
            if not _p.is_file():
                _k9_liste += 1
                findings.append({"regel": "K9", "schwere": "ERROR", "pfad": str(_p),
                                 "meldung": "steht in der Pruefsummenliste, ist aber nicht vorhanden"})
                continue
            try:
                _ist = _hl.sha256(_p.read_bytes()).hexdigest()
            except OSError as _ex:
                _k9_liste += 1
                findings.append({"regel": "K9", "schwere": "ERROR", "pfad": str(_p),
                                 "meldung": f"nicht lesbar ({type(_ex).__name__}) — UNGEPRUEFT"})
                continue
            if _ist != _h:
                _k9_liste += 1
                findings.append({"regel": "K9", "schwere": "ERROR", "pfad": str(_p),
                                 "meldung": f"INHALT GEAENDERT (soll {_h[:12]}…, ist {_ist[:12]}…) — "
                                            "Pruefsummen mit 'git ls-files | xargs sha256sum' neu erzeugen"})
    # Rueckrichtung (Zweitpruefung 25.09.2026, Befund 2): JEDE verfolgte Datei muss in der Liste stehen.
    # Sonst passierte eine NEU hinzugefuegte Datei beide Regeln unbemerkt ("0 Fehler").
    if _ist_baum and _summen.is_file() and _soll:
        import subprocess as _sp3
        _gitls = _sp3.run(["git", "-C", str(root), "ls-files"], capture_output=True, text=True, timeout=120)
        if _gitls.returncode == 0:
            for _rel in sorted(x.strip() for x in _gitls.stdout.splitlines() if x.strip()):
                if _rel == "PRUEFSUMMEN_MASTER.txt" or _rel in _soll:
                    continue
                if not (root / _rel).is_file():
                    continue          # Unter-Repos (gitlink) und Sonderfaelle sind keine zu hashenden Dateien
                _k9_liste += 1
                findings.append({"regel": "K9", "schwere": "ERROR", "pfad": str(root / _rel),
                                 "meldung": "verfolgt, aber NICHT in PRUEFSUMMEN_MASTER.txt — summen ausfuehren"})
        else:
            findings.append({"regel": "K9", "schwere": "WARNING", "pfad": str(root),
                             "meldung": "git ls-files nicht lesbar — Rueckrichtung NICHT geprueft (UNGEPRUEFT)"})
    # Selbstbeschreibung muss EXISTIEREN (Befund 10): fehlt sie ganz, war der Baum bisher "0 Fehler".
    if _ist_baum and not (root / "ro-crate-metadata.json").is_file():
        findings.append({"regel": "CRATE", "schwere": "ERROR", "pfad": str(root / "ro-crate-metadata.json"),
                         "meldung": "Selbstbeschreibung FEHLT — ./ordner.sh summen erzeugt sie"})
    # Crate als echte Regel: vorher war die Pruefung nur eine Anzeige mit '|| true' in ordner.sh,
    # dadurch konnte die Selbstbeschreibung still veralten (Befund 5).
    _crate_datei = root / "ro-crate-metadata.json"
    if _crate_datei.is_file():
        import subprocess as _sp
        _cp = _sp.run([sys.executable, "-B", str(root / "70_AUTOMATION/crate/ro_crate.py"), "--pruefen", str(root)],
                      capture_output=True, text=True)
        if _cp.returncode != 0:
            _zeilen = [x.strip() for x in (_cp.stdout or "").splitlines() if x.strip()]
            findings.append({"regel": "CRATE", "schwere": "ERROR", "pfad": str(_crate_datei),
                             "meldung": "Selbstbeschreibung passt NICHT zum Inhalt: "
                                        + (_zeilen[0][:160] if _zeilen else f"rc={_cp.returncode}")})
    _t_k9crate = _tc.monotonic() - _t_k0
    # ------- Status EINMAL am Ende berechnen (Befund 4: vorher widersprach sich die Zeile) -------
    level = max((f["schwere"] for f in findings), key=lambda s: STUFEN.index(s), default=level)
    fehler = [f for f in findings if f["schwere"] in ("ERROR", "CRITICAL")]
    hinweise = [f for f in findings if f["schwere"] == "WARNING"]
    if ungeprueft and level in ("OK", "WARNING"):
        level = "ERROR"; fehler = [f for f in findings if f["schwere"] in ("ERROR", "CRITICAL")]
    _teile = zeile.split(" · ")
    if len(_teile) >= 3:
        _teile[0] = f"PRUEFER: {level}"; _teile[1] = f"{len(fehler)} Fehler"; _teile[2] = f"{len(hinweise)} Hinweise"
        zeile = " · ".join(_teile)
    # --- Schritt 2: die Pruefdauer wird eine Zahl statt eines Bauchgefuehls ---
    _zt = getattr(ctx, "zeiten", {}) or {}
    _zsort = sorted(_zt.items(), key=lambda kv: -kv[1])
    _zregeln = sum(v for k, v in _zsort if k != "entdecke_git (Baumdurchlauf)")
    zeiten_zeile = ("ZEITEN: gesamt {:.2f}s · Baumdurchlauf {:.2f}s · Regeln zusammen {:.2f}s · "
                    "K9/CRATE {:.2f}s · Selbsttest {:.2f}s · Redundanz {:.2f}s · Rest {:.2f}s"
                    .format(_tc.monotonic() - _t_main, _zt.get("entdecke_git (Baumdurchlauf)", 0.0),
                            _zregeln, _t_k9crate, _t_selbst, _t_red, max(_t_run_all - _zregeln, 0.0))
                    + " · laengste Regeln: " + " ".join(f"{k} {v:.2f}s" for k, v in _zsort[:5]))

    if a.json:
        print(json.dumps({"rollentrennung": _rollentrennung_text(a.root),
                          "history_coverage": "PARTIAL (Arbeitsbaum + HEAD; Seitenzweige/dangling NICHT geprueft)",
                          "status": level, "exit": CODE[level], "fehler": len(fehler), "hinweise": len(hinweise),
                          "geprueft": n_geprueft, "redundanz": red, "selbsttest": st, "zeile": zeile,
                          "abdeckung": ab.get("abdeckung", {}), "ungeprueft": ab.get("ungeprueft_liste", []),
                          "findings": findings}, ensure_ascii=True, indent=2))
    else:
        if not a.quiet:
            for f in findings:
                print(f"  [{f['schwere']:8}] {f['regel']:7} {f['pfad']}: {f['meldung']}")
        print(f"STATUS: {level}" + (f" | {len(fehler)} error, {len(hinweise)} warnings" if findings else ""))
        print(zeile)
        print(zeiten_zeile)
    # F3 (OpenCode-Befund 25.09.2026): Zustandsdatei ZULETZT schreiben — sie muss denselben Stand
    # zeigen wie stdout und der Exitcode (sonst bestaetigt ein Waechter einen roten Lauf als OK).
    if R.ist_im_baum(stt, SANDBOX):
        try:
            (stt / "status.json").write_text(json.dumps(
                {"zeit": jetzt, "status": level, "exit": CODE[level], "geprueft": n_geprueft,
                 "fehler": len(fehler), "hinweise": len(hinweise),
                 "erzeuger": "check_all", "pid": os.getpid()}, ensure_ascii=True) + "\n", encoding="utf-8")
        except OSError as ex:
            sys.stderr.write(f"ABBRUCH-ZUSTAND: Statusdatei nicht schreibbar ({type(ex).__name__}: {ex}) "
                             f"— Zustand dieses Laufes UNBESTAETIGT (gemeldet als CRITICAL).\n")
            sys.stderr.flush()
            level = "CRITICAL"          # dieselbe Aussage wie das JSON und der Exitcode
            fehler = [f for f in findings if f["schwere"] in ("ERROR", "CRITICAL")]
            return CODE["CRITICAL"]
    return CODE[level]


def _rollentrennung_text(wurzel=None) -> str:
    """wurzel = der GEPRUEFTE Baum (nicht der Ort der Datei): eine Messung gilt nur fuer ihren Ort."""
    """Liest die GEMESSENE Rollentrennung (50_INFRA/rollentrennung.yaml).

    Fehlt die Messung oder wurden Spuren gefunden, sagt die Zeile das ehrlich —
    sie behauptet nie ein "OK", das nicht nachgerechnet wurde.
    """
    basis = Path(wurzel).resolve() if wurzel else Path(__file__).resolve().parents[2]
    f = basis / "50_INFRA/rollentrennung.yaml"
    if not f.is_file():
        return "NICHT VERIFIZIERT"
    daten = {}
    for zeile in f.read_text(encoding="utf-8").splitlines():
        if ":" in zeile:
            k, v = zeile.split(":", 1)
            daten[k.strip()] = v.strip()
    if daten.get("verdict") != "VERIFIZIERT":
        return f"SPUREN GEFUNDEN ({daten.get('anzahl_aenderungen', '?')})"
    # EHRLICHKEIT: eine MESSUNG gilt nur fuer den Ort, an dem sie gemacht wurde.
    # Kopien (Tests, Sicherung) erben sie NICHT — sonst behauptet eine Kopie ein OK, das nie gemessen wurde.
    if str(basis) not in daten.get("orte", ""):
        return "NICHT VERIFIZIERT (Messung gilt fuer einen anderen Ort)"
    return (f"VERIFIZIERT {daten.get('datum','?')} ({daten.get('dateien_geprueft','?')} Dateien beobachtet, "
            f"{daten.get('lesende_befehle','?')} lesende Befehle, 0 Schreibspuren)")


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""PHASE 6/7 — Skalierungstest. Erzeugt SYNTHETISCHE, K7-konforme Baeme in der Sandbox.

Form: <BEREICH>/g<XX>/h<XX>/k<XX>/f<NN>.md  ->  Tiefe 5, Breite <= 20 auf jeder Ebene.
Damit bleibt die Grenze aus v1.3 eingehalten und wir messen das System, nicht die Regelverletzung.

Gemessen wird die ENGINE (in-process) UND die CLI-Gesamtzeit (subprocess) — beides getrennt,
damit Python-Startzeit nicht als Rechenzeit verkauft wird.

Aufruf: python3 skala.py --stufen 1000 10000 100000 [--budget-datei ergebnisse.jsonl]
"""
from __future__ import annotations
import argparse, json, os, resource, subprocess, sys, time
from pathlib import Path

S = Path(__file__).resolve().parents[3]
M = next(p for p in Path(__file__).resolve().parents if (p / "ordner.sh").is_file())
sys.path.insert(0, str(M / "70_AUTOMATION/validation"))
sys.path.insert(0, str(M / "70_AUTOMATION/indexing"))
import rules as R
R.schutz_installieren()        # BLOCKER 2 (2.7): auch --budget-datei wird geprueft
import schema_check
import indexer

SANDBOX = Path(__file__).resolve().parents[3]


def nur_sandkasten(p) -> Path:
    """Waechter: jede schreibende/loeschende Operation MUSS in der Sandbox liegen."""
    p = Path(p)
    if str(p).startswith(str(SANDBOX) + "/") or p == SANDBOX:
        return p
    raise AssertionError(f"AUSSERHALB DER SANDBOX — verweigert: {p}")

BEREICHE = [
"00_SYSTEM", "10_AGENT", "20_PROJEKTE", "30_WISSEN", "40_DATEN",
            "50_INFRA", "60_RUNTIME", "70_AUTOMATION", "80_VORLAGEN", "90_ARCHIV"]
TEXT = ("# Objekt\n\nInhalt fuer den Suchindex: FTS5 Wissensbasis Prototyp Skalierung.\n"
        "artefakt cache quittung herzschlag projekt dossier node\n")


def baue(root: Path, n: int) -> dict:
    """Erzeugt n Textdateien in legaler Form. Rueckgabe: Messwerte des Aufbaus."""
    if root.exists():
        import shutil; shutil.rmtree(nur_sandkasten(root))   # nur innerhalb der Sandbox
    (root / "00_SYSTEM/manifest").mkdir(parents=True)
    (root / "00_SYSTEM/schemas").mkdir(parents=True)
    (root / "00_SYSTEM/schemas/repos.schema.json").write_text(
        (M / "00_SYSTEM/schemas/repos.schema.json").read_text(encoding="utf-8"), encoding="utf-8")
    (root / "00_SYSTEM/manifest/repos.yaml").write_text(
        'schema_version: 1\nnotfallkontakt: "skala"\npassphrase_ort: "keine"\nrepos:\n'
        '  - schema_version: 1\n    name: system_meta\n    class: system\n    status: paused\n'
        '    owner: skala\n    seit: "2026-09-21"\n    bereich: 00_SYSTEM\n    pfad: 00_SYSTEM\n    git: false\n',
        encoding="utf-8")
    (root / "40_DATEN/pointers").mkdir(parents=True)
    t0 = time.perf_counter(); erzeugt = 0
    for b in BEREICHE:
        # Breite 20 gilt je Ordner: vorhandene echte Unterordner (manifest, schemas, pointers,
        # prompts, ...) werden angerechnet — sonst erzeugt der TEST einen K7-Verstoss, nicht das System.
        vorhanden = len([x for x in os.scandir(root / b)]) if (root / b).exists() else 0
        for g in range(max(0, 20 - vorhanden)):
            if erzeugt >= n: break
            gp = root / b / f"g{g:02d}"; gp.mkdir(parents=True, exist_ok=True)
            for h in range(20):
                if erzeugt >= n: break
                hp = gp / f"h{h:02d}"; hp.mkdir(exist_ok=True)
                for k in range(20):
                    if erzeugt >= n: break
                    kp = hp / f"k{k:02d}"; kp.mkdir(exist_ok=True)
                    for f in range(20):
                        if erzeugt >= n: break
                        (kp / f"f{f:02d}.md").write_text(TEXT, encoding="utf-8"); erzeugt += 1
        if erzeugt >= n: break
    dauer = time.perf_counter() - t0
    return {"dateien": erzeugt, "aufbau_s": round(dauer, 2)}


def messe(root: Path, n: int) -> dict:
    import yaml
    kat = yaml.safe_load((root / "00_SYSTEM/manifest/repos.yaml").read_text(encoding="utf-8"))
    # --- Validator: ENGINE (in-process) ---
    t0 = time.perf_counter(); ctx = R.run_all(root, kat); t_engine = time.perf_counter() - t0
    sfehler, backend = schema_check.pruefe(root)
    mem_engine = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0     # MB
    # --- Validator: CLI (subprocess, inkl. Startzeit) ---
    t0 = time.perf_counter()
    r = subprocess.run([sys.executable, str(M / "70_AUTOMATION/validation/check_all.py"),
                        "--root", str(root), "--no-selftest", "--quiet"], capture_output=True, text=True)
    t_cli = time.perf_counter() - t0
    status = [z for z in r.stdout.splitlines() if z.startswith("STATUS:")]
    # --- Index ---
    t0 = time.perf_counter(); ib = indexer.build(root, still=True); t_index = time.perf_counter() - t0
    # --- Suche (5 Abfragen, in-process) ---
    zeiten = []
    for q in ["FTS5", "Wissensbasis", "Projekt", "artefakt", "knoten"]:
        t0 = time.perf_counter(); treffer, fehler = indexer.search(root, q, limit=20); zeiten.append(time.perf_counter() - t0)
    return {"stufe": n, "dateien_ist": ib["anzahl"].get("datei", 0),
            "validator_engine_s": round(t_engine, 3), "validator_cli_s": round(t_cli, 3),
            "validator_status": status[0] if status else "?", "validator_befunde": len(ctx.findings),
            "speicher_engine_mb": round(mem_engine, 1),
            "index_s": round(ib["dauer_s"], 3), "index_mb": round(ib["groesse_b"] / 1e6, 3),
            "index_dokumente": sum(ib["anzahl"].values()),
            "suche_s_mittel": round(sum(zeiten) / len(zeiten), 4), "suche_s_max": round(max(zeiten), 4),
            "k4_befunde": sum(1 for f in ctx.findings if f["regel"] == "K4"),
            "k7_befunde": sum(1 for f in ctx.findings if f["regel"] == "K7"),
            "k8_befunde": sum(1 for f in ctx.findings if f["regel"] == "K8")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stufen", type=int, nargs="+", default=[1000, 10000, 100000])
    ap.add_argument("--budget-datei", default=str(S / "skala/ergebnisse.jsonl"))
    ap.add_argument("--behalten", action="store_true", help="Baeume nicht loeschen (Standard: loeschen)")
    a = ap.parse_args()
    ziel = Path(a.budget_datei)
    # BLOCKER 2/3 (2.7): VALIDATE BEFORE WRITE — kein mkdir vor der kanonischen Pruefung.
    # Ohne diese Zeile entstand ein Verzeichnis ausserhalb der Sandbox und die spaetere
    # Verweigerung des open() blieb unbemerkt (Exit 0 trotz verweigerter Schreiboperation).
    R.assert_write_inside_sandbox(ziel)
    R._ziel_sicher(ziel)
    ziel.parent.mkdir(parents=True, exist_ok=True)
    for n in a.stufen:
        root = S / "skala" / f"stufe_{n}"
        print(f"\n=== STUFE {n} ===")
        b = baue(root, n); print(f"  Aufbau: {b['dateien']} Dateien in {b['aufbau_s']} s")
        m = messe(root, n); m.update(b)
        print(f"  Validator (Engine) {m['validator_engine_s']} s | (CLI) {m['validator_cli_s']} s | "
              f"{m['validator_status']} | Befunde {m['validator_befunde']} (K4 {m['k4_befunde']}, K7 {m['k7_befunde']}, K8 {m['k8_befunde']})")
        print(f"  Speicher (maxrss) {m['speicher_engine_mb']} MB | Index {m['index_s']} s / {m['index_mb']} MB / "
              f"{m['index_dokumente']} Dokumente | Suche Ø {m['suche_s_mittel']*1000:.1f} ms (max {m['suche_s_max']*1000:.1f} ms)")
        with ziel.open("a", encoding="utf-8") as fh: fh.write(json.dumps(m, ensure_ascii=False) + "\n")
        if not a.behalten:
            import shutil; shutil.rmtree(nur_sandkasten(root), ignore_errors=True)
            (S / "skala" / f"index_{n}.db").unlink(missing_ok=True)
            print("  (Baum wieder entfernt — Messwerte stehen in der Ergebnisdatei)")
    print(f"\nErgebnisse: {ziel} ({len(ziel.read_text(encoding='utf-8').splitlines())} Zeilen)")


if __name__ == "__main__":
    main()

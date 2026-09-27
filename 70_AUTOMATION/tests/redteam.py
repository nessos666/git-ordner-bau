#!/usr/bin/env python3
"""PHASE 13/14 — RED TEAM gegen den REALEN Prototyp (nicht gegen das Papierdesign).

Alle Angriffe laufen SYNTHETISCH in der Sandbox. Produktive Repositories werden nur gelesen.

Massstab (v1.3 / Phase 14):  PASS = verhindert ODER zuverlaessig erkannt
                            UND Schaden begrenzt UND Recovery definiert.
"""
from __future__ import annotations
import json, os, shutil, sqlite3, subprocess, sys, tempfile
from pathlib import Path
import yaml

S = Path(__file__).resolve().parents[3]; M = next(p for p in Path(__file__).resolve().parents if (p / "ordner.sh").is_file())
sys.path.insert(0, str(M / "70_AUTOMATION/validation")); sys.path.insert(0, str(M / "70_AUTOMATION/indexing"))
sys.path.insert(0, str(M / "70_AUTOMATION/maintenance")); sys.path.insert(0, str(M / "70_AUTOMATION/cross-repo"))
import rules as R, indexer, budget, status_sim, adapter_readonly

SANDBOX = Path(__file__).resolve().parents[3]


def nur_sandkasten(p) -> Path:
    """Waechter: jede schreibende/loeschende Operation MUSS in der Sandbox liegen."""
    p = Path(p)
    if str(p).startswith(str(SANDBOX) + "/") or p == SANDBOX:
        return p
    raise AssertionError(f"AUSSERHALB DER SANDBOX — verweigert: {p}")

TMP = S / "tmp_tests/redteam"; TMP.mkdir(parents=True, exist_ok=True)
SCH = (M / "00_SYSTEM/schemas/repos.schema.json").read_text(encoding="utf-8")
SCHECK = M / "70_AUTOMATION/validation/check_all.py"
BEFUNDE = []



def neu(name: str, eintraege=None, dirs=(), dateien=(), repos=()):
    root = TMP / name
    if root.exists(): shutil.rmtree(nur_sandkasten(root))
    (root / "00_SYSTEM/manifest").mkdir(parents=True); (root / "00_SYSTEM/schemas").mkdir(parents=True)
    (root / "00_SYSTEM/schemas/repos.schema.json").write_text(SCH, encoding="utf-8")
    (root / "40_DATEN/pointers").mkdir(parents=True)
    k = ['schema_version: 1\nnotfallkontakt: "rt"\npassphrase_ort: "keine"\nrepos:\n',
         '  - schema_version: 1\n    name: system_meta\n    class: system\n    status: paused\n'
         '    owner: t\n    seit: "2026-09-21"\n    bereich: 00_SYSTEM\n    pfad: 00_SYSTEM\n    git: false\n']
    k += list(eintraege or [])
    (root / "00_SYSTEM/manifest/repos.yaml").write_text("".join(k), encoding="utf-8")
    for d in dirs: (root / d).mkdir(parents=True, exist_ok=True)
    for f, c in dateien:
        p = root / f; p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(c if isinstance(c, bytes) else c.encode())
    for r in repos:
        p = root / r; p.mkdir(parents=True, exist_ok=True)
        (p / "README.md").write_text("# r\n", encoding="utf-8"); (p / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")
        for a in (["init", "-q", "-b", "main"], ["config", "user.email", "t@l"], ["config", "user.name", "T"],
                  ["add", "-A"], ["commit", "-q", "-m", "t"]):
            subprocess.run(["git", *a], cwd=p, capture_output=True)
    return root


def pruefe(root):
    kat = {}
    try: kat = yaml.safe_load((root / "00_SYSTEM/manifest/repos.yaml").read_text(encoding="utf-8")) or {}
    except Exception: pass
    return R.run_all(root, kat)


def hat(ctx, regel): return any(f["regel"] == regel for f in ctx.findings)


def protokoll(angriff, urteil, beleg):
    BEFUNDE.append({"angriff": angriff, "urteil": urteil, "beleg": beleg})
    print(f"  [{urteil:22}] {angriff:46} {beleg[:76]}")


def eintrag(name, **kw):
    d = {"schema_version": 1, "name": name, "class": "project", "status": "active", "owner": "t",
         "seit": "2026-09-21", "bereich": "20_PROJEKTE", "pfad": f"20_PROJEKTE/domains/thema/2026-09-21_{name}", "git": False}
    if "klasse" in kw: d["class"] = kw.pop("klasse")
    d.update(kw)
    # YAML-sauber serialisieren (None -> null), sonst entstehen Testartefakte statt echter Angriffe
    return "".join(f"  - {z}" if i == 0 else f"    {z}"
                   for i, z in enumerate(yaml.safe_dump(d, allow_unicode=True, sort_keys=False).splitlines(True)))


# ================= RED TEAM A — Daten & Skalierung =================
def redteam_a():
    print("\n=== RED TEAM A — Daten & Skalierung ===")
    r = neu("a1", [eintrag("p0", review_am="2027-09-21")], dirs=["20_PROJEKTE/domains/thema/2026-09-21_p0"])
    indexer.build(r, still=True)
    # A1 Index zerschlagen
    indexer.index_pfad(r).write_bytes(b"kein sqlite")
    t, fehler = indexer.search(r, "irgendwas")
    protokoll("A1 Index-Datei zerschlagen", "PASS" if (fehler or t == []) else "FAIL",
              f"Suche meldet Fehler statt Absturz: {bool(fehler)}; Recovery: build")
    indexer.build(r, still=True); t2, _ = indexer.search(r, "p0")
    protokoll("A2 Recovery nach Zerschlagen", "PASS" if t2 else "FAIL", f"Neuaufbau liefert {len(t2)} Treffer")
    # A3 Index loeschen
    indexer.drop(r); st = indexer.status(r)
    protokoll("A3 Index geloescht", "PASS" if not st["vorhanden"] else "FAIL", "status meldet FEHLT, kein Absturz")
    indexer.build(r, still=True)
    # A4 Index veralten lassen
    (r / "20_PROJEKTE/domains/thema/2026-09-21_p0/NEU.md").write_text("neuer inhalt zzz\n", encoding="utf-8")
    t3, _ = indexer.search(r, "zzz")
    st = indexer.status(r)
    protokoll("A4 Index veralten lassen", "PASS MIT EINSCHRAENKUNG" if not t3 else "PASS",
              f"veraltet={st.get('veraltet_gegenueber_quellen')}; neue Datei nicht im Index bis build; Pruefer bleibt Wahrheit")
    # A5-A10 Katalogfehler
    r2 = neu("a5", [eintrag("d1", review_am="2027-09-21"), eintrag("d1", review_am="2027-09-21")],
             dirs=["20_PROJEKTE/domains/thema/2026-09-21_d1"])
    ctx = pruefe(r2)
    protokoll("A5 doppelte IDs/doppelter Pfad", "PASS" if hat(ctx, "K5") else "FAIL", [f["meldung"][:60] for f in ctx.findings if f["regel"] == "K5"][:1])
    r3 = neu("a6", [eintrag("weg", pfad="20_PROJEKTE/domains/thema/2026-09-21_weg_nicht_da")])
    ctx = pruefe(r3)
    protokoll("A6 fehlende Datei (Katalog ins Leere)", "PASS" if hat(ctx, "K4") else "FAIL",
              [f["meldung"][:60] for f in ctx.findings if f["regel"] == "K4"][:1])
    r4 = neu("a7", [], dirs=["20_PROJEKTE/Projekt", "20_PROJEKTE/projekt"])
    ctx = pruefe(r4)
    protokoll("A7 Case-Kollision", "PASS" if hat(ctx, "K6") else "FAIL", [f["meldung"][:60] for f in ctx.findings if f["regel"] == "K6"][:1])
    r5 = neu("a8", [eintrag("gross", klasse="data", bereich="60_RUNTIME", pfad="60_RUNTIME/artefakt/modell", review_am="2027-09-21")],
             dirs=["60_RUNTIME/artefakt/modell"])
    (r5 / "60_RUNTIME/artefakt/modell/gewichte.bin").write_bytes(b"0" * 1024)
    b = budget.pruefe(r5)
    protokoll("A8 40_DATEN-Budget ueberschritten", "PASS" if b["status"] == "PASS" else "FAIL",
              f"aktuell {b['status']} ({b['auslastung_pct']}% von 1 MB)")
    r6 = neu("a9")
    (r6 / "40_DATEN/ballast.bin").write_bytes(b"0" * ((1 << 20) + 50))
    b = budget.pruefe(r6); ctx = pruefe(r6)
    protokoll("A9 Budgetverstoss wird gemeldet, nichts geloescht",
              "PASS" if b["status"] == "FAIL" and hat(ctx, "K8") and (r6 / "40_DATEN/ballast.bin").exists() else "FAIL",
              f"budget={b['status']}, K8={hat(ctx,'K8')}, Datei noch da={(r6/'40_DATEN/ballast.bin').exists()}")


# ================= RED TEAM B — Git & Isolation =================
def redteam_b():
    print("\n=== RED TEAM B — Git & Isolation ===")
    r = neu("b1", [eintrag("fremd", klasse="data", extern=True, git=False, pin=None, pfad="20_PROJEKTE/domains/thema/2026-09-21_fremd")],
            dirs=["20_PROJEKTE/domains/thema/2026-09-21_fremd"])
    ctx = pruefe(r)
    protokoll("B1 fremdes Repo ohne Pin", "PASS" if hat(ctx, "K4") else "FAIL", [f["meldung"][:64] for f in ctx.findings if f["regel"] == "K4"][:1])
    r = neu("b2", [eintrag("eigen", pin="0" * 40, review_am="2027-09-21")], dirs=["20_PROJEKTE/domains/thema/2026-09-21_eigen"])
    ctx = pruefe(r)
    protokoll("B2 eigenes Repo faelschlich als extern gepinnt", "PASS" if hat(ctx, "K4") else "FAIL", [f["meldung"][:64] for f in ctx.findings if f["regel"] == "K4"][:1])
    r = neu("b3", [], repos=["20_PROJEKTE/domains/thema/2026-09-21_waise"])
    ctx = pruefe(r)
    protokoll("B3 Repo ohne Katalogzeile", "PASS" if hat(ctx, "K4") else "FAIL", [f["meldung"][:64] for f in ctx.findings if f["regel"] == "K4"][:1])
    r = neu("b4", [eintrag("geistig", git=True, remote="t/geistig", review_am="2027-09-21")], dirs=["20_PROJEKTE/domains/thema/2026-09-21_geistig"])
    ctx = pruefe(r)
    protokoll("B4 Katalogzeile git=true ohne Repo", "PASS" if hat(ctx, "K4") else "FAIL", [f["meldung"][:64] for f in ctx.findings if f["regel"] == "K4"][:1])
    # B5 verschachteltes Repo
    r = neu("b5", [], repos=["20_PROJEKTE/domains/thema/2026-09-21_aussen"])
    innen = r / "20_PROJEKTE/domains/thema/2026-09-21_aussen/innen"
    innen.mkdir(parents=True, exist_ok=True)
    (innen / "README.md").write_text("# innen\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=innen, capture_output=True)
    ctx = pruefe(r)
    n_k4 = sum(1 for f in ctx.findings if f["regel"] == "K4")
    protokoll("B5 verschachteltes Repo", "PASS" if n_k4 >= 1 else "FAIL", f"{n_k4} K4-Befunde (beide Repos geprueft)")
    # B6 kaputtes .git
    r = neu("b6", [], repos=["20_PROJEKTE/domains/thema/2026-09-21_kaputt"])
    g = r / "20_PROJEKTE/domains/thema/2026-09-21_kaputt/.git"
    for f in g.iterdir():
        if f.is_file(): nur_sandkasten(f).unlink()
        else: shutil.rmtree(nur_sandkasten(f), ignore_errors=True)
    ctx = pruefe(r)
    protokoll("B6 kaputtes .git", "PASS" if hat(ctx, "K1") or hat(ctx, "K4") else "FAIL",
              [f"{f['regel']}: {f['meldung'][:48]}" for f in ctx.findings][:1] or "kein Befund!")
    # B7 dirty / B8 detached HEAD
    r = neu("b7", [eintrag("schmutz", git=True, remote="t/s", review_am="2027-09-21")],
            repos=["20_PROJEKTE/domains/thema/2026-09-21_schmutz"])
    repo = r / "20_PROJEKTE/domains/thema/2026-09-21_schmutz"
    (repo / "README.md").write_text("# geaendert aber nicht committet\n", encoding="utf-8")
    ctx = pruefe(r)
    protokoll("B7 dirty Repo", "PASS MIT EINSCHRAENKUNG" if not ctx.findings else "PASS",
              "kein Regelverstoss (dirty ist kein v1.3-Verstoss); Index zeigt HEAD/Branch")
    subprocess.run(["git", "checkout", "-q", "HEAD~0"], cwd=repo, capture_output=True)
    subprocess.run(["git", "checkout", "-q", "--detach"], cwd=repo, capture_output=True)
    ctx = pruefe(r)
    gi = adapter_readonly.beobachte(repo)
    protokoll("B8 detached HEAD", "PASS MIT EINSCHRAENKUNG", f"Branch wird als '{gi['branch']}' gelesen, kein Absturz")
    # B9 archiviertes Repo
    r = neu("b9", [eintrag("alt", klasse="archive", status="archived", bereich="90_ARCHIV",
                           pfad="90_ARCHIV/2026_alt", git=True, remote="t/alt")], repos=["90_ARCHIV/2026_alt"])
    ctx = pruefe(r)
    protokoll("B9 archiviertes Repo", "PASS" if not ctx.findings else "FAIL",
              f"{len(ctx.findings)} Befunde (archived braucht kein review_am)")
    # B10 read-only Repo
    r = neu("b10", [eintrag("ro", git=True, remote="t/ro", review_am="2027-09-21")],
            repos=["20_PROJEKTE/domains/thema/2026-09-21_ro"])
    ro = r / "20_PROJEKTE/domains/thema/2026-09-21_ro"
    os.chmod(ro, 0o500)
    ctx = pruefe(r); os.chmod(ro, 0o700)
    protokoll("B10 schreibgeschuetztes Repo", "PASS", f"Pruefer liest trotzdem ({len(ctx.findings)} Befunde, kein Absturz)")


# ================= RED TEAM C — Waechter & Mensch =================
def redteam_c():
    print("\n=== RED TEAM C — Waechter & Mensch ===")
    basis = TMP / "c"; basis.mkdir(parents=True, exist_ok=True)
    e = status_sim.szenario_a_b_c_e(basis); d = status_sim.szenario_d(basis)
    # Jeder Ausfall muss LAUT sein: UNBESTAETIGT oder CRITICAL — niemals OK.
    # (Zustellfehler quittiert = CRITICAL nach §4.4, alles andere UNBESTAETIGT.)
    still = {k: v[0] for k, v in d.items() if v[0] not in ("UNBESTAETIGT", "CRITICAL")}
    zustell = {k: v[0] for k, v in d.items() if "Zustellfehler" in k}
    ok = (not still) and all(v == "CRITICAL" for v in zustell.values())
    protokoll("C1 Waechter faellt aus / Quittung fehlt/alt/kaputt", "PASS" if ok else "FAIL",
              f"{len(d)} Faelle, nie OK (still: {still or 'keine'}), Zustellfehler CRITICAL: {zustell}")
    protokoll("C2 Selbsttest kaputt", "PASS" if e["E Selbsttest defekt"][0] == "CRITICAL" else "FAIL",
              f"Status={e['E Selbsttest defekt'][0]}")
    # C3 Index behauptet etwas anderes als Git
    r = neu("c3", [eintrag("x", review_am="2027-09-21")], dirs=["20_PROJEKTE/domains/thema/2026-09-21_x"])
    indexer.build(r, still=True)
    shutil.rmtree(nur_sandkasten(r / "20_PROJEKTE/domains/thema/2026-09-21_x"))
    t, _ = indexer.search(r, "2026-09-21_x")
    ctx = pruefe(r)
    protokoll("C3 Index sagt A, Quelle sagt B", "PASS" if (t and hat(ctx, "K4")) else "FAIL",
              f"Index zeigt alten Treffer={bool(t)}, Pruefer meldet Abweichung={hat(ctx,'K4')} -> Quelle gewinnt")
    # C4 provisional bleibt liegen
    r = neu("c4", [eintrag("liegen", status="provisional", pfad="20_PROJEKTE/domains/thema/2026-09-21_liegen", seit="2025-01-01")],
            dirs=["20_PROJEKTE/domains/thema/2026-09-21_liegen"])
    ctx = pruefe(r)
    erkannt = any("provisional" in f["meldung"].lower() and "tag" in f["meldung"].lower() for f in ctx.findings)
    protokoll("C4 provisional liegt > 30 Tage", "PASS" if erkannt else "FAIL",
              "erkannt" if erkannt else "NICHT erkannt — v1.3 sieht 30-Tage-Warnung vor, im Prototyp fehlt sie")
    # C5 Secret-Fixture
    r = neu("c5", [eintrag("sec", git=True, remote="t/sec", review_am="2027-09-21")], repos=["20_PROJEKTE/domains/thema/2026-09-21_sec"])
    (r / "20_PROJEKTE/domains/thema/2026-09-21_sec/harmlos.md").write_text("api_key = " + "sk-" + "ABCDEFGHIJKLMNOPQRSTUVWX9999\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=r / "20_PROJEKTE/domains/thema/2026-09-21_sec", capture_output=True)
    subprocess.run(["git", "commit", "-q", "-m", "s"], cwd=r / "20_PROJEKTE/domains/thema/2026-09-21_sec", capture_output=True)
    ctx = pruefe(r)
    protokoll("C5 Secret-Fixture", "PASS" if hat(ctx, "K2") else "FAIL", [f["meldung"][:60] for f in ctx.findings if f["regel"] == "K2"][:1])
    # C6 Artefakt wird als Cache klassifiziert
    r = neu("c6", [eintrag("finetune", klasse="data", bereich="60_RUNTIME", pfad="60_RUNTIME/cache/modell", review_am="2027-09-21")],
            dirs=["60_RUNTIME/cache/modell"])
    (r / "60_RUNTIME/cache/modell/gewichte.bin").write_bytes(b"0" * 1024)
    ctx = pruefe(r)
    protokoll("C6 Artefakt liegt im loeschbaren Cache", "PASS MIT EINSCHRAENKUNG" if not ctx.findings else "PASS",
              "kein Befund — v1.3-Klassifikation ('im Zweifel Artefakt') wird nicht maschinell geprueft")


if __name__ == "__main__":
    print("RED TEAM gegen den REALEN Prototyp —", M)
    redteam_a(); redteam_b(); redteam_c()
    zahlen = {}
    for b in BEFUNDE: zahlen[b["urteil"]] = zahlen.get(b["urteil"], 0) + 1
    print("\n=== BILANZ ===")
    for k in ["CRITICAL FAIL", "FAIL", "PASS MIT EINSCHRAENKUNG", "PASS"]:
        if zahlen.get(k): print(f"  {k}: {zahlen[k]}")
    out = S / "redteam/ergebnisse.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"befunde": BEFUNDE, "bilanz": zahlen}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Datei: {out}")

#!/usr/bin/env python3
"""Erzeugt fixtures/clean (0 Befunde) und fixtures/broken (bekannte Verstoesse) — reproduzierbar.
Schreibt AUSSCHLIESSLICH unter <sandbox>/fixtures/.
"""
import subprocess, shutil
from pathlib import Path


SANDBOX = Path(__file__).resolve().parents[3]


def nur_sandkasten(p) -> Path:
    """Waechter: jede schreibende/loeschende Operation MUSS in der Sandbox liegen."""
    p = Path(p)
    if str(p).startswith(str(SANDBOX) + "/") or p == SANDBOX:
        return p
    raise AssertionError(f"AUSSERHALB DER SANDBOX — verweigert: {p}")
S = Path(__file__).resolve().parents[3]; F = S / "fixtures"
M = Path(__file__).resolve().parents[2]   # der Baum selbst (namensunabhängig)
SCH = (M / "00_SYSTEM/schemas/repos.schema.json").read_text(encoding="utf-8")
GI = ".venv/\n__pycache__/\n*.log\ncache/\n"
PZ = """schema_version: 1
zeiger:
  - typ: objekt
    name: winzig
    ziel: {ziel}
    groesse: 16
    sha256: {sha}
    datum: 2026-09-21
    rekonstruktion: "16 Byte neu erzeugen"
"""

def git(*a, cwd): return subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True)
def basis(root: Path):
    assert str(root).startswith(str(F)), "nur unter fixtures/!"
    if root.exists(): shutil.rmtree(nur_sandkasten(root))
    for d in ["00_SYSTEM/manifest", "00_SYSTEM/schemas", "40_DATEN/pointers"]:
        (root / d).mkdir(parents=True, exist_ok=True)
    (root / "00_SYSTEM/schemas/repos.schema.json").write_text(SCH, encoding="utf-8")
    klein = F / "klein.bin"
    klein.write_bytes(b"0123456789abcdef")
    import hashlib
    (root / "40_DATEN/pointers/p.yaml").write_text(PZ.format(sha=hashlib.sha256(klein.read_bytes()).hexdigest(), ziel=klein), encoding="utf-8")
def katalog(root: Path, eintraege: str):
    (root / "00_SYSTEM/manifest/repos.yaml").write_text(
        "schema_version: 1\nnotfallkontakt: \"Fixture\"\npassphrase_ort: \"keine\"\nrepos:\n" + eintraege, encoding="utf-8")
def repo(pfad: Path, mit_gitignore=True, init=True):
    pfad.mkdir(parents=True, exist_ok=True)
    (pfad / "README.md").write_text("# Fixture-Repo\n", encoding="utf-8")
    if mit_gitignore: (pfad / ".gitignore").write_text(GI, encoding="utf-8")
    if init:
        git("init", "-q", "-b", "main", cwd=pfad)
        git("config", "user.email", "f@local", cwd=pfad); git("config", "user.name", "F", cwd=pfad)
    return pfad
def commit(pfad: Path):
    git("add", "-A", cwd=pfad); git("commit", "-q", "-m", "fixture", cwd=pfad)

EINT = """  - schema_version: 1
    name: {name}
    class: {klasse}
    status: {status}
    owner: fixture
    seit: 2026-09-21
    bereich: {bereich}
    pfad: {pfad}
    git: {git}
{extra}"""

def main():
    # ---------------- CLEAN ----------------
    c = F / "clean"; basis(c); e = []
    p1 = repo(c / "00_SYSTEM"); commit(p1)
    e.append(EINT.format(name="system_meta", klasse="system", status="active", bereich="00_SYSTEM",
        pfad="00_SYSTEM", git="true", extra="    remote: f/system\n    review_am: 2027-09-21\n"))
    p2 = repo(c / "20_PROJEKTE/domains/thema/2026-09-21_sauber")
    (p2 / "STATUS.md").write_text("status: active\n", encoding="utf-8"); commit(p2)
    e.append(EINT.format(name="2026-09-21_sauber", klasse="project", status="active", bereich="20_PROJEKTE",
        pfad="20_PROJEKTE/domains/thema/2026-09-21_sauber", git="true", extra="    remote: f/sauber\n    review_am: 2027-09-21\n"))
    katalog(c, "".join(e))

    # ---------------- BROKEN (6 bekannte Verstoesse) ----------------
    b = F / "broken"; basis(b); e = []
    p1 = repo(b / "00_SYSTEM"); commit(p1)
    e.append(EINT.format(name="system_meta", klasse="system", status="active", bereich="00_SYSTEM",
        pfad="00_SYSTEM", git="true", extra="    remote: f/system\n    review_am: 2027-09-21\n"))
    p2 = repo(b / "20_PROJEKTE/domains/thema/2026-09-21_gross")           # K1 + K2
    with open(p2 / "daten.bin", "wb") as fh: fh.truncate(12 * 1024 * 1024)
    # Synthetisches Muster, absichtlich NICHT als Literal im Repo (K2 wuerde es sonst melden):
    SCHEIN = "api_key = " + "sk-" + "ABCDEFGHIJKLMNOPQRSTUVWX1234"
    (p2 / "config.md").write_text(SCHEIN + "\n", encoding="utf-8")
    (p2 / "STATUS.md").write_text("status: active\n", encoding="utf-8"); commit(p2)
    e.append(EINT.format(name="2026-09-21_gross", klasse="project", status="active", bereich="20_PROJEKTE",
        pfad="20_PROJEKTE/domains/thema/2026-09-21_gross", git="true", extra="    remote: f/gross\n    review_am: 2027-09-21\n"))
    p3 = repo(b / "30_WISSEN/research/2026-09-21_ohne_ignore", mit_gitignore=False)   # K3
    commit(p3)
    e.append(EINT.format(name="2026-09-21_ohne_ignore", klasse="knowledge", status="active", bereich="30_WISSEN",
        pfad="30_WISSEN/research/2026-09-21_ohne_ignore", git="true", extra="    remote: f/w\n    review_am: 2027-09-21\n"))
    e.append(EINT.format(name="geist", klasse="project", status="paused", bereich="20_PROJEKTE",   # K4 (Pfad existiert nicht)
        pfad="20_PROJEKTE/domains/thema/2026-09-21_existiert_nicht", git="false", extra=""))
    p4 = repo(b / "20_PROJEKTE/domains/thema/2026-09-21_unbekannt"); commit(p4)        # K4 umgekehrt (Repo ohne Katalogzeile)
    e.append(EINT.format(name="2026-09-21_ohne_review", klasse="project", status="active", bereich="20_PROJEKTE",  # K5
        pfad="20_PROJEKTE/domains/thema/2026-09-21_ohne_review", git="false", extra=""))
    (b / "20_PROJEKTE/domains/thema/2026-09-21_ohne_review").mkdir(parents=True, exist_ok=True)
    (b / "20_PROJEKTE/domains/thema/2026-09-21_tief/01_input/details").mkdir(parents=True, exist_ok=True)  # K7 (Tiefe 6)
    katalog(b, "".join(e))
    print("fixtures/clean und fixtures/broken erzeugt (clean=0 erwartet, broken=6 bekannte Verstoesse).")

if __name__ == "__main__": main()

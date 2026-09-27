#!/usr/bin/env python3
"""Strukturelle Pruefung des Katalogs gegen das JSON Schema (v1.3, Anhang A4).

Bevorzugt die Standardbibliothek; nutzt jsonschema NUR, wenn es vorhanden ist
(keine Installation noetig). Ohne jsonschema greift ein interner Minimalpruefer
fuer genau die Forderungen des Schemas. Keine Schreiboperation.
"""
from __future__ import annotations
import json
from pathlib import Path

try:
    import jsonschema
    BACKEND = "jsonschema"
except ImportError:
    BACKEND = "intern (Standardbibliothek)"

KLASSEN = ["system","agent","project","knowledge","data","infra","automation","template","archive"]
BEREICHE = ["00_SYSTEM","10_AGENT","20_PROJEKTE","30_WISSEN","40_DATEN","50_INFRA",
            "60_RUNTIME","70_AUTOMATION","80_VORLAGEN","90_ARCHIV"]
STATUS = ["provisional","active","paused","done","abandoned","archived"]
PFLICHT = ["schema_version","name","class","status","owner","seit","bereich","pfad","git"]


def _intern(daten: dict, schema: dict):
    fehler = []
    if daten.get("schema_version") != 1:
        fehler.append("schema_version fehlt oder ist nicht 1 (Kopf).")
    if not isinstance(daten.get("repos"), list) or not daten["repos"]:
        fehler.append("repos fehlt oder ist leer.")
        return fehler
    for i, e in enumerate(daten["repos"]):
        if not isinstance(e, dict):
            fehler.append(f"repos[{i}] ist kein Objekt."); continue
        for f in PFLICHT:
            if f not in e: fehler.append(f"repos[{i}]: Pflichtfeld '{f}' fehlt.")
        if e.get("class") not in KLASSEN: fehler.append(f"repos[{i}]: class {e.get('class')!r} ungueltig.")
        if e.get("bereich") not in BEREICHE: fehler.append(f"repos[{i}]: bereich {e.get('bereich')!r} ungueltig.")
        if e.get("status") not in STATUS: fehler.append(f"repos[{i}]: status {e.get('status')!r} ungueltig.")
        if not isinstance(e.get("git"), bool): fehler.append(f"repos[{i}]: git ist kein Wahrheitswert.")
        if isinstance(e.get("pfad"), str) and (e["pfad"].startswith("/") or ".." in e["pfad"]):
            fehler.append(f"repos[{i}]: pfad ist nicht relativ/kanonisch.")
        unbekannt = set(e) - set(schema["properties"]["repos"]["items"]["properties"])
        if unbekannt: fehler.append(f"repos[{i}]: unbekannte Felder: {sorted(unbekannt)}")
    return fehler


def pruefe(root: Path):
    """-> (findings, backend). findings = Liste von Meldungen."""
    kat = root / "00_SYSTEM" / "manifest" / "repos.yaml"
    sch = root / "00_SYSTEM" / "schemas" / "repos.schema.json"
    import yaml
    if not kat.exists(): return [f"Katalog fehlt: {kat}"], BACKEND
    if not sch.exists(): return [f"Schema fehlt: {sch}"], BACKEND
    daten = yaml.safe_load(kat.read_text(encoding="utf-8")) or {}
    # YAML liest 2026-09-21 als date-Objekt. Fuer das Schema ist es ein String (ISO).
    import datetime as _dt
    def _norm(o):
        if isinstance(o, dict):  return {k: _norm(v) for k, v in o.items()}
        if isinstance(o, list):  return [_norm(v) for v in o]
        if isinstance(o, (_dt.date, _dt.datetime)): return o.isoformat()
        return o
    daten = _norm(daten)
    schema = json.loads(sch.read_text(encoding="utf-8"))
    if BACKEND == "jsonschema":
        v = jsonschema.Draft202012Validator(schema)
        fehler = []
        for err in sorted(v.iter_errors(daten), key=lambda e: list(e.path)):
            ort = "/".join(str(x) for x in err.path) or "(Wurzel)"
            fehler.append(f"{ort}: {err.message}")
        return fehler, BACKEND
    return _intern(daten, schema), BACKEND

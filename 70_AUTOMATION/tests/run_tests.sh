#!/usr/bin/env bash
# Basissuite des Prototyps (Etappe 1). Alles zusammen: alle_suiten.sh
set -u
cd "$(dirname "$0")"
python3 weg1/test_suite.py

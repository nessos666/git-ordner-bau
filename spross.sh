#!/usr/bin/env bash
# spross.sh — einen NEUEN Git-Ordner-BAUM aus diesem Baum anlegen (24.09.2026).
#
# Warum: bisher bekam jedes Projekt nur einen einfachen Git-Ordner. Ab jetzt soll es den
# Git-Ordner-BAUM bekommen — dieselbe Ordnung, dieselben Werkzeuge, dieselben Pruefungen.
# Kopiert wird nur das GERICHT (Bereiche, Werkzeuge, Tests, Doku) — NICHT die Daten:
#   nicht .git (frische Historie) · nicht 60_RUNTIME (Arbeitsdaten) · keine Zeiger auf fremde Bestaende.
# Es wird NIE ueberschrieben: existiert das Ziel, bricht es ab.
#
# Aufruf: ./spross.sh <ZIEL> [NAME]
set -u
HIER="$(cd "$(dirname "$0")" && pwd)"
ZIEL="${1:-}"; NAME="${2:-$(basename "${ZIEL:-ba}")}"
[ -n "$ZIEL" ] || { echo "Aufruf: ./spross.sh <ZIEL> [NAME]"; exit 2; }
if [ -e "$ZIEL" ]; then echo "STOP: '$ZIEL' existiert schon — nichts ueberschrieben."; exit 2; fi
mkdir -p "$ZIEL"
tar -C "$HIER" --exclude=./.git --exclude=./60_RUNTIME --exclude=./40_DATEN/pointers \
    --exclude=./ro-crate-metadata.json --exclude=./tmp* --exclude='*.pyc' --exclude=./__pycache__ -cf - . \
  | tar -C "$ZIEL" -xf -
mkdir -p "$ZIEL/40_DATEN/pointers" "$ZIEL/60_RUNTIME"
printf '# Zeiger auf Bestaende ausserhalb des Baums entstehen mit: ./ordner.sh zeiger <Pfad>\n' > "$ZIEL/40_DATEN/pointers/README.txt"
# GEMESSENE Zustaende des Elternbaums NICHT erben (sie gelten fuer einen anderen Ort):
rm -f "$ZIEL/50_INFRA/redundanz.yaml" "$ZIEL/50_INFRA/rollentrennung.yaml"
# Katalog von Eintraegen befreien, die im neuen Baum ins Leere zeigen (z. B. 60_RUNTIME-Artefakte)
if ! python3 -B "$ZIEL/70_AUTOMATION/projects/katalog_bereinigen.py" --ordner "$ZIEL"; then
  echo "WARNUNG: Katalog konnte nicht bereinigt werden (siehe Meldung oben)."
fi
# Selbsttest-Fixtures im neuen Baum erzeugen (sonst ist der Selbsttest DEFEKT)
if ! ( cd "$ZIEL/70_AUTOMATION/tests" && python3 -B make_fixtures.py ); then
  echo "WARNUNG: Selbsttest-Fixtures konnten nicht erzeugt werden (Meldung oben) — der Selbsttest meldet dann DEFEKT."
fi
git -C "$ZIEL" init -q
git -C "$ZIEL" -c user.name='Git-Ordner-Bau' -c user.email='noreply@example.invalid' add -A --ignore-errors >/dev/null
# Selbstbeschreibung + Pruefsummen in der richtigen Reihenfolge (erzeugt auch den Crate)
( cd "$ZIEL" && ./ordner.sh summen >/dev/null ) || { echo "FEHLER: summen im neuen Baum fehlgeschlagen."; exit 2; }
# WICHTIG: Selbstbeschreibung UND Prüfsummenliste müssen mit in den Commit — sonst enthält der erste
# Commit die geerbte Liste des Elternbaums und der neue Baum wäre sofort "schmutzig" (Blocker 09/2026).
git -C "$ZIEL" add -A >/dev/null
git -C "$ZIEL" -c user.name='Git-Ordner-Bau' -c user.email='noreply@example.invalid' commit -q -m "Neuer Git-Ordner-Baum '$NAME' aus Vorlage angelegt"
# Selbstkontrolle: nach dem Anlegen darf nichts offen sein
if [ -n "$(git -C "$ZIEL" status --porcelain)" ]; then
  echo "FEHLER: der neue Baum ist nach dem Anlegen nicht sauber:"; git -C "$ZIEL" status --short; exit 2
fi
echo "Neuer Git-Ordner-Baum: $ZIEL"
echo "  Bereiche: $(cd "$ZIEL" && ls -1d 0*_* 1*_* 2*_* 3*_* 4*_* 5*_* 6*_* 7*_* 8*_* 9*_* 2>/dev/null | wc -l) · Dateien: $(cd "$ZIEL" && git ls-files | wc -l) · Commit: $(git -C "$ZIEL" rev-parse --short HEAD)"
echo "  Naechste Schritte (einmalig):"
echo "    cd \"$ZIEL\" && ./ordner.sh neu          # Suchindex bauen"
echo "    cd \"$ZIEL\" && ./ordner.sh pruefen       # muss 0 Fehler melden"
echo "    python3 -B \"$ZIEL\"/70_AUTOMATION/validation/rollentrennung_messen.py   # Rollentrennung messen"

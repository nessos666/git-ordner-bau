export PYTHONDONTWRITEBYTECODE=1   # Punkt 8: keine __pycache__ im Baum anlegen
#!/usr/bin/env bash
# Diese Suiten brauchen eine Python MIT PyYAML (Katalog). Steht sie in python3 nicht bereit,
# wird die erste gefundene Python mit PyYAML benutzt (gemessen 26.09.2026).
if ! python3 -c "import yaml" 2>/dev/null; then
    for _k in /usr/bin/python3 /usr/local/bin/python3; do
        if [ -x "$_k" ] && "$_k" -c "import yaml" 2>/dev/null; then
            export PATH="$(dirname "$_k"):$PATH"; break
        fi
    done
fi
# alle_suiten.sh — jede Suite laufen lassen (findet test_suite*.py in tests/, tests/weg1/, tests/ausbau/).
# Aufruf: bash 70_AUTOMATION/tests/alle_suiten.sh
set -u
HIER="$(cd "$(dirname "$0")" && pwd)"
fehler=0; n=0; uebersprungen=0
# Der GEMESSENE Originalbaum traegt die Rollentrennungs-Messung. Kopien und frisch angelegte Baeume nicht.
# Punkt 4 (Fremdpruefung 27.09.2026): NICHT an 50_INFRA/rollentrennung.yaml festmachen — diese
# Datei ist selbst versioniert, jeder Klon trug sie mit, galt als Original, und der Ueberspring-
# Schutz konnte nie feuern. Jetzt zaehlt ein Merker, der NIE versioniert wird.
if [ -f "$HIER/../../60_RUNTIME/state/baum_original" ]; then ORIGINAL=1; else ORIGINAL=0; fi
if [ "$ORIGINAL" = "0" ]; then
  echo "Hinweis: kein gemessener Originalbaum (Merker 60_RUNTIME/state/baum_original fehlt)."
  echo "         Suiten, die den Originalbaum brauchen, werden uebersprungen — mit Begruendung."
fi
for f in $(find "$HIER" -maxdepth 2 -name 'test_suite*.py' | sort); do
  n=$((n+1))
  if [ "$ORIGINAL" = "0" ] && grep -qx "$(basename "$f")" "$HIER/braucht_originalbaum.txt" 2>/dev/null; then
    e="uebersprungen (braucht den gemessenen Originalbaum)"
  else
    e="$(timeout 900 python3 -B "$f" 2>&1 | tail -1)"
  fi
  printf '%-30s %s\n' "$(basename "$f")" "$e"
  case "$e" in OK*) ;; uebersprungen*) uebersprungen=$((uebersprungen+1));; *) fehler=$((fehler+1));; esac
done
# --- Aufraeumen (verschaerft 25.09.2026 nach Befund 9 der Fremd-Pruefung): geloescht werden NUR
# die eigenen Scratch-Ordner der Suiten. Jedes andere "tmp*" neben dem Baum wird nur GEMELDET.
for d in "$HIER"/../../../tmp[0-9]* "$HIER"/../../../tmp_tests "$HIER"/../../../tmp_gegen "$HIER"/../../../tmp_unabh; do
  [ -e "$d" ] || continue
  name="$(basename "$d")"
  if [ -d "$d" ] && [ "$(readlink -f "$d")" != "$(readlink -f "$HIER/../../..")" ]; then
    rm -rf "$d" && echo "aufgeraeumt (eigener Testrest): $name"
  fi
done
for d in "$HIER"/../../../tmp*; do
  [ -e "$d" ] || continue
  name="$(basename "$d")"
  case "$name" in tmp[0-9]*|tmp_tests|tmp_gegen|tmp_unabh|tmp_25|tmp_probe) continue;; esac
  echo "HINWEIS: '$name' bleibt unangetastet (nicht von den Suiten angelegt) — bitte selbst pruefen."
done
echo "--- $n Suiten, $fehler mit Fehlern, $uebersprungen uebersprungen"
[ "$fehler" -eq 0 ]

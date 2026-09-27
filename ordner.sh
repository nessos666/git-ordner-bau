#!/usr/bin/env bash
# ordner.sh — Bedienung des Git-Ordner-Baums (Etappe 2.8, Weg 1)
# Aufruf:  ./ordner.sh hilfe | status | pruefen | suchen "begriff" | neu
set -u
HIER="$(cd "$(dirname "$0")" && pwd)"
# Der Pruefer muss den Katalog lesen koennen (PyYAML). Fehlt die Bibliothek in python3, nimmt
# das Skript die erste Python, die sie hat; sonst meldet der Pruefer es als Befund.
PY="${PY:-python3}"
if ! "$PY" -c "import yaml" 2>/dev/null; then
    for _k in /usr/bin/python3 /usr/local/bin/python3; do
        if [ -x "$_k" ] && "$_k" -c "import yaml" 2>/dev/null; then PY="$_k"; break; fi
    done
fi
case "${1:-hilfe}" in
  status)
    "$PY" -B "$HIER/70_AUTOMATION/indexing/indexer.py" status --root "$HIER";;
  pruefen)
    "$PY" -B "$HIER/70_AUTOMATION/validation/check_all.py" --root "$HIER"; rc=$?
    # Der Regelpruefer braucht fuer eine Probe ein Schreibverzeichnis. Es lag bisher als "tmp_probe"
    # NEBEN dem Baum und blieb liegen (Zweitpruefung 25.09.2026, Befund 8) — hier wird es entfernt.
    rm -rf "$HIER/../tmp_probe" 2>/dev/null || true
    # Selbstbeschreibung anzeigen — die VERBINDLICHE Pruefung steckt seit 25.09.2026 als Regel CRATE in check_all
    if [ -f "$HIER/ro-crate-metadata.json" ]; then
      "$PY" -B "$HIER/70_AUTOMATION/crate/ro_crate.py" --pruefen "$HIER" | sed 's/^/CRATE: /' || true
    fi
    exit $rc;;
  suchen)
    [ $# -ge 2 ] || { echo "Nutzung: ./ordner.sh suchen \"begriff\""; exit 2; }
    shift
    "$PY" -B "$HIER/70_AUTOMATION/indexing/indexer.py" search "$*" --root "$HIER";;
  neu)
    "$PY" -B "$HIER/70_AUTOMATION/indexing/indexer.py" build --root "$HIER"    # Punkt 4: Merker setzen — dieser Baum gilt ab jetzt als GEMESSENER Originalbaum.
    mkdir -p "$HIER/60_RUNTIME/state" && : > "$HIER/60_RUNTIME/state/baum_original"
    ;;
  zeiger)
    [ $# -ge 2 ] || { echo "Nutzung: ./ordner.sh zeiger <Pfad> [Name]"; exit 2; }
    shift; NAME="${2:-}"; PFAD="$1"
    if [ -n "$NAME" ]; then
      "$PY" -B "$HIER/70_AUTOMATION/pointers/zeiger_bauen.py" "$PFAD" --name "$NAME" --root "$HIER"
    else
      "$PY" -B "$HIER/70_AUTOMATION/pointers/zeiger_bauen.py" "$PFAD" --root "$HIER"
    fi;;
  projekt)
    [ $# -ge 2 ] || { echo "Nutzung: ./ordner.sh projekt \"name\" [bereich]   (z.B.: ./ordner.sh projekt island_sprache standalone)"; exit 2; }
    "$PY" -B "$HIER/70_AUTOMATION/projects/neues_projekt.py" --root "$HIER" --name "$2" ${3:+--bereich "$3"};; 
  finden)
    [ $# -ge 2 ] || { echo "Nutzung: ./ordner.sh finden \"begriff\"   (sucht IM INHALT der angebundenen Bestaende)"; exit 2; }
    "$PY" -B "$HIER/70_AUTOMATION/pointers/finden.py" --root "$HIER" --begriff "$2";;
  dateien)
    [ $# -ge 2 ] || { echo "Nutzung: ./ordner.sh dateien \"muster\"   (Dateinamen im Baum UND in den angebundenen Bestaenden)"; exit 2; }
    "$PY" -B "$HIER/70_AUTOMATION/pointers/suchen_namen.py" dateien --root "$HIER" --muster "$2";;
  springen)
    "$PY" -B "$HIER/70_AUTOMATION/pointers/suchen_namen.py" springen --root "$HIER" ${2:+--muster "$2"};;
  doppelt)
    [ $# -ge 2 ] || { echo "Nutzung: ./ordner.sh doppelt <Pfad>   (BERICHTET doppelte Dateien — loescht nichts)"; exit 2; }
    "$PY" -B "$HIER/70_AUTOMATION/pointers/doppelte.py" --pfad "$2" --root "$HIER";;
  bag)
    if [ "${2:-}" = "--pruefen" ]; then
      [ $# -ge 3 ] || { echo "Nutzung: ./ordner.sh bag --pruefen <Bag>"; exit 2; }
      "$PY" -B "$HIER/70_AUTOMATION/bagit/bagit_bauen.py" --pruefen "$3"
    else
      [ $# -ge 3 ] || { echo "Nutzung: ./ordner.sh bag <Quelle> <Ziel>"; exit 2; }
      "$PY" -B "$HIER/70_AUTOMATION/bagit/bagit_bauen.py" --quelle "$2" --ziel "$3"
    fi;;
  crate)
    shift
    case "${1:-}" in
      --zeiger|--pruefen) "$PY" -B "$HIER/70_AUTOMATION/crate/ro_crate.py" "$1" "${2:-$HIER}";;
      *) "$PY" -B "$HIER/70_AUTOMATION/crate/ro_crate.py" --ordner "${1:-$HIER}" ${2:+--name "$2"} ${3:-};;
    esac;;
  vorlage)
    [ $# -ge 3 ] || { echo "Nutzung: ./ordner.sh vorlage <Projektordner> <name>   (Vorlagen: standard, forschung, handwerk, trading)"; exit 2; }
    shift
    "$PY" -B "$HIER/70_AUTOMATION/projects/vorlage_anwenden.py" --ordner "$1" --vorlage "$2";;
  spross)
    [ $# -ge 2 ] || { echo "Nutzung: ./ordner.sh spross <Ziel> [Name]   (legt einen NEUEN Git-Ordner-Baum an)"; exit 2; }
    shift
    bash "$HIER/spross.sh" "$1" ${2:-};; 
  summen)
    # Nach JEDER Aenderung an verfolgten Dateien: neue Dateien aufnehmen, dann Selbstbeschreibung,
    # dann Pruefsummen. Diese Reihenfolge ist Pflicht — sonst fehlen neue Dateien in der Liste (K9)
    # oder Crate und Pruefsummen beschreiben sich gegenseitig falsch.
    _top="$(git -C "$HIER" rev-parse --show-toplevel 2>/dev/null || true)"
    [ "$_top" = "$HIER" ] || { echo "STOP: $HIER ist kein eigenes Git-Repository (gehoert zu: ${_top:-keinem})";
                               echo "      summen wuerde sonst die Dateiliste des Eltern-Repos schreiben (OpenCode-Befund F8)."; exit 2; }
    # --ignore-errors: ein eingebettetes Unter-Repo OHNE Commit laesst "git add -A" sonst hart
    # abbrechen ("does not have a commit checked out") — der Baum soll aber weiter summen
    # koennen. Was ausgelassen wurde, wird gemeldet (OpenCode-Befund, Ursache 25.09.2026).
    # REIHENFOLGE (Befund eines Fremdpruefers, 25.09.2026): erst die Selbstbeschreibung erzeugen,
    # DANN aufnehmen, DANN die Pruefsummenliste bauen. Vorher lief "git add" zuerst: die frisch
    # erzeugte ro-crate-metadata.json war beim Bauen der Liste noch unverfolgt und fehlte darin —
    # K9 meldete in einem FRISCHEN Baum darum einen Fehler; erst ein zweites "summen" half.
    "$PY" -B "$HIER/70_AUTOMATION/crate/ro_crate.py" --ordner "$HIER" | tail -1
    if ! ( cd "$HIER" && git add -A --ignore-errors 2>/dev/null ); then
      echo "HINWEIS: git add konnte nicht alles aufnehmen (eingebettetes Unter-Repo ohne Commit?) —";
      ( cd "$HIER" && git add -A --ignore-errors 2>&1 | head -3 );
    fi
    # Tote Verweise (Symlink ohne Ziel) gehoeren NICHT in die Liste, duerfen 'summen' aber nicht
    # abbrechen — sie werden uebersprungen und gemeldet (OpenCode-Befund: sha256sum scheiterte hart).
python3 "$HIER/70_AUTOMATION/crate/liste_aus_crate.py" "$HIER" "$HIER/PRUEFSUMMEN_MASTER.txt" \
    || { echo "STOP: Pruefsummenliste nicht erzeugbar"; exit 2; }
    ( cd "$HIER" && git add -A >/dev/null 2>&1 )
    echo "PRUEFSUMMEN_MASTER.txt neu erzeugt: $(wc -l < "$HIER/PRUEFSUMMEN_MASTER.txt") Zeilen — jetzt committen.";;
  formate)
    "$PY" -B "$HIER/70_AUTOMATION/validation/formate_pruefen.py" --ordner "$HIER";;
  hilfe|*)
    cat <<'HILFE'
Git-Ordner-Baum — sechzehn Befehle

  ./ordner.sh status            Kurzer Zustand: Index vorhanden/frisch? Quellen vollstaendig?
  ./ordner.sh pruefen           Vollpruefung des Baums (Katalog, Regeln, Secrets, Index)
  ./ordner.sh suchen "begriff"  Im ganzen Baum suchen (Inhalt + Namen)
  ./ordner.sh neu               Suchindex neu bauen (der Index ist nur eine Projektion)
  ./ordner.sh zeiger <Pfad>     Bestand ausserhalb read-only aufnehmen (Zeiger + Pruefsummen-Liste)
  ./ordner.sh finden "begriff"  IM INHALT der angebundenen Bestaende suchen (nur lesend)
  ./ordner.sh projekt "name"     Neues Projekt mit FESTER NUMMER anlegen (001_name_JJJJ-MM-TT)
  ./ordner.sh dateien "muster"  Dateinamen suchen (Baum + angebundene Bestaende)
  ./ordner.sh springen "muster" Zu einem Projekt/Ordner springen (Pfeiltasten)
  ./ordner.sh doppelt <Pfad>    Doppelte Dateien BERICHTEN (nur lesen, nie loeschen)
  ./ordner.sh crate [Ordner]    Ordner SELBSTBESCHREIBEND machen (RO-Crate, Standard)
  ./ordner.sh vorlage <Ordner> <name>  Vorlage anwenden (standard|forschung|handwerk|trading)
  ./ordner.sh bag <Quelle> <Ziel>      Normgerechte BagIt-Sicherung bauen (RFC 8493)
  ./ordner.sh spross <Ziel> [Name]     NEUEN Git-Ordner-Baum anlegen (Vorlage: dieser Baum)
  ./ordner.sh formate                   Dateitypen + Namen markieren (aendert nichts)
  ./ordner.sh summen                    Selbstbeschreibung + Pruefsummen nachziehen (nach JEDER Aenderung)

Exitcodes der Vollpruefung: 0 = OK  1 = WARNUNG  2 = FEHLER  3 = KRITISCH  4 = UNBESTAETIGT
Der Baum wird nie veraendert: pruefen liest nur, neu baut nur den Suchindex neu.
HILFE
    ;;
esac

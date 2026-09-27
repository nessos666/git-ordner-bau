#!/usr/bin/env bash
# sicherung.sh — Zweite Kopie erzeugen und die Wiederherstellung BEWEISEN.
# Aufruf: ./sicherung.sh kopie <ZIEL>          (legt <ZIEL>/baum, <ZIEL>/repo.bundle, <ZIEL>/PRUEFSUMMEN.sha256 an)
#         ./sicherung.sh kopie <ZIEL> --bag     (zusatzlich eine NORMGERECHTE BagIt-Sicherung, RFC 8493)
#         ./sicherung.sh pruefen <KOPIE>       (Pruefsummen der Kopie gegen das Manifest)
#         ./sicherung.sh wiederherstellen <KOPIE> <ZIELNEU>   (Restore + Pruefsummenvergleich)
set -u
HIER="$(cd "$(dirname "$0")" && pwd)"
BAUM="$HIER"; ZEIT="$(date +%Y-%m-%dT%H:%M:%S%z)"
# Unterschale: das cd darf NICHT in der Hauptshell wirken (OpenCode-Befund F4) — sonst landen
# relative Ziele nach dem Aufruf im falschen Verzeichnis.
manifest() { ( cd "$1" && find . -type f -not -path './60_RUNTIME/*' -not -path './.git/*' \
              -not -name '*.lock' -print0 | sort -z | xargs -0 sha256sum ) > "$2"; }

case "${1:-}" in
  kopie)
    ZIEL="${2:-}"; [ -n "$ZIEL" ] || { echo "Aufruf: ./sicherung.sh kopie <ZIEL> [--bag]"; exit 2; }
    ZIEL="$(realpath -m "$ZIEL")"     # absolut (OpenCode-Befund F4: relative Pfade + cd)
    mkdir -p "$ZIEL"
    rm -rf "$ZIEL/baum"; mkdir -p "$ZIEL/baum"
    # 1:1-Kopie OHNE den fluessigen Zustand (60_RUNTIME) und ohne .git-Arbeitskopie
    tar -C "$BAUM" --exclude=./60_RUNTIME --exclude=./.git -cf - . | tar -C "$ZIEL/baum" -xf -
    manifest "$ZIEL/baum" "$ZIEL/PRUEFSUMMEN.sha256"
    _top="$(git -C "$BAUM" rev-parse --show-toplevel 2>/dev/null || true)"
    if [ "$_top" != "$BAUM" ]; then
      echo "HINWEIS: Quellbaum ist kein eigenes Git-Repository (gehoert zu: ${_top:-keinem}) — kein Buendel."
      echo "        Sonst wuerde git die Historie des ELTERN-Repos buendeln (OpenCode-Befund F5)."
    else
      # 'bundle verify' braucht ein Repository — deshalb im QUELLBAUM pruefen, nicht im Ziel.
      GB=""
      GB="$(git -C "$BAUM" bundle create "$ZIEL/repo.bundle" --all 2>&1)" || {
        echo "FEHLER: Git-Buendel konnte NICHT erzeugt werden — die Kopie ist UNVOLLSTAENDIG (ohne Historie)."
        echo "        Grund: $(echo "$GB" | tail -1)"
        echo "        Kopie: $ZIEL"
        exit 2
      }
      GB="$(git -C "$BAUM" bundle verify "$ZIEL/repo.bundle" 2>&1)" || {
        echo "FEHLER: Git-Buendel ist NICHT lesbar — die Kopie ist UNVOLLSTAENDIG (ohne Historie)."
        echo "        Grund: $(echo "$GB" | tail -1)"
        echo "        Kopie: $ZIEL"
        exit 2
      }
    fi
    printf 'ZEIT=%s\nDATEIEN=%s\nQUELLE=%s\nQUELLSTAND=%s\n' "$ZEIT" "$(wc -l < "$ZIEL/PRUEFSUMMEN.sha256")" "$BAUM" "$(sha256sum "$BAUM/PRUEFSUMMEN_MASTER.txt" 2>/dev/null | cut -c1-64)" > "$ZIEL/README.txt"
    if [ "${3:-}" = "--bag" ]; then
      python3 -B "$BAUM/70_AUTOMATION/bagit/bagit_bauen.py" --quelle "$ZIEL/baum" --ziel "$ZIEL/bag" | tail -1
      python3 -B "$BAUM/70_AUTOMATION/bagit/bagit_bauen.py" --pruefen "$ZIEL/bag" | tail -1
    fi
    cat "$ZIEL/README.txt";;
  pruefen)
    K="${2:-}"; [ -n "$K" ] || { echo "Aufruf: ./sicherung.sh pruefen <KOPIE>"; exit 2; }
    K="$(realpath -m "$K")"
    rc=0
    # (a) Vergleich mit dem eigenen Manifest der Kopie — sagt nur, dass die Kopie mit sich stimmt.
    if ( cd "$K/baum" && sha256sum -c "$K/PRUEFSUMMEN.sha256" --quiet ); then
      echo "PRUEFSUMMEN: OK ($(wc -l < "$K/PRUEFSUMMEN.sha256") Dateien)"
    else
      echo "PRUEFSUMMEN: FEHLER (Kopie weicht von ihrem eigenen Manifest ab)"; rc=2
    fi
    # (b) Vergleich gegen den QUELLBAUM. Wichtig (Zweitpruefung 25.09.2026): die Liste darf NICHT aus
    # der Kopie selbst kommen — sonst quittiert eine manipulierte Kopie sich selbst mit "OK".
    # Der Quellpfad steht in README.txt der Kopie (Feld QUELLE=).
    QUELLE="$(sed -n 's/^QUELLE=//p' "$K/README.txt" 2>/dev/null | head -1)"
    if [ -n "$QUELLE" ] && [ -f "$QUELLE/PRUEFSUMMEN_MASTER.txt" ]; then
      if cmp -s "$QUELLE/PRUEFSUMMEN_MASTER.txt" "$K/baum/PRUEFSUMMEN_MASTER.txt"; then
        echo "LISTE DES QUELLBAUMS: identisch mit der Liste in der Kopie"
      else
        echo "LISTE DES QUELLBAUMS: WEICHT AB — die Liste in der Kopie ist nicht die des Baums"; rc=2
      fi
      if ( cd "$K/baum" && sha256sum -c "$QUELLE/PRUEFSUMMEN_MASTER.txt" --quiet >/dev/null 2>&1 ); then
        echo "GEGEN DEN BAUM: OK (Kopie stimmt mit der Pruefsummenliste des QUELLBAUMS ueberein)"
      else
        echo "GEGEN DEN BAUM: FEHLER — Kopie passt NICHT zur Pruefsummenliste des Quellbaums"; rc=2
      fi
    else
      echo "GEGEN DEN BAUM: nicht pruefbar (QUELLE fehlt in README.txt oder Quellbaum nicht erreichbar)"; rc=2
    fi
    exit $rc;;
  wiederherstellen)
    K="${2:-}"; N="${3:-}"; [ -n "$K" ] && [ -n "$N" ] || { echo "Aufruf: ./sicherung.sh wiederherstellen <KOPIE> <ZIELNEU>"; exit 2; }
    K="$(realpath -m "$K")"; N="$(realpath -m "$N")"
    # Wache (OpenCode-Befund F9): niemals /, $HOME, die Quelle selbst oder deren Eltern loeschen.
    case "$N" in
      "/"|"$HOME"|"$K"|"$K"/*|"$(dirname "$K")") echo "STOP: Ziel wird nicht angetastet (Schutzgrenze): $N"; exit 2;;
    esac
    rm -rf "$N"; mkdir -p "$N"
    tar -C "$K/baum" -cf - . | tar -C "$N" -xf -
    cd "$N" && sha256sum -c "$K/PRUEFSUMMEN.sha256" --quiet && echo "WIEDERHERSTELLUNG: OK — Pruefsummen identisch"
    git clone -q "$K/repo.bundle" "$N.git" 2>/dev/null && chmod -R u+rwX "$N.git" 2>/dev/null
    g="$(git -C "$N.git" rev-parse --short HEAD 2>/dev/null)"
    if [ -z "$g" ]; then printf 'GIT AUS BUENDEL: FEHLGESCHLAGEN — Historie fehlt\n'; exit 2; fi
    printf 'GIT AUS BUENDEL: %s\n' "$g";;
  *) echo "Aufruf: ./sicherung.sh kopie <ZIEL> | pruefen <KOPIE> | wiederherstellen <KOPIE> <NEU>";;
esac

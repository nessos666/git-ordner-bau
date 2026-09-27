# Merkblatt: Ein neues Thema anlegen

**Ein Thema = ein Ordner im Git-Ordner-Baum.** Mehr nicht. Kein neuer Baum, keine Umlagerung.
Der Baum **beschreibt**, was wo liegt — er verschiebt, benennt und löscht nichts.

_Gilt ab 27.09.2026 (Entscheid „Option 2"). Vorher entstanden neue Ordner aus einer anderen Vorlage —
die bleiben alle, wo sie sind._

---

## In drei Schritten

```bash
neuesProjekt "mein_thema"                  # 1) Thema anlegen (Nummer vergibt das Werkzeug selbst)
neuesProjekt "mein_thema" --vorlage forschung   #    andere Vorlage: standard|forschung|handwerk|trading
                                           # 2) fertig — das Werkzeug macht den Rest:
                                           #    3) Selbstbeschreibung + Prüfsummen + Kontrolle + 1 Commit
```

Auslöser im Chat: **„neues Thema …"** oder **„neuer Ordner …"** — beides legt einen Baum-Ordner an.

## Was danach anders ist (nachgemessen am 27.09.2026)

Genau **vier** Dinge im Baum: der **Katalog**, die neue **STATUS.md**, die **Selbstbeschreibung**,
die **Prüfsummenliste**. Danach meldet die Kontrolle **0 Fehler**.
**Außerhalb des Baums: nichts.**

## Was dabei NIE passiert

- **kein neuer Git-Ordner-Baum** (das geht nur ausdrücklich: `./ordner.sh spross <Ziel>`)
- **nichts wird verschoben, umbenannt oder gelöscht**
- große Bestände bekommen nur einen **Zeiger** (Ort, Größe, Prüfsumme) — die Originale bleiben liegen
- **kein Upload, kein Push, kein Cron**, keine Hintergrund-Automatik

## Welcher Befehl wofür

| Zweck | Befehl |
|---|---|
| **Neues Thema** (Normalfall) | `neuesProjekt "mein_thema"` |
| Thema mit anderer Vorlage | `neuesProjekt "mein_thema" --vorlage forschung` |
| Ganz neuer Baum (Ausnahme, nur auf Ansage) | `./ordner.sh spross <Ziel>` |
| Klassischer Ordner für Archiv/System/Temp | `neuesProjekt "name" --klassisch` |
| Bestehenden Ordner einsortieren (er bleibt liegen) | `./ordner.sh zeiger <Objekt>` |

## Nachschauen

```bash
ordner status                 # liegt alles richtig?
ordner pruefen                # 0 Fehler?
ordner suchen "begriff"       # im Katalog und in den Beschreibungen
ordner finden "begriff"       # IM Inhalt der angebundenen Bestände (nur lesend)
ordner springen               # wohin komme ich als Nächstes?
```

**Im Zweifel:** `ordner --hilfe` zeigt alle 16 Befehle mit einem Satz.

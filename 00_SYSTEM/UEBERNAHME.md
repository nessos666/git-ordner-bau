# ÜBERNAHME — eine Seite für einen Menschen ohne Vorwissen  ·  PROTOTYPE

**Was ist das?** Ein geordneter Ordnerbaum mit Regeln und einem Prüfer. Er verwaltet Verweise,
keine Daten.

**Wo liegen die Daten?** Nicht hier. `40_DATEN/pointers/` zeigt auf Objekte; die Objekte selbst
liegen **außerhalb** des Baums (im Prototyp: neben dem Baum, `~/HAUPTLAGER/03_PROJEKTE/55_Git_Ordner_Prototyp/daten/`).

**Wie prüft man alles?** `python3 70_AUTOMATION/validation/check_all.py --root <MASTER-Wurzel>`
Ausgabe = eine Statuszeile. `CRITICAL` heißt: sofort ansehen.

**Was ist wertvoll?** `00_SYSTEM/manifest/repos.yaml` (der Katalog) und die Repositories.
**Was kann weg?** `60_RUNTIME/cache/` — jederzeit löschbar.

**Schlüssel:** Im Prototyp **keine** Verschlüsselung, **keine** Passphrase.
Ort der Passphrase (im echten Betrieb): siehe `passphrase_ort` im Katalog-Kopf.
**Notfallkontakt:** im Katalog-Kopf (`notfallkontakt`).

**PROTOTYPE — NOT PRODUCTION**

# Recoll — optionaler Zusatz zur Inhaltssuche (Stand 24.09.2026)

**Gemessen: Recoll ist auf diesem Rechner NICHT installiert.** Die Installation braucht ein
Administrator-Passwort — **das darf nur David eingeben**, das Programm fragt es nie ab.
**Nötig ist sie nicht:** die Suche in PDF/DOCX läuft bereits ohne Recoll.

## Was schon läuft — ohne Installation, gemessen

```bash
./ordner.sh finden "begriff"
```
| Was | Womit | Ergebnis an echten Daten (Island-Dossier) |
|---|---|---|
| Textdateien (.txt/.md/.py/.json) | `rg` (ripgrep) | sofort |
| **PDF** | `pdftotext` | Treffer **im PDF-Text** ✓ |
| **DOCX · ODT · XLSX · PPTX** | `libreoffice --headless` | Text wird herausgeholt ✓ |
| Wiederholte Suche | Zwischenspeicher `60_RUNTIME/dokumenttext/` | **1,5 s → 0,1 s** (15× schneller) |

Der Zwischenspeicher ist nach dem **Inhalt** der Datei benannt (SHA256): eine geänderte Datei
bekommt automatisch einen neuen Eintrag — ein veralteter Eintrag kann keine falschen Treffer
liefern. Er liegt in `60_RUNTIME` und wird **nie** von Git verfolgt.

## Wenn du Recoll trotzdem willst (deine Entscheidung, dein Passwort)

```bash
sudo apt update && sudo apt install -y recoll
recoll -c ~/.recoll          # Einrichtung; als topdirs: /home/user/HAUPTLAGER/03_PROJEKTE
recollindex                  # dauert Minuten, je nach Datenmenge
recoll -t "begriff"          # Textsuche im Terminal
```
**Vorteil:** dauerhafter Index über sehr große Bestände, auch E-Mails.
**Nachteil:** ein zusätzlicher Hintergrund-Index, der gepflegt werden muss.
Für deine Größenordnung (16 PDFs im Island-Dossier, Sekunden statt Minuten) reicht die
vorhandene Lösung — Recoll ist die Option für später, nicht die Voraussetzung.

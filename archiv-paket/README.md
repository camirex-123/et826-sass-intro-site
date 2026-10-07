# Archiv-Paket Aktenarchiv

Enthaelt nur Regeln und Werkzeuge, keine Falldaten. Voraussetzung: Python 3.8+ (ohne Zusatzpakete).

## Einrichtung (Windows, PowerShell)
1. Kopiere diesen Ordnerinhalt (`AGENTS.md`, `README.md`, `.gitignore`, `tools\`) in `D:\Codex\Aktenarchiv_Archiv\`.
   Das ist ein NEUER Ordner. Dein bestehender Ordner bleibt unberuehrt.
2. `cd D:\Codex\Aktenarchiv_Archiv`
3. `python tools\aufbau.py` legt die Ordner an.
4. Kopiere (nicht verschieben) deine Dateien aus `D:\Codex\Aktenarchiv` in `00_Eingang_ungeprueft\`.
5. `python tools\inventar.py` erfasst alles und markiert exakte Duplikate.
6. `python tools\pruefen.py` zeigt Fehler und Hinweise.
7. Starte Codex in diesem Ordner. Es liest `AGENTS.md` und sortiert nach den Regeln.

## Wichtig
- Kein Git-Repo ohne Passwortschutz oder in einem oeffentlichen Repo. Die `.gitignore` schliesst die Akten aus.
- Sichere das Archiv verschluesselt (z. B. BitLocker oder Veracrypt-Container) und gib es den Rechtsanwalt nur ueber einen
  vereinbarten sicheren Weg.

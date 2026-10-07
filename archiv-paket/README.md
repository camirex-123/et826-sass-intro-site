# Archiv-Paket Aktenarchiv

Enthaelt nur Regeln und Werkzeuge, keine Falldaten. Voraussetzung: Python 3.8+ (ohne Zusatzpakete).

## Einrichtung ohne zusaetzlichen Speicherplatz (empfohlen, wenn D: knapp ist)
0. **Zuerst Sicherung**: Kopiere den Ordner einmal auf ein anderes Laufwerk (externe Platte, C: oder USB).
   Pruefe vorher in PowerShell, ob es passt:
   `(Get-ChildItem D:\Codex\Amtshaftungsklage -Recurse -File | Measure-Object Length -Sum).Sum/1GB` (Groesse in GB),
   `Get-PSDrive D` (freier Platz). Ohne Sicherung nicht weitermachen.
1. Alles in einen Unterordner VERSCHIEBEN (kostet auf demselben Laufwerk keinen Platz):
   ```
   $r = "D:\Codex\Amtshaftungsklage"
   New-Item "$r\00_Eingang_ungeprueft" -ItemType Directory
   Get-ChildItem $r -Force | Where-Object Name -ne "00_Eingang_ungeprueft" | Move-Item -Destination "$r\00_Eingang_ungeprueft"
   ```
2. Jetzt erst `AGENTS.md`, `README.md`, `.gitignore` und `tools\` in `$r` kopieren (klein, kaum Platz).
3. `cd D:\Codex\Amtshaftungsklage`, dann `python tools\aufbau.py`, `python tools\inventar.py`, `python tools\sortieren.py`.
4. Vorschlag in `index\zuordnung_vorschlag.csv` pruefen, dann `python tools\sortieren.py --anwenden`. Der alte Pfad jeder Datei bleibt im Index (`vorher:`).
5. `python tools\pruefen.py`, danach Codex in diesem Ordner starten.

Duplikate werden nur markiert und spaeter nach `99_Duplikate_Quarantaene` verschoben. Erst wenn du sie freigibst,
wird dadurch Platz frei.

## Wichtig
- Kein Git-Repo ohne Passwortschutz oder in einem oeffentlichen Repo. Die `.gitignore` schliesst die Akten aus.
- Sichere das Archiv verschluesselt (z. B. BitLocker oder Veracrypt-Container) und gib es den Rechtsanwalt nur ueber einen
  vereinbarten sicheren Weg.

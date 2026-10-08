"""Schreibt die Chronologie aller Dokumente nach Dokumentdatum (aufsteigend).
Ergebnis in <ZIEL>: chronologie_auto.csv (fuer Tabellen/Codex) und chronologie_auto.md (zum Lesen, nach Jahr/Monat).
Bestehende Dateien mit anderen Namen im Zielordner werden nie angefasst.
Gesicherte Daten (hoch/mittel) stehen in der Zeitleiste; ungesicherte (niedrig) getrennt am Ende zur Pruefung.
Duplikate erscheinen nicht einzeln, sondern als Anzahl 'Kopien' beim Original.
Arbeitsdateien (Standard: md, csv, ps1, py, svg) und --ausschliessen-Ordner erscheinen nicht.
Aufruf:  python tools/chronologie.py ARCHIV_WURZEL --ziel "KANZLEI_CODEX_CASE_TEMPLATE/02_CHRONOLOGIE"
         [--ohne-typen md,csv,ps1,py,svg] [--ausschliessen "KANZLEI_CODEX_CASE_TEMPLATE/00_MASTER"] """
import csv, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from archiv_lib import *

args = sys.argv[1:]
ziel = args[args.index("--ziel") + 1].replace("\\", "/").strip("/") if "--ziel" in args else ""
if not ziel:
    sys.exit('FEHLER: --ziel fehlt, z. B. --ziel "KANZLEI_CODEX_CASE_TEMPLATE/02_CHRONOLOGIE"')
ohne = {"." + t.strip().lower().lstrip(".") for t in (args[args.index("--ohne-typen") + 1] if "--ohne-typen" in args else "md,csv,ps1,py,svg").split(",") if t.strip()}
aus = [a.strip().replace("\\", "/").strip("/") for a in (args[args.index("--ausschliessen") + 1] if "--ausschliessen" in args else "").split(",") if a.strip()]
rest = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or args[i - 1] not in ("--ziel", "--ohne-typen", "--ausschliessen"))]
wurzel = os.path.abspath(rest[0] if rest else os.getcwd())
zeilen = lese_index(wurzel)
kopien = {}
for z in zeilen:
    if z["status"] == "duplikat" and z["duplikat_von"]:
        kopien[z["duplikat_von"]] = kopien.get(z["duplikat_von"], 0) + 1
dok = [z for z in zeilen if z["status"] not in ("duplikat", "ausgelagert") and z.get("dokdatum")
       and not z["pfad"].replace("\\", "/").startswith(ziel + "/")
       and os.path.splitext(z["name"])[1].lower() not in ohne
       and not any(z["pfad"].replace("\\", "/").startswith(a + "/") for a in aus)]
dok.sort(key=lambda z: (z["dokdatum"], z["name"].lower()))
sicher = [z for z in dok if z["dokdatum_konf"] in ("hoch", "mittel")]
unsicher = [z for z in dok if z["dokdatum_konf"] not in ("hoch", "mittel")]
os.makedirs(os.path.join(wurzel, ziel), exist_ok=True)

with open(os.path.join(wurzel, ziel, "chronologie_auto.csv"), "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f, delimiter=";")
    w.writerow(["datum", "sicherheit", "quelle_des_datums", "doc_id", "id", "dateiname", "ordner", "weitere_daten", "kopien"])
    for z in sicher + unsicher:
        w.writerow([z["dokdatum"], z["dokdatum_konf"], z["dokdatum_quelle"], z.get("doc_id", ""), z["id"], z["name"],
                    os.path.dirname(z["pfad"]).replace("\\", "/"), z.get("dokdatum_alt", ""), kopien.get(z["id"], 0)])


def zeile(z):
    k = kopien.get(z["id"], 0)
    return (f"- **{z['dokdatum']}** `{z.get('doc_id') or z['id']}` {z['name']}  \n  _Datum: {z['dokdatum_quelle']}, {z['dokdatum_konf']}"
            f"{'; weitere Daten: ' + z['dokdatum_alt'] if z.get('dokdatum_alt') else ''}"
            f"{'; ' + str(k) + ' Kopie(n)' if k else ''}_")


md = ["# Chronologie der Dokumente", "",
      "Sortiert nach **Dokumentdatum** (nicht Download-Datum). Quelle und Sicherheit stehen bei jedem Eintrag.",
      "Nur Dokumente mit gesichertem Datum (hoch/mittel) stehen in der Zeitleiste; die uebrigen am Ende zur Pruefung.",
      "",
      "**Hinweis:** Diese Liste ordnet Dokumente nach Datum. Aus der zeitlichen Abfolge folgt keine Kausalitaet. Sie ist eine Arbeitsgrundlage",
      "und ersetzt weder Chronologie-Ereignisse (CHR-) noch eine rechtliche Bewertung. Das Datum ist maschinell ermittelt und zu pruefen.",
      f"{len(sicher)} Dokumente mit gesichertem Datum, {len(unsicher)} zur Pruefung.", ""]
jahr = monat = None
for z in sicher:
    j, m = z["dokdatum"][:4], z["dokdatum"][:7]
    if j != jahr:
        md += ["", f"## {j}"]
        jahr, monat = j, None
    if m != monat:
        md += ["", f"### {m}", ""]
        monat = m
    md.append(zeile(z))
md += ["", "## Datum ungesichert (bitte pruefen)", "",
       "Bei diesen Dokumenten stammt das Datum nur vom Datei- oder Download-Zeitpunkt. Bitte Datum im Index (Spalte `datum`) eintragen.", ""]
md += [zeile(z) for z in unsicher]
with open(os.path.join(wurzel, ziel, "chronologie_auto.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(md) + "\n")
print(f"{len(sicher)} gesichert, {len(unsicher)} ungesichert -> {os.path.join(wurzel, ziel)}")

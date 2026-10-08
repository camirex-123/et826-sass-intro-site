"""Bewertet Duplikate NEU, mit fester Rangfolge statt Zufall. Loescht und verschiebt NICHTS.
Gleicher SHA-256 = gleicher Inhalt. Je Gruppe wird ein 'Original' gewaehlt:
  1. Pfad beginnt mit einem Eintrag aus --bevorzugt (in dieser Reihenfolge)
  2. bereits geprueftes Dokument (status geprueft/zugeordnet-auto)
  3. Name ohne 'Kopie', 'copy', '(1)' usw. (Kopien-Namen verlieren)
  4. aeltestes Aenderungsdatum
  5. kuerzester Pfad
Alle anderen Dateien der Gruppe werden 'duplikat' mit Verweis auf das Original.
Ergebnis: index/dokumente.csv (status, duplikat_von) und index/duplikat_gruppen.csv zur Pruefung.
Leere Dateien (0 Byte) werden nie als Duplikat gewertet.
Aufruf:
  python tools/duplikate.py ARCHIV_WURZEL --bevorzugt "KANZLEI_CODEX_CASE_TEMPLATE/01_ORIGINALE,KANZLEI_CODEX_CASE_TEMPLATE"
Ohne --bevorzugt entscheiden nur Punkt 2 bis 5. Nur Zahlen werden auf dem Bildschirm gezeigt, keine Dateinamen."""
import csv, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from archiv_lib import *

args = sys.argv[1:]
bevorzugt = []
if "--bevorzugt" in args:
    i = args.index("--bevorzugt")
    bevorzugt = [b.strip().strip("/\\").replace("\\", "/") for b in args[i + 1].split(",") if b.strip()]
    args = args[:i] + args[i + 2:]
wurzel = os.path.abspath(args[0] if args else os.getcwd())
zeilen = lese_index(wurzel)
FEST = {"geprueft", "zugeordnet-auto"}


def rang(z):
    r = len(bevorzugt)
    for k, b in enumerate(bevorzugt):
        if z["pfad"] == b or z["pfad"].startswith(b + "/"):
            r = k
            break
    kopie = 1 if re.search(r"kopie|copy|\(\d+\)", os.path.splitext(z["name"])[0].lower()) else 0
    return (r, 0 if z["status"] in FEST else 1, kopie, z["geaendert"] or "9999", len(z["pfad"]), z["pfad"])


gruppen = {}
for z in zeilen:
    if z["status"] == "ausgelagert":
        continue
    if str(z["bytes"]) == "0" and z["status"] == "duplikat":   # leere Dateien nie als Duplikat werten
        z["status"], z["duplikat_von"] = "neu", ""
    if z["sha256"] and str(z["bytes"]) != "0":
        gruppen.setdefault(z["sha256"], []).append(z)

bericht, zusatz, nach_ordner = [], 0, {}
for nr, (h, g) in enumerate(sorted(gruppen.items()), 1):
    if len(g) < 2:
        for z in g:
            if z["status"] == "duplikat":
                z["status"], z["duplikat_von"] = "neu", ""
        continue
    g.sort(key=rang)
    orig = g[0]
    if orig["status"] == "duplikat":
        orig["status"] = "neu"
    orig["duplikat_von"] = ""
    for z in g[1:]:
        if z["status"] not in FEST:
            z["status"] = "duplikat"
        z["duplikat_von"] = orig["id"]
        zusatz += 1
        k = (z["pfad"].split("/")[0], orig["pfad"].split("/")[0])
        nach_ordner[k] = nach_ordner.get(k, 0) + 1
    bericht.append({"gruppe": f"G-{nr:04d}", "sha256": h[:16], "anzahl": len(g), "original_id": orig["id"],
                    "original_pfad": orig["pfad"], "kopien_ids": " ".join(z["id"] for z in g[1:]),
                    "kopien_pfade": " | ".join(z["pfad"] for z in g[1:])})

schreibe_index(wurzel, zeilen)
out = os.path.join(wurzel, "index", "duplikat_gruppen.csv")
with open(out, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=["gruppe", "sha256", "anzahl", "original_id", "original_pfad", "kopien_ids", "kopien_pfade"], delimiter=";")
    w.writeheader()
    w.writerows(bericht)
print(f"{len(bericht)} Duplikat-Gruppen, {zusatz} ueberzaehlige Kopien, {len(zeilen) - zusatz} verschiedene Dokumente")
print("Kopien nach Ordner (Kopie liegt in -> Original liegt in):")
for (a, b), n in sorted(nach_ordner.items(), key=lambda kv: -kv[1]):
    print(f"  {n:4}  {a[:38]}  ->  {b[:38]}")
print("Bericht:", out)

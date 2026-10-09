"""Prueflisten fuer unsicher datierte Dokumente (Konfidenz 'niedrig') und Einlesen der Handeintraege.
1) Liste erzeugen:   python tools/datumspruefung.py ARCHIV_WURZEL
   -> index/datum_pruefliste.csv (nur aktive Dokumente, ohne Duplikate/Ausgelagerte; Spalte 'datum_manuell' leer)
2) In Excel Spalte 'datum_manuell' ausfuellen (Format JJJJ-MM-TT), als index/datum_manuell.csv speichern (CSV, Semikolon).
3) Einlesen:         python tools/datumspruefung.py ARCHIV_WURZEL --einlesen
   -> traegt gueltige Datumswerte in Spalte 'datum' des Index ein; danach datieren.py --neu laufen lassen.
Es wird nichts an den Dokumenten geaendert. Ein Datum wird nur eingetragen, wenn du es selbst angibst."""
import csv, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from archiv_lib import *
from datetime import date as _date

args = sys.argv[1:]
rest = [a for a in args if not a.startswith("--")]
wurzel = os.path.abspath(rest[0] if rest else os.getcwd())
zeilen = lese_index(wurzel)
liste = os.path.join(wurzel, "index", "datum_pruefliste.csv")
eingabe = os.path.join(wurzel, "index", "datum_manuell.csv")

if "--einlesen" not in args:
    sel = [z for z in zeilen if z.get("dokdatum_konf") == "niedrig" and z["status"] not in ("duplikat", "ausgelagert")]
    sel.sort(key=lambda z: z["pfad"])
    with open(liste, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["id", "name", "pfad", "vorschlag_datum", "quelle_des_vorschlags", "weitere_funde_im_text", "datum_manuell"])
        for z in sel:
            w.writerow([z["id"], z["name"], z["pfad"], z.get("dokdatum", ""), z.get("dokdatum_quelle", ""), z.get("dokdatum_alt", ""), ""])
    je = {}
    for z in sel:
        je[z.get("dokdatum_quelle", "")] = je.get(z.get("dokdatum_quelle", ""), 0) + 1
    print(f"{len(sel)} unsicher datierte aktive Dokumente: " + ", ".join(f"{k}={v}" for k, v in sorted(je.items())))
    print("Pruefliste:", liste)
    print("Datum nur eintragen, wenn du es am Dokument selbst sicher erkennst. Speichern als index/datum_manuell.csv.")
    sys.exit(0)

if not os.path.exists(eingabe):
    sys.exit(f"FEHLER: {eingabe} nicht gefunden.")
roh = open(eingabe, "rb").read()
try:
    txt = roh.decode("utf-8-sig")
except UnicodeDecodeError:
    txt = roh.decode("cp1252")
nach_id = {z["id"]: z for z in zeilen}
ok, schlecht = 0, []
for r in csv.DictReader(txt.splitlines(), delimiter=";"):
    d = (r.get("datum_manuell") or "").strip()
    i = (r.get("id") or "").strip()
    if not d:
        continue
    try:
        _date.fromisoformat(d)
    except ValueError:
        schlecht.append((i, d))
        continue
    if i not in nach_id:
        schlecht.append((i, d))
        continue
    nach_id[i]["datum"] = d
    ok += 1
schreibe_index(wurzel, zeilen)
print(f"{ok} Datumswerte uebernommen, {len(schlecht)} abgelehnt (Format JJJJ-MM-TT oder unbekannte ID).")
for i, d in schlecht:
    print("  abgelehnt:", i, repr(d))
print("Jetzt datieren.py ... --neu ausfuehren.")

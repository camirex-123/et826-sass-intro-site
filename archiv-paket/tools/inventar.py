"""Erfasst alle Dateien im Archiv in index/dokumente.csv.
- Neue Dateien bekommen eine ID und einen Hash.
- Bereits erfasste Dateien bleiben unveraendert (manuelle Spalten bleiben erhalten).
- Gleicher Hash wie eine aeltere Datei => Status 'duplikat', Verweis in duplikat_von.
- Es werden keine Dateien verschoben, geloescht oder veraendert.
Aufruf:  python tools/inventar.py [ARCHIV_WURZEL]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from archiv_lib import *

wurzel = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.getcwd())
zeilen = lese_index(wurzel)
bekannt = {z["pfad"]: z for z in zeilen}
nach_hash = {}
for z in zeilen:
    if z["status"] != "duplikat":
        nach_hash.setdefault(z["sha256"], z)
naechste = max([int(z["id"][2:]) for z in zeilen if z["id"].startswith("D-")] + [0]) + 1
neu = dup = 0

for p in sorted(dateien(wurzel)):
    r = rel(wurzel, p)
    if r in bekannt:
        continue
    st = os.stat(p)
    h = sha256(p)
    z = {"id": f"D-{naechste:05d}", "pfad": r, "name": os.path.basename(p), "sha256": h,
         "bytes": st.st_size, "geaendert": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d"),
         "erfasst_am": jetzt(), "typ": "", "datum": "", "aktenzeichen": "",
         "beschreibung": "", "status": "neu", "duplikat_von": ""}
    naechste += 1
    if h in nach_hash and st.st_size > 0:
        z["status"] = "duplikat"
        z["duplikat_von"] = nach_hash[h]["id"]
        dup += 1
    elif st.st_size > 0:
        nach_hash[h] = z
    zeilen.append(z)
    bekannt[r] = z
    neu += 1

schreibe_index(wurzel, zeilen)
print(f"{neu} neu erfasst, davon {dup} Duplikate. Gesamt im Index: {len(zeilen)}")

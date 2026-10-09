"""Prueflisten fuer Dokumente, deren Text nicht oder nur schwach gelesen werden konnte (text_status leer, ocr-schwach, fehler).
Aufruf: python tools/ocrpruefung.py ARCHIV_WURZEL
-> index/ocr_pruefliste.csv (nur aktive Dokumente, ohne Duplikate/Ausgelagerte) und eine Uebersicht nach Status, Dateityp und Ordner.
'leer' bei Fotos kann normal sein (kein Text im Bild); bei Dokumenten (PDF, Scan) bitte im Original ansehen.
Das Tool aendert nichts an den Dokumenten."""
import csv, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from archiv_lib import *

rest = [a for a in sys.argv[1:] if not a.startswith("--")]
wurzel = os.path.abspath(rest[0] if rest else os.getcwd())
zeilen = lese_index(wurzel)
sel = [z for z in zeilen if z.get("text_status") in ("leer", "ocr-schwach", "fehler") and z["status"] not in ("duplikat", "ausgelagert")]
sel.sort(key=lambda z: (z["text_status"], os.path.splitext(z["name"])[1].lower(), z["pfad"]))
out = os.path.join(wurzel, "index", "ocr_pruefliste.csv")
with open(out, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f, delimiter=";")
    w.writerow(["id", "text_status", "typ", "seiten", "dokdatum", "name", "pfad", "ergebnis_pruefung"])
    for z in sel:
        w.writerow([z["id"], z["text_status"], os.path.splitext(z["name"])[1].lower().lstrip("."), z.get("seiten", ""), z.get("dokdatum", ""), z["name"], z["pfad"], ""])
print(f"{len(sel)} aktive Dokumente ohne verwertbaren Text.")
je = {}
for z in sel:
    k = (z["text_status"], os.path.splitext(z["name"])[1].lower().lstrip("."))
    je[k] = je.get(k, 0) + 1
for (st, t), n in sorted(je.items(), key=lambda kv: (kv[0][0], -kv[1])):
    print(f"  {n:4}  {st:12} {t}")
print("Prueffliste:", out)

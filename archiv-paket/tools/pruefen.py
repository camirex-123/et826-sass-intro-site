"""Prueft das Archiv. Rueckgabe 1 bei Fehlern.
FEHLER:  Datei nicht im Index / Index-Eintrag ohne Datei / Inhalt eines Originals geaendert
         / Duplikat liegt noch ausserhalb von 99_Duplikate_Quarantaene (nur Hinweis, kein Loeschen)
HINWEIS: Pflichtangaben fehlen (typ, datum, aktenzeichen), Dateiname folgt nicht dem Schema
Aufruf:  python tools/pruefen.py [ARCHIV_WURZEL]"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from archiv_lib import *

wurzel = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.getcwd())
zeilen = lese_index(wurzel)
im_index = {z["pfad"]: z for z in zeilen}
fehler, hinweise = [], []
schema = re.compile(r"^\d{4}-\d{2}-\d{2}_[^_]+_[^_]+_.+")

auf_platte = {rel(wurzel, p): p for p in dateien(wurzel)}
def abgeleitet(r):
    """Von den Tools erzeugte Ergebnisse (99_CODEX_OUTPUT) sind keine Originale: Abweichungen nur als Hinweis."""
    return "/99_CODEX_OUTPUT/" in "/" + r


for r in sorted(auf_platte):
    if r not in im_index:
        (hinweise if abgeleitet(r) else fehler).append(f"nicht im Index{' (abgeleitet)' if abgeleitet(r) else ''}: {r}")
for r, z in im_index.items():
    if r not in auf_platte and z["status"] == "ausgelagert":
        continue
    if r not in auf_platte:
        fehler.append(f"Datei fehlt: {r} ({z['id']})")
        continue
    if sha256(auf_platte[r]) != z["sha256"]:
        (hinweise if abgeleitet(r) else fehler).append(f"Inhalt veraendert{' (abgeleitet, neu erzeugt?)' if abgeleitet(r) else ''} (Hash stimmt nicht): {r} ({z['id']})")
        continue
    if z["status"] == "duplikat" and not r.startswith("99_Duplikate_Quarantaene/"):
        hinweise.append(f"Duplikat von {z['duplikat_von']} liegt noch in {r} - nach 99_Duplikate_Quarantaene verschieben (nicht loeschen)")
    if z["status"] not in ("duplikat",) and not r.startswith("00_Eingang") and not abgeleitet(r):
        if not (z["typ"] and z["datum"] and z["aktenzeichen"]):
            hinweise.append(f"Angaben unvollstaendig: {r}")
        if not schema.match(z["name"]):
            hinweise.append(f"Name ohne Schema JJJJ-MM-TT_Typ_Aktenzeichen_Titel: {r}")

bericht = os.path.join(wurzel, "index", "pruefbericht.txt")
with open(bericht, "w", encoding="utf-8") as bf:
    for f in fehler: bf.write("FEHLER  " + f + "\n")
    for h in hinweise: bf.write("HINWEIS " + h + "\n")
for f in fehler: print("FEHLER ", f)
arten = {}
for h in hinweise:
    k = h.split(":")[0]
    k = "Duplikat ausserhalb Quarantaene" if k.startswith("Duplikat von") else k
    arten[k] = arten.get(k, 0) + 1
for k, n in sorted(arten.items(), key=lambda kv: -kv[1]):
    print(f"  Hinweise {n:5}  {k}")
print("Voller Bericht:", bericht)
print(f"{len(fehler)} Fehler, {len(hinweise)} Hinweise, {len(im_index)} Dokumente im Index")
sys.exit(1 if fehler else 0)

"""Volltextsuche im gelesenen Text aller Dokumente (index/text/*.txt, aus ocr.py). Alles lokal, nur Anzeige am Bildschirm.
Jede Fundstelle nennt Dokument (ID, DOC-ID falls vorhanden), Seite, Dateiname, Dokumentdatum und ein Textstueck zum Belegen.
Duplikate und ausgelagerte Dokumente erscheinen nicht. OCR-Fehler sind moeglich: Funde im Original gegenpruefen.
Aufruf:
  python tools/suche.py ARCHIV_WURZEL "23.03.2022"                      (Text; Gross/Klein egal)
  python tools/suche.py ARCHIV_WURZEL "23\\.03\\.(20)?22" --regex        (regulaerer Ausdruck)
  Optionen: --max 40 (Anzahl Dokumente)  --kontext 70 (Zeichen links/rechts)  --stellen 2 (Fundstellen je Dokument)"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from archiv_lib import *


def opt(args, name, default):
    return type(default)(args[args.index(name) + 1]) if name in args else default


args = sys.argv[1:]
feste = ("--max", "--kontext", "--stellen")
pos = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or args[i - 1] not in feste)]
if len(pos) < 2:
    sys.exit('FEHLER: Aufruf: suche.py ARCHIV_WURZEL "Suchbegriff" [--regex]')
wurzel, begriff = os.path.abspath(pos[0]), pos[1]
muster = re.compile(begriff if "--regex" in args else re.escape(begriff), re.I)
maxd, ktx, stellen = opt(args, "--max", 40), opt(args, "--kontext", 70), opt(args, "--stellen", 2)
zeilen = {z["id"]: z for z in lese_index(wurzel)}
ordner = os.path.join(wurzel, "index", "text")
if not os.path.isdir(ordner):
    sys.exit("FEHLER: index/text nicht gefunden. Zuerst ocr.py ausfuehren.")
treffer = []
for n in os.listdir(ordner):
    z = zeilen.get(n[:-4])
    if not n.endswith(".txt") or not z or z["status"] in ("duplikat", "ausgelagert"):
        continue
    text = lies_sidecar(os.path.join(ordner, n))
    ms = list(muster.finditer(text))
    if not ms:
        continue
    seiten = [(m.start(), int(m[1])) for m in re.finditer(r"=== Seite (\d+) ===", text)]
    funde = []
    for m in ms[:stellen]:
        s = max([p for st, p in seiten if st <= m.start()] or [1])
        ausschnitt = re.sub(r"\s+", " ", text[max(0, m.start() - ktx):m.end() + ktx])
        funde.append((s, ausschnitt))
    treffer.append((len(ms), z, funde))
treffer.sort(key=lambda t: (-t[0], t[1]["dokdatum"] or "9999"))
print(f"{len(treffer)} Dokumente mit Treffer fuer '{begriff}' (angezeigt: {min(len(treffer), maxd)})")
for anz, z, funde in treffer[:maxd]:
    kennung = z.get("doc_id") or z["id"]
    print(f"\n{kennung}  [{z['id']}]  {anz}x  Datum {z.get('dokdatum') or '?'} ({z.get('dokdatum_konf') or '?'})  {z['name'][:90]}")
    for s, a in funde:
        print(f"   S. {s}: ...{a}...")

"""Datumsindex auf SEITENEBENE: jedes Datum, das im gelesenen Text vorkommt, mit Dokument, Seite und Textstueck.
Gedacht fuer mehrseitige Akten (Baende), in denen die Dokument-Chronologie nur ein Datum je Datei zeigt.
WICHTIG: Ein Datum im Text ist eine ERWAEHNUNG, kein Beleg fuer ein Ereignis (es kann ein Termin, eine Frist, ein Zitat oder ein
OCR-Fehler sein). Geburtsdaten ('geb.', 'geboren') werden ausgelassen. Aus der Haeufigkeit folgt nichts. Bitte im Original pruefen.
Ergebnis in <ZIEL> (z. B. 99_CODEX_OUTPUT/03_CHRONOLOGIEN):
  JJJJ-MM-TT_CHR-AUTO_ARCHIVTOOLS_Datumsfundstellen.csv  (Datum; Dokument-ID; Seite; Anzahl; Dateiname; Kontext)
Aufruf:
  python tools/datumsindex.py ARCHIV_WURZEL --ziel "KANZLEI_CODEX_CASE_TEMPLATE/99_CODEX_OUTPUT/03_CHRONOLOGIEN"
         [--von 2018-01-01] [--bis 2026-12-31] [--kontext 70] [--ausschliessen "KANZLEI_CODEX_CASE_TEMPLATE/07_RECHTSFRAGEN/14_LITERATUR"]"""
import csv, os, re, sys
from datetime import date
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from archiv_lib import *
from datieren import funde


def opt(args, name, default=None):
    return args[args.index(name) + 1] if name in args else default


args = sys.argv[1:]
ziel = (opt(args, "--ziel") or "").replace("\\", "/").strip("/")
if not ziel:
    sys.exit('FEHLER: --ziel fehlt, z. B. --ziel "KANZLEI_CODEX_CASE_TEMPLATE/99_CODEX_OUTPUT/03_CHRONOLOGIEN"')
von, bis = date.fromisoformat(opt(args, "--von", "2018-01-01")), date.fromisoformat(opt(args, "--bis", "2026-12-31"))
ktx = int(opt(args, "--kontext", 70))
aus = [a.strip().replace("\\", "/").strip("/") for a in (opt(args, "--ausschliessen") or "").split(",") if a.strip()]
feste = ("--ziel", "--von", "--bis", "--kontext", "--ausschliessen")
rest = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or args[i - 1] not in feste)]
wurzel = os.path.abspath(rest[0] if rest else os.getcwd())
zeilen = {z["id"]: z for z in lese_index(wurzel)}
ordner = os.path.join(wurzel, "index", "text")
if not os.path.isdir(ordner):
    sys.exit("FEHLER: index/text nicht gefunden. Zuerst ocr.py ausfuehren.")

zeilen_out, je_jahr = [], {}
for n in sorted(os.listdir(ordner)):
    z = zeilen.get(n[:-4])
    if not n.endswith(".txt") or not z or z["status"] in ("duplikat", "ausgelagert"):
        continue
    p = z["pfad"].replace("\\", "/")
    if any(p == a or p.startswith(a + "/") for a in aus) or os.path.splitext(p)[1].lower() in (".md", ".csv", ".ps1", ".py", ".svg"):
        continue
    text = lies_sidecar(os.path.join(ordner, n))
    marken = [(m.start(), int(m[1])) for m in re.finditer(r"=== Seite (\d+) ===", text)]
    je_seite = {}
    for pos, d in funde(text):
        if not (von <= d <= bis):
            continue
        seite = max([s for st, s in marken if st <= pos] or [1])
        schluessel = (d, seite)
        if schluessel in je_seite:
            je_seite[schluessel][0] += 1
            continue
        k = re.sub(r"\s+", " ", text[max(0, pos - ktx):pos + ktx + 10])
        je_seite[schluessel] = [1, k]
    for (d, seite), (anz, k) in je_seite.items():
        zeilen_out.append((d.isoformat(), z.get("doc_id") or z["id"], z["id"], seite, anz, z["name"], k))
        je_jahr[d.year] = je_jahr.get(d.year, 0) + 1
zeilen_out.sort(key=lambda r: (r[0], r[1], r[3]))
os.makedirs(os.path.join(wurzel, *ziel.split("/")), exist_ok=True)
out = os.path.join(wurzel, *ziel.split("/"), f"{date.today().isoformat()}_CHR-AUTO_ARCHIVTOOLS_Datumsfundstellen.csv")
with open(out, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f, delimiter=";")
    w.writerow(["datum", "doc_id", "id", "seite", "anzahl_auf_seite", "dateiname", "kontext"])
    w.writerows(zeilen_out)
print(f"{len(zeilen_out)} Fundstellen (Datum + Dokument + Seite) aus {len({r[2] for r in zeilen_out})} Dokumenten")
print("Fundstellen je Jahr:", ", ".join(f"{j}: {c}" for j, c in sorted(je_jahr.items())))
print("Datei:", out)
print("Hinweis: Datumserwaehnungen sind keine Belege fuer Ereignisse; im Original pruefen.")

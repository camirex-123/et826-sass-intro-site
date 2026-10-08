"""Gleicht den Index mit dem Kanzlei-Manifest (DATEIMANIFEST.csv, IDs DOC-0001) ab. Das Manifest wird NIE veraendert.
- Dokumente, deren SHA-256 im Manifest steht, uebernehmen dessen DOC-ID (Spalte doc_id, doc_status = manifest).
- Neue Dokumente bekommen einen VORSCHLAG fuer die naechste freie DOC-ID (doc_status = neu-vorschlag), fortlaufend nach dem
  hoechsten vorhandenen Wert. Die Vorschlaege stehen in <AUSGABE>/DATEIMANIFEST_ergaenzung_auto.csv zum Pruefen und
  Uebernehmen durch dich bzw. die Kanzlei. Duplikate erhalten die ID ihres Originals.
- Die Spalten des Manifests werden erkannt (Trennzeichen, SHA-Spalte, ID-Spalte). Das Ergebnis der Erkennung wird angezeigt.
Aufruf:
  python tools/manifest.py ARCHIV_WURZEL --manifest "KANZLEI_CODEX_CASE_TEMPLATE/00_MASTER/DATEIMANIFEST.csv"
                                         --ausgabe "KANZLEI_CODEX_CASE_TEMPLATE/99_CODEX_OUTPUT/ARCHIV_AUTO"
                                         [--ausschliessen "KANZLEI_CODEX_CASE_TEMPLATE"] [--ohne-typen md,csv,ps1,py,svg]
--ausschliessen: Dateien unter diesen Ordnern bekommen KEINEN neuen Vorschlag (Treffer im Manifest werden trotzdem uebernommen),
  z. B. das Template mit seinen Arbeitsdateien. --ohne-typen: dasselbe fuer Dateitypen. """
import csv, io, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from archiv_lib import *


def opt(args, name):
    return args[args.index(name) + 1] if name in args else None


def lies_text(pfad):
    roh = open(pfad, "rb").read()
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return roh.decode(enc)
        except UnicodeDecodeError:
            continue


def lade_manifest(pfad):
    text = lies_text(pfad)
    kopf = text.splitlines()[0] if text.strip() else ""
    delim = max(";,\t|", key=kopf.count)
    zeilen = list(csv.reader(io.StringIO(text), delimiter=delim))
    kopf, daten = zeilen[0], zeilen[1:]
    low = [k.strip().lower() for k in kopf]
    hex64 = re.compile(r"^[0-9a-fA-F]{64}$")
    doc = re.compile(r"^DOC-\d+$", re.I)

    def spalte(pred, prufen):
        for i, k in enumerate(low):
            if pred(k):
                return i
        best, bi = 0, None
        for i in range(len(kopf)):
            n = sum(1 for r in daten if i < len(r) and prufen.match(r[i].strip()))
            if n > best:
                best, bi = n, i
        return bi if best >= max(1, len(daten) // 2) else None
    i_sha = spalte(lambda k: "sha" in k, hex64)
    i_id = spalte(lambda k: k in ("doc_id", "docid", "doc-id", "doc", "id", "dok_id", "dokument_id"), doc)
    if i_sha is None or i_id is None:
        sys.exit(f"FEHLER: Spalten nicht erkannt (SHA: {i_sha}, ID: {i_id}). Kopfzeile: {kopf}")
    print(f"Manifest: {len(daten)} Zeilen, Trennzeichen '{delim}', ID-Spalte '{kopf[i_id]}', SHA-Spalte '{kopf[i_sha]}'")
    sha2doc, ids = {}, []
    for r in daten:
        if len(r) > max(i_sha, i_id) and hex64.match(r[i_sha].strip()) and doc.match(r[i_id].strip()):
            sha2doc.setdefault(r[i_sha].strip().lower(), r[i_id].strip().upper())
            ids.append(r[i_id].strip().upper())
    return sha2doc, ids


args = sys.argv[1:]
mf, ausgabe = opt(args, "--manifest"), opt(args, "--ausgabe")
if not mf or not ausgabe:
    sys.exit('FEHLER: --manifest und --ausgabe angeben')
aus = [a.strip().replace("\\", "/").strip("/") for a in (opt(args, "--ausschliessen") or "").split(",") if a.strip()]
ohne = {"." + t.strip().lower().lstrip(".") for t in (opt(args, "--ohne-typen") or "").split(",") if t.strip()}
rest = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or args[i - 1] not in ("--manifest", "--ausgabe", "--ausschliessen", "--ohne-typen"))]
wurzel = os.path.abspath(rest[0] if rest else os.getcwd())
mpfad = os.path.join(wurzel, *mf.replace("\\", "/").split("/"))
if not os.path.exists(mpfad):
    sys.exit(f"FEHLER: Manifest nicht gefunden: {mpfad}")
sha2doc, ids = lade_manifest(mpfad)
zeilen = lese_index(wurzel)
zahlen = [int(i[4:]) for i in ids] + [int(z["doc_id"][4:]) for z in zeilen if re.match(r"^DOC-\d+$", z.get("doc_id", ""))]
naechste = (max(zahlen) if zahlen else 0) + 1
breite = max([len(i) - 4 for i in ids] + [4])
by_id = {z["id"]: z for z in zeilen}

for z in zeilen:                                   # 1. Treffer im Manifest
    if not z.get("doc_id") and z["sha256"].lower() in sha2doc:
        z["doc_id"], z["doc_status"] = sha2doc[z["sha256"].lower()], "manifest"
neu = []
def ausgenommen(z):
    p = z["pfad"]
    return any(p == a or p.startswith(a + "/") for a in aus) or os.path.splitext(p)[1].lower() in ohne


kandidaten = sorted((z for z in zeilen if not z.get("doc_id") and z["status"] not in ("duplikat", "ausgelagert") and not ausgenommen(z)),
                    key=lambda z: (z.get("dokdatum") or "9999", z["pfad"]))
for z in kandidaten:                                # 2. Vorschlaege fuer Neues (stabil, einmal vergeben)
    z["doc_id"], z["doc_status"] = f"DOC-{naechste:0{breite}d}", "neu-vorschlag"
    naechste += 1
    neu.append(z)
for z in zeilen:                                   # 3. Duplikate erben die ID des Originals
    if z["status"] == "duplikat" and not z.get("doc_id") and z["duplikat_von"] in by_id and by_id[z["duplikat_von"]].get("doc_id"):
        o = by_id[z["duplikat_von"]]
        z["doc_id"], z["doc_status"] = o["doc_id"], o["doc_status"]
schreibe_index(wurzel, zeilen)

os.makedirs(os.path.join(wurzel, *ausgabe.replace("\\", "/").split("/")), exist_ok=True)
out = os.path.join(wurzel, *ausgabe.replace("\\", "/").split("/"), "DATEIMANIFEST_ergaenzung_auto.csv")
vorhanden = {z["doc_id"] for z in zeilen if z.get("doc_status") == "neu-vorschlag"}
with open(out, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f, delimiter=";")
    w.writerow(["doc_id", "sha256", "dateiname", "pfad", "bytes", "dokumentdatum", "datum_sicherheit", "datum_quelle", "hinweis"])
    for z in sorted((z for z in zeilen if z.get("doc_status") == "neu-vorschlag" and z["status"] != "duplikat"), key=lambda z: z["doc_id"]):
        w.writerow([z["doc_id"], z["sha256"], z["name"], z["pfad"], z["bytes"], z.get("dokdatum", ""),
                    z.get("dokdatum_konf", ""), z.get("dokdatum_quelle", ""), "VORSCHLAG - nicht im Manifest, bitte pruefen"])
im = sum(1 for z in zeilen if z.get("doc_status") == "manifest")
print(f"{im} Index-Eintraege mit ID aus dem Manifest, {len(neu)} neue Vorschlaege" + (f" (DOC-{naechste - len(neu):0{breite}d} bis DOC-{naechste - 1:0{breite}d})" if neu else ""))
print(f"{sum(1 for z in zeilen if not z.get('doc_id') and z['status'] not in ('duplikat', 'ausgelagert'))} Eintraege ohne ID (ausgeschlossene Ordner/Typen, z. B. Arbeitsdateien des Templates).")
manifest_shas = set(sha2doc)
fehlt = len(manifest_shas - {z["sha256"].lower() for z in zeilen})
print(f"{fehlt} Manifest-Eintraege haben keine passende Datei im Archiv-Index (anderer Inhalt oder anderer Ort).")
print("Vorschlagsliste:", out)

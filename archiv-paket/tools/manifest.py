"""Erzeugt Vorschlaege fuer DATEIMANIFEST.csv (IDs DOC-0001, SHA-256 je Original). Das Manifest selbst wird NIE veraendert.
Das Manifest fuehrt nur ORIGINALE aus 01_ORIGINALE. Darum wertet dieses Werkzeug die Dateien unter --originale aus
(nach uebernehmen.py --anwenden und inventar.py):
- SHA-256 steht schon im Manifest        -> deren Datei_ID wird uebernommen (Spalte doc_id, doc_status = manifest)
- sonst                                   -> Vorschlag fuer die naechste freie ID (doc_status = neu-vorschlag), fortlaufend nach
                                             dem hoechsten vorhandenen Wert, stabil bei Wiederholung
- Duplikate/Arbeitskopien erben die ID ihres Originals.
Die Vorschlagsdatei hat GENAU die Spalten des Manifests und liegt in --ausgabe (z. B. 99_CODEX_OUTPUT/05_ENTWUERFE), damit die Kanzlei
sie pruefen und uebernehmen kann.
Aufruf:
  python tools/manifest.py ARCHIV_WURZEL --manifest "KANZLEI_CODEX_CASE_TEMPLATE/00_MASTER/DATEIMANIFEST.csv"
        --originale "KANZLEI_CODEX_CASE_TEMPLATE/01_ORIGINALE" --ausgabe "KANZLEI_CODEX_CASE_TEMPLATE/99_CODEX_OUTPUT/05_ENTWUERFE"
        [--basis "KANZLEI_CODEX_CASE_TEMPLATE"] [--ohne-typen md,csv,ps1,py,svg]
--basis: Ordner, zu dem 'Relativer_Pfad' gerechnet wird (Standard: Elternordner von --originale, also z. B. 01_ORIGINALE/GERICHT/...)."""
import csv, io, os, re, sys
from datetime import date
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from archiv_lib import *

IDNAMEN = ("doc_id", "docid", "doc-id", "doc", "id", "dok_id", "dokument_id", "datei_id", "dateiid")


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
    kopf_zeile = text.splitlines()[0] if text.strip() else ""
    delim = max(";,\t|", key=kopf_zeile.count)
    zeilen = list(csv.reader(io.StringIO(text), delimiter=delim))
    kopf, daten = [k.strip() for k in zeilen[0]], [r for r in zeilen[1:] if any(c.strip() for c in r)]
    low = [k.lower() for k in kopf]
    hex64, doc = re.compile(r"^[0-9a-fA-F]{64}$"), re.compile(r"^DOC-\d+$", re.I)

    def spalte(pred, pruef):
        for i, k in enumerate(low):
            if pred(k):
                return i
        best, bi = 0, None
        for i in range(len(kopf)):
            n = sum(1 for r in daten if i < len(r) and pruef.match(r[i].strip()))
            if n > best:
                best, bi = n, i
        return bi if best >= max(1, len(daten) // 2) else None
    i_sha = spalte(lambda k: "sha" in k, hex64)
    i_id = spalte(lambda k: k in IDNAMEN, doc)
    if i_sha is None or i_id is None:
        sys.exit(f"FEHLER: Spalten nicht erkannt (SHA: {i_sha}, ID: {i_id}). Kopfzeile: {kopf}")
    print(f"Manifest: {len(daten)} Datenzeilen, Trennzeichen '{delim}', ID-Spalte '{kopf[i_id]}', SHA-Spalte '{kopf[i_sha]}'")
    sha2doc, ids = {}, []
    for r in daten:
        if len(r) > max(i_sha, i_id) and hex64.match(r[i_sha].strip()) and doc.match(r[i_id].strip()):
            sha2doc.setdefault(r[i_sha].strip().lower(), r[i_id].strip().upper())
            ids.append(r[i_id].strip().upper())
    return kopf, delim, sha2doc, ids


args = sys.argv[1:]
mf, ausgabe, originale = opt(args, "--manifest"), opt(args, "--ausgabe"), opt(args, "--originale")
if not (mf and ausgabe and originale):
    sys.exit("FEHLER: --manifest, --originale und --ausgabe angeben")
norm = lambda s: s.replace("\\", "/").strip("/")
originale = norm(originale)
basis = norm(opt(args, "--basis") or os.path.dirname(originale))
ohne = {"." + t.strip().lower().lstrip(".") for t in (opt(args, "--ohne-typen") or "").split(",") if t.strip()}
feste = ("--manifest", "--ausgabe", "--originale", "--basis", "--ohne-typen")
rest = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or args[i - 1] not in feste)]
wurzel = os.path.abspath(rest[0] if rest else os.getcwd())
mpfad = os.path.join(wurzel, *norm(mf).split("/"))
if not os.path.exists(mpfad):
    sys.exit(f"FEHLER: Manifest nicht gefunden: {mpfad}")
kopf, delim, sha2doc, ids = lade_manifest(mpfad)
zeilen = lese_index(wurzel)
zahlen = [int(i[4:]) for i in ids] + [int(z["doc_id"][4:]) for z in zeilen if re.match(r"^DOC-\d+$", z.get("doc_id", ""))]
naechste = (max(zahlen) if zahlen else 0) + 1
breite = max([len(i) - 4 for i in ids] + [4])
by_id = {z["id"]: z for z in zeilen}

for z in zeilen:                                   # 1. Treffer im Manifest (alle Dateien, gleicher Inhalt = gleiche ID)
    if not z.get("doc_id") and z["sha256"].lower() in sha2doc:
        z["doc_id"], z["doc_status"] = sha2doc[z["sha256"].lower()], "manifest"


def kandidat(z):
    p = z["pfad"].replace("\\", "/")
    return (p.startswith(originale + "/") and z["status"] not in ("duplikat", "ausgelagert")
            and os.path.splitext(p)[1].lower() not in ohne)


neu = []
for z in sorted((z for z in zeilen if kandidat(z) and not z.get("doc_id")), key=lambda z: z["pfad"]):
    z["doc_id"], z["doc_status"] = f"DOC-{naechste:0{breite}d}", "neu-vorschlag"
    naechste += 1
    neu.append(z)
for z in zeilen:                                   # Duplikate/Arbeitskopien erben die ID ihres Originals
    if z["status"] == "duplikat" and not z.get("doc_id") and z["duplikat_von"] in by_id and by_id[z["duplikat_von"]].get("doc_id"):
        o = by_id[z["duplikat_von"]]
        z["doc_id"], z["doc_status"] = o["doc_id"], o["doc_status"]
schreibe_index(wurzel, zeilen)

zielordner = os.path.join(wurzel, *norm(ausgabe).split("/"))
os.makedirs(zielordner, exist_ok=True)
out = os.path.join(zielordner, "DATEIMANIFEST_ergaenzung_auto.csv")
heute = date.today().isoformat()


def feld(name, z):
    n = name.lower()
    p = z["pfad"].replace("\\", "/")
    rel_basis = p[len(basis) + 1:] if basis and p.startswith(basis + "/") else p
    if n in IDNAMEN:
        return z["doc_id"]
    return {"relativer_pfad": rel_basis, "dateiname": z["name"], "dateityp": os.path.splitext(z["name"])[1].lstrip(".").lower(),
            "groesse_bytes": z["bytes"], "aenderungsdatum_dateisystem": z["geaendert"], "sha256": z["sha256"],
            "original_arbeitskopie": "Original", "importdatum": heute,
            "notiz": f"VORSCHLAG Archiv-Tools; Dokumentdatum {z.get('dokdatum', '') or 'unbekannt'} "
                     f"({z.get('dokdatum_quelle', '')}, {z.get('dokdatum_konf', '')}); nicht im Manifest, bitte pruefen"}.get(n, "")


with open(out, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f, delimiter=delim)
    w.writerow(kopf)
    for z in sorted(neu, key=lambda z: z["doc_id"]):
        w.writerow([feld(k, z) for k in kopf])
im = sum(1 for z in zeilen if z.get("doc_status") == "manifest")
print(f"{im} Index-Eintraege mit Datei_ID aus dem Manifest, {len(neu)} neue Vorschlaege"
      + (f" (DOC-{naechste - len(neu):0{breite}d} bis DOC-{naechste - 1:0{breite}d})" if neu else ""))
print(f"{len(set(sha2doc) - {z['sha256'].lower() for z in zeilen})} Manifest-Eintraege haben keine passende Datei im Archiv-Index.")
print("Vorschlagsliste:", out)

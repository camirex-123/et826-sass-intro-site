"""Baut ein sauberes Archiv durch KOPIEREN (nie Verschieben, nie Loeschen, nie Ueberschreiben).
- Pro Dokument (Hash) wird nur das gewaehlte Original uebernommen, Duplikate nicht (zuerst duplikate.py ausfuehren).
- Ordner wie im Kanzlei-Template (01_ORIGINALE): BEHOERDEN, EMAILS, FOTOS, GERICHT (AG_Schoeneberg/89_F_xx-22, Kammergericht),
  GUTACHTEN, MEDIZIN, SCHULE, SONSTIGE, VIDEOS, AUDIO. Unklare Dokumente kommen nach SONSTIGE/_UNGEKLAERT
  (nichts geht verloren, aber sichtbar zur Pruefung). Quellen bleiben unveraendert.
- Bereits im Ziel vorhandene Inhalte (gleicher Hash) werden uebersprungen.
- Originale behalten IMMER ihren urspruenglichen Dateinamen (Regel des Templates). Das Dokumentdatum steht im Index und in der
  Chronologie. Nur mit --datumspraefix wird JJJJ-MM-TT_ vorangestellt (nicht empfohlen).
- Standard = nur PLAN (index/uebernahme_plan.csv). Kopiert wird erst mit --anwenden.
Aufruf:
  python tools/uebernehmen.py ARCHIV_WURZEL --ziel "KANZLEI_CODEX_CASE_TEMPLATE/01_ORIGINALE"
       [--ausschliessen "KANZLEI_CODEX_CASE_TEMPLATE,index"] [--ohne-typen md,csv,ps1,py,svg] [--anwenden] [--datumspraefix]
Handzuordnung: Beim Plan entsteht index/zuordnung_manuell_VORLAGE.csv mit allen unklaren Dateien (Spalte 'ordner' leer). In Excel
ausfuellen (z. B. GERICHT/AG_Schoeneberg, MEDIZIN, SCHULE), als index/zuordnung_manuell.csv speichern (CSV, Trennzeichen Semikolon).
Beim naechsten Lauf gilt dieser Ordner statt der automatischen Zuordnung. Eintrag '-' = nicht kopieren (eigene Entwuerfe, abgeleitete
Auszuege: sie gehoeren laut Template nicht nach 01_ORIGINALE).
Vorher: inventar.py, duplikate.py, ocr.py (damit der Inhalt in die Zuordnung eingeht)."""
import csv, os, re, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from archiv_lib import *
from sortieren import bewerten, entscheide, text_anfang

# Zuordnung der Kategorien zu den Ordnernamen des Templates (README_CODEX.md, 01_ORIGINALE)
LABEL = {"01_Verfahren": "GERICHT", "02_Behoerden": "BEHOERDEN", "03_Medizin_Gutachten": "MEDIZIN",
         "04_Korrespondenz": "EMAILS", "05_Beweise": "FOTOS", "06_Eigene_Texte": "SONSTIGE/EIGENE_ENTWUERFE",
         "07_Schule_Kita": "SCHULE", "08_Polizei": "BEHOERDEN/POLIZEI", "09_Vollmachten": "SONSTIGE/VOLLMACHTEN"}
VIDEO = {".mp4", ".mov", ".avi", ".mkv", ".m4v", ".3gp", ".wmv", ".webm"}
AUDIO = {".mp3", ".m4a", ".wav", ".opus", ".ogg", ".aac"}


def az_ordner(az):
    """'89 F 36/22' -> '89_F_36-22' (Schema des Templates)."""
    return re.sub(r"[^A-Za-z0-9_-]+", "", re.sub(r"\s+", "_", az.strip()).replace("/", "-")) or "ohne-az"


def ziel_unterordner(kat, az, name, text, ext):
    if kat == "03_Medizin_Gutachten" and ("gutachten" in name or "sachverst" in name or "gutachten" in text[:1500]):
        return "GUTACHTEN"
    if kat == "05_Beweise":
        return "VIDEOS" if ext in VIDEO else "AUDIO" if ext in AUDIO else "FOTOS"
    if kat == "01_Verfahren":
        t = (name + " " + text[:4000]).lower()
        stufe = "Kammergericht" if "kammergericht" in t else "AG_Schoeneberg" if ("sch\u00f6neberg" in t or "schoeneberg" in t or az.startswith("89")) else ""
        teile = ["GERICHT"] + ([stufe] if stufe else []) + ([az_ordner(az)] if az else [])
        return "/".join(teile)
    return LABEL.get(kat, kat)


def opt(args, name, default=""):
    return args[args.index(name) + 1] if name in args else default


args = sys.argv[1:]
anwenden = "--anwenden" in args
datumspraefix = "--datumspraefix" in args
ziel = opt(args, "--ziel").replace("\\", "/").strip("/")
if not ziel:
    sys.exit("FEHLER: --ziel fehlt, z. B. --ziel \"KANZLEI_CODEX_CASE_TEMPLATE/01_ORIGINALE\"")
ausgeschlossen = [a.strip().replace("\\", "/").strip("/") for a in opt(args, "--ausschliessen").split(",") if a.strip()]
ohne = {"." + t.strip().lower().lstrip(".") for t in opt(args, "--ohne-typen").split(",") if t.strip()}
rest = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or args[i - 1] not in ("--ziel", "--ausschliessen", "--ohne-typen"))]
wurzel = os.path.abspath(rest[0] if rest else os.getcwd())
zeilen = lese_index(wurzel)

manuell = {}
mp = os.path.join(wurzel, "index", "zuordnung_manuell.csv")
if os.path.exists(mp):
    roh = open(mp, "rb").read()
    try:
        txt = roh.decode("utf-8-sig")
    except UnicodeDecodeError:
        txt = roh.decode("cp1252")
    for r in csv.DictReader(txt.splitlines(), delimiter=";"):
        o = (r.get("ordner") or "").strip().replace("\\", "/").strip("/")
        if o and r.get("id"):
            manuell[r["id"].strip()] = o
    print(f"Handzuordnung: {len(manuell)} Eintraege aus index/zuordnung_manuell.csv")

im_ziel = {z["sha256"] for z in zeilen if z["pfad"].startswith(ziel + "/")}
plan, belegt = [], set()
for z in zeilen:
    p = z["pfad"]
    if z["status"] in ("duplikat", "ausgelagert") or p.startswith(ziel + "/"):
        continue
    if any(p == a or p.startswith(a + "/") for a in ausgeschlossen):
        continue
    if os.path.splitext(p)[1].lower() in ohne:
        continue
    if z["sha256"] in im_ziel:
        plan.append({"id": z["id"], "quelle": p, "ziel": "", "kategorie": "", "konfidenz": "", "aktion": "schon im Ziel vorhanden"})
        continue
    quelle = os.path.join(wurzel, p)
    if not os.path.exists(quelle):
        continue
    punkte, gruende, az = bewerten(quelle, text_pfad(wurzel, z["id"]))
    kat, konf = entscheide(punkte)
    if z["id"] in manuell:
        unter = manuell[z["id"]]
    elif konf == "niedrig" or not kat:
        unter = "SONSTIGE/_UNGEKLAERT"
    else:
        txt = text_anfang(quelle, text_pfad(wurzel, z["id"])).lower()
        unter = ziel_unterordner(kat, az, z["name"].lower(), txt, os.path.splitext(p)[1].lower())
    if unter == "-" or unter.upper() == "NICHT" or unter == "SONSTIGE/EIGENE_ENTWUERFE":
        plan.append({"id": z["id"], "quelle": p, "ziel": "", "kategorie": "nicht kopiert", "konfidenz": konf or "",
                     "aktion": "nicht in Originale (Entwurf/abgeleitet)"})
        continue
    dd = z.get("dokdatum", "")
    pre = (dd if dd and z.get("dokdatum_konf") in ("hoch", "mittel") else "0000-00-00") + "_"
    kname = z["name"] if (not datumspraefix or re.match(r"^\d{4}-\d{2}-\d{2}_", z["name"])) else pre + z["name"]
    zd = f"{ziel}/{unter}/{kname}"
    i = 1
    while zd in belegt or os.path.exists(os.path.join(wurzel, zd)):
        b, e = os.path.splitext(kname)
        zd = f"{ziel}/{unter}/{b}__{i}{e}"
        i += 1
    belegt.add(zd)
    plan.append({"id": z["id"], "quelle": p, "ziel": zd, "kategorie": unter, "konfidenz": konf or "niedrig",
                 "aktion": "kopieren"})

offen = [r for r in plan if r["kategorie"] == "SONSTIGE/_UNGEKLAERT"]
if offen:
    nach_id = {z["id"]: z for z in zeilen}
    vl = os.path.join(wurzel, "index", "zuordnung_manuell_VORLAGE.csv")
    with open(vl, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["id", "dateiname", "dokumentdatum", "quelle", "ordner"])
        for r in offen:
            z = nach_id[r["id"]]
            w.writerow([r["id"], z["name"], z.get("dokdatum", ""), r["quelle"], ""])
out = os.path.join(wurzel, "index", "uebernahme_plan.csv")
os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=["id", "quelle", "ziel", "kategorie", "konfidenz", "aktion"], delimiter=";")
    w.writeheader()
    w.writerows(plan)

zaehl = {}
for r in plan:
    if r["aktion"] == "kopieren":
        k = "/".join(r["kategorie"].split("/")[:2])      # bis zu zwei Ebenen, z. B. SONSTIGE/_UNGEKLAERT
        zaehl[k] = zaehl.get(k, 0) + 1
schon = sum(1 for r in plan if r["aktion"] == "schon im Ziel vorhanden")
entw = sum(1 for r in plan if r["aktion"].startswith("nicht in Originale"))
print(f"Plan: {sum(zaehl.values())} Dateien kopieren, {schon} schon im Ziel, {entw} als Entwurf/abgeleitet nicht kopiert")
for k, n in sorted(zaehl.items(), key=lambda kv: -kv[1]):
    print(f"  {n:4}  {k}")
print("Plan-Datei:", out)
if offen:
    print(f"{len(offen)} Dateien sind unklar. Zum Selbstzuordnen: index/zuordnung_manuell_VORLAGE.csv (Anleitung im Kopf von uebernehmen.py).")
if not anwenden:
    print("Nichts kopiert. Mit --anwenden ausfuehren, wenn der Plan passt.")
    sys.exit(0)

fehler = 0
by_id = {z["id"]: z for z in zeilen}
for r in plan:
    if r["aktion"] != "kopieren":
        continue
    q, zp = os.path.join(wurzel, r["quelle"]), os.path.join(wurzel, r["ziel"])
    os.makedirs(os.path.dirname(zp), exist_ok=True)
    shutil.copy2(q, zp)
    if sha256(zp) != by_id[r["id"]]["sha256"]:
        print("FEHLER Pruefsumme stimmt nicht:", r["ziel"])
        fehler += 1
        continue
    by_id[r["id"]]["beschreibung"] = (by_id[r["id"]]["beschreibung"] + " | " if by_id[r["id"]]["beschreibung"] else "") + "kopiert nach: " + r["ziel"]
schreibe_index(wurzel, zeilen)
print(f"Fertig. {fehler} Fehler. Neue Dateien bitte mit inventar.py erfassen.")
sys.exit(1 if fehler else 0)

"""Prueflisten fuer unsicher datierte Dokumente (Konfidenz 'niedrig') und Einlesen der Handeintraege.
1) Liste erzeugen:   python tools/datumspruefung.py ARCHIV_WURZEL [--ausschliessen "A,B"] [--ohne-typen md,csv,ps1,py,svg]
                     (Standard fuer --ohne-typen wie bei chronologie.py; --ausschliessen blendet Ordner aus)
   -> index/datum_pruefliste.csv (nur aktive Dokumente, ohne Duplikate/Ausgelagerte; Spalte 'datum_manuell' leer)
   Kopien zum Sortieren: python tools/datumspruefung.py ARCHIV_WURZEL --kopieren ZIELORDNER [--ausschliessen ...]
     -> KOPIERT (nichts wird verschoben) alle Dokumente der Liste, deren Datum nur aus Dateiaenderung oder Datei-Metadaten stammt,
        nach ZIELORDNER (am besten ausserhalb des Archivs), als '<ID>_<Name>', mit Pruefsummenkontrolle und _LISTE.csv.
   Schnell am Bildschirm: python tools/datumspruefung.py ARCHIV_WURZEL --interaktiv PRUEFORDNER [--ausschliessen ...]
     -> oeffnet jedes Dokument aus dem Pruefordner nacheinander, fragt nach dem Datum (TT.MM.JJJJ oder JJJJ-MM-TT; Enter = leer lassen,
        s = ueberspringen, q = beenden) und traegt es sofort in den Index ein (Spalte 'datum', Quelle 'manuell'). Protokoll: index/datum_eingaben_log.csv.
2) In Excel Spalte 'datum_manuell' ausfuellen (Format JJJJ-MM-TT oder TT.MM.JJJJ), als index/datum_manuell.csv speichern (CSV, Semikolon).
3) Einlesen:         python tools/datumspruefung.py ARCHIV_WURZEL --einlesen
   -> traegt gueltige Datumswerte in Spalte 'datum' des Index ein; danach datieren.py --neu laufen lassen.
Es wird nichts an den Dokumenten geaendert. Ein Datum wird nur eingetragen, wenn du es selbst angibst."""
import csv, os, re, shutil, sys
from datetime import datetime as _dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from archiv_lib import *
from datetime import date as _date

args = sys.argv[1:]
def opt(name, default=""):
    return args[args.index(name) + 1] if name in args else default


aus = [a.strip().replace("\\", "/").strip("/") for a in opt("--ausschliessen").split(",") if a.strip()]
ohne = {"." + t.strip().lower().lstrip(".") for t in opt("--ohne-typen", "md,csv,ps1,py,svg").split(",") if t.strip()}
rest = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or args[i - 1] not in ("--ausschliessen", "--ohne-typen", "--kopieren", "--interaktiv"))]
wurzel = os.path.abspath(rest[0] if rest else os.getcwd())
zeilen = lese_index(wurzel)
liste = os.path.join(wurzel, "index", "datum_pruefliste.csv")
eingabe = os.path.join(wurzel, "index", "datum_manuell.csv")

def norm_datum(d):
    d = d.strip()
    m = re.match(r"^(\d{1,2})\.(\d{1,2})\.(\d{4})$", d)
    if m:
        d = f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    try:
        return _date.fromisoformat(d).isoformat()
    except ValueError:
        return None


if "--interaktiv" in args:
    ordner = os.path.abspath(opt("--interaktiv"))
    if not os.path.isdir(ordner):
        sys.exit(f"FEHLER: Pruefordner nicht gefunden: {ordner}")
    sel = [z for z in zeilen if z.get("dokdatum_konf") == "niedrig" and z["status"] not in ("duplikat", "ausgelagert")
           and z.get("dokdatum_quelle") in ("dateiaenderung", "datei-metadaten") and not z.get("datum")
           and os.path.splitext(z["name"])[1].lower() not in ohne
           and not any(z["pfad"] == a or z["pfad"].startswith(a + "/") for a in aus)]
    sel.sort(key=lambda z: z["pfad"])
    print(f"{len(sel)} Dokumente ohne eigenes Datum. Eingabe: TT.MM.JJJJ | Enter = leer lassen | s = ueberspringen | q = beenden\n")
    log = os.path.join(wurzel, "index", "datum_eingaben_log.csv")
    neu_log = not os.path.exists(log)
    n_ein = 0
    for i, z in enumerate(sel, 1):
        datei = os.path.join(ordner, f"{z['id']}_{z['name']}")
        print(f"[{i}/{len(sel)}] {z['id']}  {z['name']}")
        print(f"      bisheriger Vorschlag (nicht geprueft): {z.get('dokdatum', '')}  Quelle: {z.get('dokdatum_quelle', '')}")
        if z.get("dokdatum_alt"):
            print(f"      weitere Funde im Text: {z['dokdatum_alt']}")
        if os.path.exists(datei):
            try:
                os.startfile(datei)
            except (AttributeError, OSError):
                print("      Bitte selbst oeffnen:", datei)
        else:
            print("      (Kopie im Pruefordner nicht gefunden:", datei, ")")
        while True:
            eingabe = input("      Datum am Dokument: ").strip()
            if eingabe.lower() == "q":
                break
            if eingabe == "" or eingabe.lower() == "s":
                break
            iso = norm_datum(eingabe)
            if iso:
                z["datum"] = iso
                schreibe_index(wurzel, zeilen)
                with open(log, "a", newline="", encoding="utf-8-sig") as f:
                    w = csv.writer(f, delimiter=";")
                    if neu_log:
                        w.writerow(["zeitpunkt", "id", "name", "datum_eingegeben"])
                        neu_log = False
                    w.writerow([_dt.now().strftime("%Y-%m-%d %H:%M:%S"), z["id"], z["name"], iso])
                n_ein += 1
                print(f"      -> {iso} gespeichert")
                break
            print("      Ungueltig. Format TT.MM.JJJJ oder JJJJ-MM-TT, Enter = leer, s = ueberspringen, q = beenden.")
        if eingabe.lower() == "q":
            break
        print()
    print(f"Fertig. {n_ein} Daten eingetragen. Als Naechstes: datieren.py --neu, dann Chronologie, Datumsindex und pruefen.py.")
    sys.exit(0)

if "--kopieren" in args:
    zielordner = os.path.abspath(opt("--kopieren"))
    if not zielordner or os.path.commonpath([zielordner, wurzel]) == wurzel:
        sys.exit("FEHLER: --kopieren braucht einen Ordner AUSSERHALB des Archivs (sonst wuerden die Kopien im Index landen).")
    sel = [z for z in zeilen if z.get("dokdatum_konf") == "niedrig" and z["status"] not in ("duplikat", "ausgelagert")
           and z.get("dokdatum_quelle") in ("dateiaenderung", "datei-metadaten")
           and os.path.splitext(z["name"])[1].lower() not in ohne
           and not any(z["pfad"] == a or z["pfad"].startswith(a + "/") for a in aus)]
    sel.sort(key=lambda z: z["pfad"])
    os.makedirs(zielordner, exist_ok=True)
    fehler = ok = 0
    liste = []
    for z in sel:
        q = os.path.join(wurzel, z["pfad"])
        ziel = os.path.join(zielordner, f"{z['id']}_{z['name']}")
        if not os.path.exists(q):
            print("FEHLT:", z["pfad"]); fehler += 1; continue
        if os.path.exists(ziel):
            print("uebersprungen (existiert schon):", os.path.basename(ziel)); continue
        shutil.copy2(q, ziel)
        if sha256(ziel) != z["sha256"]:
            print("FEHLER Pruefsumme:", ziel); fehler += 1; continue
        ok += 1
        liste.append([z["id"], os.path.basename(ziel), z["pfad"], z.get("dokdatum", ""), z.get("dokdatum_quelle", "")])
    lp = os.path.join(zielordner, "_LISTE.csv")
    neu = not os.path.exists(lp)
    with open(lp, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        if neu:
            w.writerow(["id", "datei_im_pruefordner", "original_im_archiv", "vorschlag_datum", "quelle_des_vorschlags"])
        w.writerows(liste)
    print(f"{ok} Dateien kopiert, {fehler} Fehler. Zielordner: {zielordner}")
    print("Die Originale im Archiv sind unveraendert. Daten bitte in index/datum_pruefliste.csv eintragen, nicht in den Dateinamen.")
    sys.exit(1 if fehler else 0)

if "--einlesen" not in args:
    sel = [z for z in zeilen if z.get("dokdatum_konf") == "niedrig" and z["status"] not in ("duplikat", "ausgelagert")
           and os.path.splitext(z["name"])[1].lower() not in ohne
           and not any(z["pfad"] == a or z["pfad"].startswith(a + "/") for a in aus)]
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
    m = re.match(r"^(\d{1,2})\.(\d{1,2})\.(\d{4})$", d)       # Excel speichert Daten oft als TT.MM.JJJJ
    if m:
        d = f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
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
print(f"{ok} Datumswerte uebernommen, {len(schlecht)} abgelehnt (Format JJJJ-MM-TT oder TT.MM.JJJJ, oder unbekannte ID).")
for i, d in schlecht:
    print("  abgelehnt:", i, repr(d))
print("Jetzt datieren.py ... --neu ausfuehren.")

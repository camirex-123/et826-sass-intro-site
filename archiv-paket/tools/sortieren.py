"""Ordnet lose Dateien aus 00_Eingang_ungeprueft den Zielordnern zu.

Standard = nur VORSCHLAG (index/zuordnung_vorschlag.csv), es wird nichts verschoben.
  python tools/sortieren.py                 Vorschlag erzeugen
  python tools/sortieren.py --anwenden      nur Konfidenz 'hoch' verschieben
  python tools/sortieren.py --anwenden --auch-mittel   zusaetzlich 'mittel'
Unklare Dateien ('niedrig' / 'klaeren') bleiben im Eingang und werden NIE geraten.
Bewertet wird Dateiname (Gewicht 2) und Textanfang (Gewicht 1; txt, md, eml, docx,
pdf nur mit installiertem 'pdftotext'). Alles laeuft lokal. Duplikate werden uebersprungen."""
import csv, os, re, shutil, subprocess, sys, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from archiv_lib import *

KAT = {
    "01_Verfahren": ["klage", "beschluss", "amtsgericht", "landgericht", "verwaltungsgericht", "oberlandesgericht",
        "schriftsatz", "urteil", "ladung", "antrag", "schutzschrift", "einstweilig", "widerspruch", "ag ", "vg ",
        "gericht", "verfahren", "familiengericht", "aktenzeichen", "terminsladung"],
    "02_Behoerden": ["jugendamt", "gesundheitsamt", "staatsanwalt", "bezirksamt", "inobhutnahme", "obhutnahme",
        "polizei", "ordnungsamt", "sozialamt", "senatsverwaltung", "behoerde", "behörde", "e-akte", "akteneinsicht",
        "kinderschutz", "gefaehrdung", "gefährdung"],
    "03_Medizin_Gutachten": ["arzt", "aerzt", "ärzt", "psycholog", "psychiat", "gutachten", "attest", "diagnose",
        "kinderpraxis", "klinik", "krankenhaus", "therapie", "befund", "u-heft", "impf", "sachverstaendig", "sachverständig"],
    "04_Korrespondenz": ["gmail", "outlook", "e-mail", "email", "mail", "anwalt", "rechtsanwalt", "ra ", "kanzlei",
        "schreiben an", "antwort", "fw ", "fwd", "aw ", "wg "],
    "07_Schule_Kita": ["schule", "grundschule", "kita", "kindergarten", "lehrer", "schulleitung", "klassenlehrer",
        "dienstaufsicht", "schulamt", "hort", "elternabend", "zeugnis", "integrationsstatus", "dbbl"],
    "08_Polizei": ["polizei", "anzeige", "strafanzeige", "ermittlung", "vernehmung", "aussage"],
    "09_Vollmachten": ["vollmacht", "schweigepflichtentbindung", "einwilligung", "mandat"],
    "06_Eigene_Texte": ["statement", "entwurf", "chronologie", "notiz", "stellungnahme eigen", "eigene darstellung",
        "zusammenfassung", "lebenslauf", "erklaerung", "erklärung"],
}
EXT_KAT = {}
for e in (".png", ".jpg", ".jpeg", ".gif", ".heic", ".webp", ".bmp", ".tif", ".tiff", ".mp4", ".mov", ".avi", ".mp3",
          ".m4a", ".wav", ".opus", ".ogg", ".3gp"):
    EXT_KAT[e] = "05_Beweise"
for e in (".eml", ".msg"):
    EXT_KAT[e] = "04_Korrespondenz"

AZ = re.compile(r"(\b\d{1,2}\s?[A-Z]{1,3}\s?\d{1,4}\s?/\s?\d{2}\b"      # 2 F 84/22
                r"|\b[A-Z]{1,3}\s?\d{1,4}\s?/\s?\d{2}\b"                # F 84/22
                r"|\b\d{2}/\d{5,7}\b"                                   # 25/000396
                r"|\b\d{3,4}-\d{2}\b"                                   # 046-22, 1760-25
                r"|\b\d{2}-[A-Za-z]{2,4}-[A-Za-z]{2}-[A-Za-z]{2}-\d{3,5}-\d{4,7}\b)")  # 06-Jug-RD-SW-8127-000045


def text_anfang(p, tp=None):
    if tp and os.path.exists(tp):
        return re.sub(r"=== Seite \d+ ===", " ", lies_sidecar(tp, 20000))
    ext = os.path.splitext(p)[1].lower()
    try:
        if ext in (".txt", ".md", ".eml", ".csv", ".rtf", ".html", ".htm"):
            with open(p, "rb") as f:
                return f.read(20000).decode("utf-8", "ignore")
        if ext == ".docx":
            with zipfile.ZipFile(p) as z:
                x = z.read("word/document.xml").decode("utf-8", "ignore")
            return re.sub(r"<[^>]+>", " ", x)[:20000]
        if ext == ".pdf" and shutil.which("pdftotext"):
            r = subprocess.run(["pdftotext", "-l", "3", p, "-"], capture_output=True, timeout=60)
            return r.stdout.decode("utf-8", "ignore")[:20000]
    except Exception:
        pass
    return ""


def bewerten(p, tp=None):
    name = os.path.basename(p).lower().replace("_", " ").replace("-", " ")
    roh_txt = text_anfang(p, tp)
    txt = roh_txt.lower()
    ext = os.path.splitext(p)[1].lower()
    punkte, gruende = {}, {}
    for kat, worte in KAT.items():
        for w in worte:
            n, t = name.count(w), txt.count(w)
            if n or t:
                punkte[kat] = punkte.get(kat, 0) + 2 * min(n, 1) + min(t, 3)
                gruende.setdefault(kat, []).append(w.strip())
    if ext in EXT_KAT:
        k = EXT_KAT[ext]
        punkte[k] = punkte.get(k, 0) + (2 if (k == "05_Beweise" and len(txt.strip()) > 80) else 6)
        gruende.setdefault(k, []).append("Dateityp " + ext)
    roh = os.path.splitext(os.path.basename(p))[0].replace("_", " ")
    roh = re.sub(r"(?<![A-Za-z0-9])([A-Z]{1,3})[ _](\d{1,4})[ _-](\d{2})(?![0-9])", r"\1 \2/\3", roh)
    az = AZ.search(roh) or AZ.search(roh_txt)
    return punkte, gruende, (az.group(1).strip() if az else "")



def entscheide(punkte):
    if not punkte:
        return "", "niedrig"
    rang = sorted(punkte.items(), key=lambda kv: -kv[1])
    top, s1 = rang[0]
    s2 = rang[1][1] if len(rang) > 1 else 0
    if s1 >= 4 and s1 - s2 >= 3:
        return top, "hoch"
    if s1 >= 2 and s1 - s2 >= 2:
        return top, "mittel"
    return top, "niedrig"


def sicher(s):
    s = re.sub(r"[^A-Za-z0-9._-]+", "-", s.replace("/", "-").replace(" ", "-")).strip("-")
    return s or "ohne-az"


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    anwenden, mittel = "--anwenden" in sys.argv, "--auch-mittel" in sys.argv
    wurzel = os.path.abspath(args[0] if args else os.getcwd())
    zeilen = lese_index(wurzel)
    ids = {z["pfad"]: z for z in zeilen}
    vorschlag, bewegt = [], 0
    for z in zeilen:
        if not z["pfad"].startswith("00_Eingang_ungeprueft/") or z["status"] == "duplikat":
            continue
        p = os.path.join(wurzel, z["pfad"])
        if not os.path.exists(p):
            continue
        punkte, gruende, az = bewerten(p, text_pfad(wurzel, z["id"]))
        ziel, konf = entscheide(punkte)
        grund = "; ".join(gruende.get(ziel, [])) if ziel else "keine Hinweise"
        zielpfad = ziel
        if ziel == "01_Verfahren" and az:
            zielpfad = f"01_Verfahren/{sicher(az)}"
        v = {"id": z["id"], "pfad": z["pfad"], "ziel": zielpfad if ziel else "", "konfidenz": konf,
             "aktenzeichen": az, "grund": grund}
        vorschlag.append(v)
        if anwenden and ziel and (konf == "hoch" or (mittel and konf == "mittel")):
            os.makedirs(os.path.join(wurzel, zielpfad), exist_ok=True)
            neu = os.path.join(wurzel, zielpfad, z["name"])
            i = 1
            while os.path.exists(neu):
                b, e = os.path.splitext(z["name"])
                neu = os.path.join(wurzel, zielpfad, f"{b}__{i}{e}")
                i += 1
            alt = z["pfad"]
            shutil.move(p, neu)
            z["pfad"] = rel(wurzel, neu)
            z["name"] = os.path.basename(neu)
            z["status"] = "zugeordnet-auto"
            if az and not z["aktenzeichen"]:
                z["aktenzeichen"] = az
            z["beschreibung"] = (z["beschreibung"] + " | " if z["beschreibung"] else "") + f"auto: {grund} ({konf}); vorher: {alt}"
            bewegt += 1
        elif konf == "niedrig":
            z["status"] = "klaeren" if z["status"] == "neu" else z["status"]
    out = os.path.join(wurzel, "index", "zuordnung_vorschlag.csv")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["id", "pfad", "ziel", "konfidenz", "aktenzeichen", "grund"], delimiter=";")
        w.writeheader()
        w.writerows(vorschlag)
    schreibe_index(wurzel, zeilen)
    zaehl = {k: sum(1 for v in vorschlag if v["konfidenz"] == k) for k in ("hoch", "mittel", "niedrig")}
    print(f"{len(vorschlag)} lose Dateien bewertet: hoch={zaehl['hoch']}, mittel={zaehl['mittel']}, niedrig={zaehl['niedrig']}")
    print("Vorschlag:", out)
    print(f"{bewegt} Dateien verschoben" if anwenden else "Nichts verschoben (Vorschlag). Mit --anwenden ausfuehren, wenn der Vorschlag passt.")


if __name__ == "__main__":
    main()

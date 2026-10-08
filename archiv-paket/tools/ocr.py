"""Liest den Text aller erfassten Dokumente aus und fuehrt bei Scans OCR aus. ALLES LOKAL.
Ergebnis je Dokument: index/text/<ID>.txt mit Seitenmarken '=== Seite N ==='. Originale bleiben unveraendert.
In index/dokumente.csv: text_status = text | ocr | ocr-schwach | leer | nicht-unterstuetzt | fehler, seiten = Anzahl.

Voraussetzungen (einmalig, Windows):
  1. Tesseract installieren (UB Mannheim Build), dabei Sprachpaket 'German' (deu) anhaken.
  2. pip install pymupdf pillow
Aufruf:
  python tools/ocr.py                 nur Dokumente ohne Text
  python tools/ocr.py --neu           alles neu einlesen
  python tools/ocr.py --id D-00012    ein Dokument
Optional: --sprache deu+eng  --dpi 300
  --typen pdf,docx        nur diese Dateitypen
  --ordner EINGANG_KITA   nur Pfade, die so beginnen
  --max 50                hoechstens 50 Dokumente pro Lauf (zum Testen)
  --ungedatiert           nur Dokumente, deren Datum noch ungesichert ist (Spalte dokdatum_konf = niedrig)"""
import os, re, shutil, subprocess, sys, tempfile, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from archiv_lib import *

BILD = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".gif", ".webp"}
ROH = {".txt", ".md", ".csv", ".eml", ".html", ".htm", ".rtf"}


def finde_tesseract():
    t = shutil.which("tesseract")
    if t:
        return t
    for p in (r"C:\Program Files\Tesseract-OCR\tesseract.exe", r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"):
        if os.path.exists(p):
            return p
    return None


def ocr_bild(tess, bildpfad, sprache):
    r = subprocess.run([tess, bildpfad, "stdout", "-l", sprache, "--psm", "3"], capture_output=True, timeout=300)
    return r.stdout.decode("utf-8", "ignore")


def qualitaet_ok(text):
    woerter = re.findall(r"\S+", text)
    if len(woerter) < 5:
        return False
    gut = sum(1 for w in woerter if re.fullmatch(r"[A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß.,;:\-()]{2,}|\d[\d./,-]*", w))
    return gut / len(woerter) >= 0.55


def lies(pfad, sprache, dpi, tess):
    """Gibt (text, status, seiten) zurueck."""
    ext = os.path.splitext(pfad)[1].lower()
    if ext in ROH:
        with open(pfad, "rb") as f:
            t = f.read().decode("utf-8", "ignore")
        return (f"=== Seite 1 ===\n{t}", "text", 1) if t.strip() else ("", "leer", 1)
    if ext == ".docx":
        with zipfile.ZipFile(pfad) as z:
            x = z.read("word/document.xml").decode("utf-8", "ignore")
        t = re.sub(r"</w:p>", "\n", x)
        t = re.sub(r"<[^>]+>", "", t)
        return (f"=== Seite 1 ===\n{t}", "text", 1) if t.strip() else ("", "leer", 1)
    if ext in BILD:
        if not tess:
            return "", "fehler", 1
        t = ocr_bild(tess, pfad, sprache)
        st = "ocr" if qualitaet_ok(t) else ("ocr-schwach" if t.strip() else "leer")
        return f"=== Seite 1 ===\n{t}", st, 1
    if ext == ".pdf":
        try:
            import pymupdf as fitz
        except ImportError:
            import fitz
        doc = fitz.open(pfad)
        teile, genutzt_ocr, schwach = [], False, False
        for i, seite in enumerate(doc, 1):
            t = seite.get_text("text")
            if len(t.strip()) < 40:                      # kaum Text => gescannte Seite => OCR
                if not tess:
                    t, schwach = "", True
                else:
                    genutzt_ocr = True
                    with tempfile.TemporaryDirectory() as tmp:
                        bp = os.path.join(tmp, "s.png")
                        seite.get_pixmap(dpi=dpi).save(bp)
                        t = ocr_bild(tess, bp, sprache)
                    if not qualitaet_ok(t):
                        schwach = True
            teile.append(f"=== Seite {i} ===\n{t}")
        n = len(teile)
        text = "\n".join(teile)
        if not re.sub(r"=== Seite \d+ ===|\s", "", text):
            return "", "leer" if tess else "fehler", n
        return text, ("ocr-schwach" if schwach else "ocr" if genutzt_ocr else "text"), n
    return "", "nicht-unterstuetzt", 0


def main():
    args = sys.argv[1:]
    neu = "--neu" in args
    sprache = args[args.index("--sprache") + 1] if "--sprache" in args else "deu+eng"
    dpi = int(args[args.index("--dpi") + 1]) if "--dpi" in args else 300
    nur = args[args.index("--id") + 1] if "--id" in args else None
    typen = {"." + t.strip().lower().lstrip(".") for t in args[args.index("--typen") + 1].split(",")} if "--typen" in args else None
    ordner = args[args.index("--ordner") + 1].replace("\\", "/").strip("/") if "--ordner" in args else None
    maxn = int(args[args.index("--max") + 1]) if "--max" in args else None
    ungedatiert = "--ungedatiert" in args
    rest = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or args[i - 1] not in ("--sprache", "--dpi", "--id", "--typen", "--ordner", "--max"))]
    wurzel = os.path.abspath(rest[0] if rest else os.getcwd())
    tess = finde_tesseract()
    if not tess:
        print("HINWEIS: Tesseract nicht gefunden. Scans koennen nicht gelesen werden (nur Dokumente mit Textebene).")
    zeilen = lese_index(wurzel)
    os.makedirs(os.path.join(wurzel, "index", "text"), exist_ok=True)
    stat = {}
    for z in zeilen:
        if z["status"] in ("duplikat", "ausgelagert") or (nur and z["id"] != nur):
            continue
        if not neu and not nur and z.get("text_status") in ("text", "ocr", "ocr-schwach", "leer", "nicht-unterstuetzt"):
            continue
        if typen and os.path.splitext(z["pfad"])[1].lower() not in typen:
            continue
        if ungedatiert and z.get("dokdatum_konf") not in ("niedrig", "", None):
            continue
        if ordner and not z["pfad"].startswith(ordner):
            continue
        if maxn is not None and sum(stat.values()) >= maxn:
            break
        p = os.path.join(wurzel, z["pfad"])
        if not os.path.exists(p):
            continue
        try:
            text, st, n = lies(p, sprache, dpi, tess)
        except Exception as e:
            print("FEHLER", z["id"], z["pfad"], type(e).__name__, e)
            text, st, n = "", "fehler", 0
        if text:
            with open(text_pfad(wurzel, z["id"]), "w", encoding="utf-8") as f:
                f.write(f"# Quelle: {z['id']} | {z['pfad']} | Status: {st}\n{text}")
        z["text_status"], z["seiten"] = st, str(n)
        stat[st] = stat.get(st, 0) + 1
        print(f"{z['id']}  {st:18} {n:3} S.  {z['pfad']}")
    schreibe_index(wurzel, zeilen)
    print("Zusammenfassung:", ", ".join(f"{k}={v}" for k, v in sorted(stat.items())) or "nichts zu tun")
    schwach = [z for z in zeilen if z.get("text_status") in ("ocr-schwach", "leer", "fehler")]
    if schwach:
        print(f"{len(schwach)} Dokumente manuell pruefen (schlechter Scan, leer oder Fehler): index/dokumente.csv, Spalte text_status")


if __name__ == "__main__":
    main()

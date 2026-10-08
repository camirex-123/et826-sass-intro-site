"""Ermittelt das DOKUMENTDATUM jedes Dokuments (nicht das Download-Datum) und speichert es im Index.
Quellen in dieser Rangfolge (Spalte dokdatum_quelle, Sicherheit in dokdatum_konf):
  1. manuell     Spalte 'datum' im Index von Hand gesetzt             -> hoch
  2. dateiname   2022-06-14, 20220614, 14.06.2022, 05_07_2021         -> hoch;  220623-... (JJMMTT) -> mittel
  3. exif        Aufnahmedatum von Fotos                              -> hoch
  4. text        erstes Datum im Text (PDF, docx, txt, OCR-Text)      -> mittel
  5. video       Aufnahmedatum aus den Videodaten (ffprobe)           -> mittel
  6. pdf/docx    Erstellungsdatum der Datei                           -> niedrig
  7. dateiaenderung  Datum der Datei auf dem PC                       -> niedrig (nur Notbehelf!)
Daten, die dem Dateidatum (Download/Druckdatum) entsprechen oder danach liegen, werden bei Textfunden
ausgeblendet, weil sie meist das Druck- oder Downloaddatum sind. Weitere Funde stehen in dokdatum_alt.
Veraendert keine Dateien, nur den Index. Von Hand gesetzte Daten bleiben erhalten.
Aufruf:  python tools/datieren.py ARCHIV_WURZEL [--neu]      (--neu = alle automatischen Daten neu berechnen)"""
import os, re, shutil, subprocess, sys, zipfile
from datetime import date
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from archiv_lib import *

MIN, MAX = date(2010, 1, 1), date(2026, 12, 31)
MON = {"jan": 1, "feb": 2, "mär": 3, "mar": 3, "mrz": 3, "apr": 4, "mai": 5, "jun": 6, "jul": 7, "aug": 8,
       "sep": 9, "okt": 10, "nov": 11, "dez": 12}
RE_ISO = re.compile(r"(?<!\d)(20[0-2]\d)[-_.](0[1-9]|1[0-2])[-_.](0[1-9]|[12]\d|3[01])(?!\d)")
RE_KOMPAKT = re.compile(r"(?<!\d)(20[0-2]\d)(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])(?!\d)")
RE_DE = re.compile(r"(?<!\d)(0?[1-9]|[12]\d|3[01])\.(0?[1-9]|1[0-2])\.(20[0-2]\d|[12]\d)(?!\d)")
RE_DE_STRICH = re.compile(r"(?<!\d)(0?[1-9]|[12]\d|3[01])[-_](0?[1-9]|1[0-2])[-_](20[0-2]\d)(?!\d)")
RE_DE_MONAT = re.compile(r"(?<!\d)(\d{1,2})\.?\s*(Jan|Feb|M[aä]r|Mrz|Apr|Mai|Jun|Jul|Aug|Sep|Okt|Nov|Dez)[a-zäöü]*\.?,?\s*(20[0-2]\d)", re.I)
RE_YYMMDD = re.compile(r"(?<!\d)(1\d|2[0-6])(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])(?=[-_ ])")


def d_ok(y, m, t):
    try:
        x = date(int(y), int(m), int(t))
    except ValueError:
        return None
    return x if MIN <= x <= MAX else None


def jahr(j):
    j = int(j)
    return j + 2000 if j < 100 else j


def funde(text, kompakt=False):
    """Alle gueltigen Daten im Text mit Position (ohne JJMMTT)."""
    out = []
    for m in RE_ISO.finditer(text):
        x = d_ok(m[1], m[2], m[3]); x and out.append((m.start(), x))
    if kompakt:
        for m in RE_KOMPAKT.finditer(text):
            x = d_ok(m[1], m[2], m[3]); x and out.append((m.start(), x))
    for m in RE_DE.finditer(text):
        x = d_ok(jahr(m[3]), m[2], m[1]); x and out.append((m.start(), x))
    for m in RE_DE_STRICH.finditer(text):
        x = d_ok(m[3], m[2], m[1]); x and out.append((m.start(), x))
    for m in RE_DE_MONAT.finditer(text):
        mo = MON.get(m[2].lower()[:3].replace("ä", "a")) or MON.get(m[2].lower()[:3])
        x = mo and d_ok(m[3], mo, m[1]); x and out.append((m.start(), x))
    out.sort()
    return out


def aus_dateiname(name):
    roh = os.path.splitext(name)[0]
    f = funde(roh, kompakt=True)
    if f:
        return f[0][1], "hoch", [x for _, x in f[1:]]
    m = RE_YYMMDD.search(roh)
    if m:
        x = d_ok(2000 + int(m[1]), m[2], m[3])
        if x:
            return x, "mittel", []
    return None, None, []


def exif_datum(p):
    try:
        from PIL import Image
        with Image.open(p) as im:
            ex = im.getexif()
            for wert in (ex.get_ifd(0x8769).get(0x9003), ex.get_ifd(0x8769).get(0x9004), ex.get(0x9003), ex.get(0x0132)):
                if wert:
                    m = re.match(r"(\d{4}):(\d{2}):(\d{2})", str(wert))
                    if m:
                        x = d_ok(m[1], m[2], m[3])
                        if x:
                            return x
    except Exception:
        pass
    return None


def video_datum(p):
    ff = shutil.which("ffprobe")
    if not ff:
        return None
    try:
        r = subprocess.run([ff, "-v", "quiet", "-show_entries", "format_tags=creation_time", "-of", "default=nw=1:nk=1", p],
                           capture_output=True, timeout=60)
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})", r.stdout.decode("utf-8", "ignore").strip())
        return d_ok(m[1], m[2], m[3]) if m else None
    except Exception:
        return None


def text_und_meta(p, tp):
    """(Text, Metadatum) – Text aus OCR-Datei oder direkt aus der Datei gelesen."""
    ext = os.path.splitext(p)[1].lower()
    text, meta = "", None
    try:
        if tp and os.path.exists(tp):
            text = open(tp, encoding="utf-8", errors="ignore").read(6000)
        if ext in (".txt", ".md", ".csv", ".eml", ".html", ".htm", ".rtf") and not text:
            text = open(p, "rb").read(6000).decode("utf-8", "ignore")
        elif ext == ".docx":
            with zipfile.ZipFile(p) as z:
                if not text:
                    x = z.read("word/document.xml").decode("utf-8", "ignore")
                    text = re.sub(r"<[^>]+>", " ", x)[:6000]
                core = z.read("docProps/core.xml").decode("utf-8", "ignore")
                m = re.search(r"<dcterms:created[^>]*>(\d{4})-(\d{2})-(\d{2})", core)
                meta = d_ok(m[1], m[2], m[3]) if m else None
        elif ext == ".pdf":
            try:
                import pymupdf as fitz
            except ImportError:
                import fitz
            doc = fitz.open(p)
            if not text:
                text = "\n".join(doc[i].get_text("text") for i in range(min(3, len(doc))))[:6000]
            m = re.match(r"D:(\d{4})(\d{2})(\d{2})", doc.metadata.get("creationDate", "") or "")
            meta = d_ok(m[1], m[2], m[3]) if m else None
    except Exception:
        pass
    return text, meta


def main():
    args = sys.argv[1:]
    neu = "--neu" in args
    rest = [a for a in args if not a.startswith("--")]
    wurzel = os.path.abspath(rest[0] if rest else os.getcwd())
    zeilen = lese_index(wurzel)
    zaehl, n = {}, 0
    for z in zeilen:
        if z["status"] in ("duplikat", "ausgelagert"):
            continue
        if z.get("datum"):
            z["dokdatum"], z["dokdatum_quelle"], z["dokdatum_konf"], z["dokdatum_alt"] = z["datum"], "manuell", "hoch", ""
            continue
        if z.get("dokdatum") and not neu and z.get("dokdatum_quelle") != "manuell":
            continue
        p = os.path.join(wurzel, z["pfad"])
        if not os.path.exists(p):
            continue
        ext = os.path.splitext(p)[1].lower()
        try:
            mt = date.fromisoformat(z["geaendert"])
        except ValueError:
            mt = None
        wahl = alle = None
        kand = []                                   # (rang, datum, konf, quelle)
        x, k, alt = aus_dateiname(z["name"])
        if x:
            kand.append((1, x, k, "dateiname"))
        if ext in (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"):
            x = exif_datum(p)
            x and kand.append((2, x, "hoch", "exif"))
        text, meta = text_und_meta(p, text_pfad(wurzel, z["id"]))
        tf = [x for _, x in funde(text) if not mt or x < mt]
        if tf:
            kand.append((3, tf[0], "mittel", "text"))
            alt += tf[1:5]
        if ext in (".mp4", ".mov", ".avi", ".mkv", ".m4v", ".3gp"):
            x = video_datum(p)
            x and kand.append((4, x, "mittel", "video"))
        if meta and meta != mt:
            kand.append((5, meta, "niedrig", "datei-metadaten"))
        if mt:
            kand.append((6, mt, "niedrig", "dateiaenderung"))
        if kand:
            kand.sort(key=lambda c: c[0])
            r, x, k, q = kand[0]
            andere = sorted(({c[1].isoformat() for c in kand[1:] if c[3] != "dateiaenderung"} | {a.isoformat() for a in alt}) - {x.isoformat()} - ({mt.isoformat()} if mt else set()))
            z["dokdatum"], z["dokdatum_konf"], z["dokdatum_quelle"] = x.isoformat(), k, q
            z["dokdatum_alt"] = " | ".join(andere[:5])
            zaehl[(q, k)] = zaehl.get((q, k), 0) + 1
        n += 1
    schreibe_index(wurzel, zeilen)
    print(f"{n} Dokumente datiert")
    for (q, k), c in sorted(zaehl.items(), key=lambda kv: -kv[1]):
        print(f"  {c:4}  {q:16} {k}")
    sicher = sum(c for (q, k), c in zaehl.items() if k in ("hoch", "mittel"))
    print(f"Davon mit gesichertem Datum (hoch/mittel): {sicher}. Der Rest (niedrig) braucht deine Pruefung.")


if __name__ == "__main__":
    main()

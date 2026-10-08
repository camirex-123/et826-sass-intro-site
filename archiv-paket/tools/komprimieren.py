"""Erzeugt verkleinerte KOPIEN von Bildern und Videos. Originale bleiben unveraendert (Beweiswert!).
Fuer die Weitergabe (z. B. an den Rechtsanwalt) nimmst du die Kopien, die Originale bleiben im Archiv.
- Bilder: laengste Kante max. 2000 px, JPEG-Qualitaet 80, Ausrichtung und EXIF (Datum, Ort) bleiben erhalten.
  PNG bleibt PNG (verlustfrei optimiert), damit Text in Screenshots lesbar bleibt.
- Videos: H.264, max. 1280 px Breite, CRF 28, AAC 96 kbit/s, Metadaten uebernommen. Braucht ffmpeg.
- Dateien unter --min-mb (Standard 1 MB) werden uebersprungen, da sich das nicht lohnt.
- Nur die Originale (keine Duplikate) werden bearbeitet. Wird eine Kopie nicht kleiner, wird sie verworfen.
- Schon erledigte Dokumente werden uebersprungen (Spalte 'komprimiert' im Index).
Aufruf:
  python tools/komprimieren.py ARCHIV_WURZEL --ziel "KANZLEI_CODEX_CASE_TEMPLATE/99_CODEX_OUTPUT/komprimiert"
      [--typen jpg,png,mp4] [--ordner PRAEFIX] [--max 20] [--min-mb 1] [--kante 2000] [--qualitaet 80] [--crf 28]
ffmpeg installieren (Windows): winget install Gyan.FFmpeg   (danach neues cmd-Fenster oeffnen)"""
import os, shutil, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from archiv_lib import *

BILD = {".jpg", ".jpeg", ".png"}
VIDEO = {".mp4", ".mov", ".avi", ".mkv", ".m4v", ".3gp", ".wmv", ".webm"}


def opt(args, name, default=None):
    return args[args.index(name) + 1] if name in args else default


def bild(q, z, kante, qual):
    from PIL import Image, ImageOps
    with Image.open(q) as im:
        exif = im.info.get("exif")
        im = ImageOps.exif_transpose(im)
        if max(im.size) > kante:
            f = kante / max(im.size)
            im = im.resize((round(im.width * f), round(im.height * f)), Image.LANCZOS)
        if os.path.splitext(q)[1].lower() == ".png":
            im.save(z, "PNG", optimize=True)
        else:
            im.convert("RGB").save(z, "JPEG", quality=qual, optimize=True, **({"exif": exif} if exif else {}))


def video(q, z, crf):
    ff = shutil.which("ffmpeg")
    if not ff:
        raise RuntimeError("ffmpeg nicht gefunden (winget install Gyan.FFmpeg)")
    r = subprocess.run([ff, "-y", "-loglevel", "error", "-i", q, "-vf", "scale='min(1280,iw)':-2", "-c:v", "libx264",
                        "-crf", str(crf), "-preset", "medium", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart",
                        "-map_metadata", "0", z], capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.decode("utf-8", "ignore")[-300:])


def main():
    args = sys.argv[1:]
    ziel = (opt(args, "--ziel") or "").replace("\\", "/").strip("/")
    if not ziel:
        sys.exit('FEHLER: --ziel fehlt, z. B. --ziel "KANZLEI_CODEX_CASE_TEMPLATE/99_CODEX_OUTPUT/komprimiert"')
    typen = {"." + t.strip().lower().lstrip(".") for t in opt(args, "--typen", "").split(",") if t.strip()} or (BILD | VIDEO)
    ordner = (opt(args, "--ordner") or "").replace("\\", "/").strip("/")
    maxn = int(opt(args, "--max", 0)) or None
    kante, qual, crf = int(opt(args, "--kante", 2000)), int(opt(args, "--qualitaet", 80)), int(opt(args, "--crf", 28))
    min_b = float(opt(args, "--min-mb", 1)) * 1e6
    feste = ("--min-mb", "--ziel", "--typen", "--ordner", "--max", "--kante", "--qualitaet", "--crf")
    rest = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or args[i - 1] not in feste)]
    wurzel = os.path.abspath(rest[0] if rest else os.getcwd())
    zeilen = lese_index(wurzel)
    vorher = nachher = n = 0
    stat = {}
    for z in zeilen:
        ext = os.path.splitext(z["pfad"])[1].lower()
        if z["status"] in ("duplikat", "ausgelagert") or z.get("komprimiert") or ext not in typen or ext not in (BILD | VIDEO):
            continue
        if z["pfad"].startswith(ziel + "/") or (ordner and not z["pfad"].startswith(ordner)):
            continue
        if maxn and n >= maxn:
            break
        q = os.path.join(wurzel, z["pfad"])
        if not os.path.exists(q) or os.path.getsize(q) < min_b:
            continue
        name = os.path.splitext(z["name"])[0]
        zext = ".mp4" if ext in VIDEO else ext
        zp = os.path.join(wurzel, ziel, f"{z['id']}__{name}{zext}")
        os.makedirs(os.path.dirname(zp), exist_ok=True)
        try:
            (video(q, zp, crf) if ext in VIDEO else bild(q, zp, kante, qual))
            a, b = os.path.getsize(q), os.path.getsize(zp)
            if b >= a:
                os.remove(zp)
                z["komprimiert"] = "nicht-kleiner"
                stat["nicht kleiner"] = stat.get("nicht kleiner", 0) + 1
            else:
                z["komprimiert"] = rel(wurzel, zp)
                vorher, nachher = vorher + a, nachher + b
                stat["komprimiert"] = stat.get("komprimiert", 0) + 1
                print(f"{z['id']}  {a / 1e6:8.1f} MB -> {b / 1e6:7.1f} MB")
        except Exception as e:
            if os.path.exists(zp):
                os.remove(zp)
            z["komprimiert"] = "fehler"
            stat["fehler"] = stat.get("fehler", 0) + 1
            print("FEHLER", z["id"], type(e).__name__, str(e)[:200])
        n += 1
        schreibe_index(wurzel, zeilen)   # Fortschritt sofort sichern, damit ein Abbruch nichts verliert
    schreibe_index(wurzel, zeilen)
    print("Zusammenfassung:", ", ".join(f"{k}={v}" for k, v in sorted(stat.items())) or "nichts zu tun")
    if vorher:
        print(f"Gesamt: {vorher / 1e6:.0f} MB -> {nachher / 1e6:.0f} MB ({100 - 100 * nachher / vorher:.0f} % gespart)")


if __name__ == "__main__":
    main()

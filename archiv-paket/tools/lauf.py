"""Ein Befehl fuer 'Neues verarbeiten' - beliebig oft wiederholbar (es wird nur Neues angefasst).
Reihenfolge: inventar -> duplikate -> ocr -> datieren -> uebernehmen (PLAN); mit --chronik DIR zusaetzlich die Chronologie. Kopiert wird nur mit --anwenden.
Videos (mp4, mov ...) werden erfasst und gehasht, aber nicht inhaltlich gelesen (text_status = nicht-unterstuetzt).
Aufruf:
  python tools/lauf.py ARCHIV_WURZEL --ziel "KANZLEI_CODEX_CASE_TEMPLATE/01_ORIGINALE"
      [--bevorzugt "A,B"] [--ausschliessen "A,B"] [--ohne-typen md,csv,ps1,py,svg] [--ocr-typen pdf,docx,jpg,png] [--paket "EINGANGSORDNER=ZIELORDNER"] [--anwenden]"""
import os, subprocess, sys

hier = os.path.dirname(os.path.abspath(__file__))
args = sys.argv[1:]


def opt(name):
    return args[args.index(name) + 1] if name in args else None


rest = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or args[i - 1] not in
        ("--ziel", "--bevorzugt", "--ausschliessen", "--ohne-typen", "--ocr-typen", "--chronik", "--paket"))]
wurzel = rest[0] if rest else os.getcwd()
ziel = opt("--ziel")
if not ziel:
    sys.exit("FEHLER: --ziel fehlt")


def schritt(titel, skript, *extra):
    print(f"\n=== {titel} ===", flush=True)
    r = subprocess.run([sys.executable, os.path.join(hier, skript), wurzel, *extra])
    if r.returncode not in (0,):
        print(f"HINWEIS: Schritt '{titel}' meldete Rueckgabe {r.returncode}")
    return r.returncode


schritt("1/5 Neue Dateien erfassen", "inventar.py")
schritt("2/5 Duplikate bewerten", "duplikate.py", *(["--bevorzugt", opt("--bevorzugt")] if opt("--bevorzugt") else []))
ocr = ["--typen", opt("--ocr-typen")] if opt("--ocr-typen") else []
schritt("3/5 Text lesen / OCR (nur Neues)", "ocr.py", *ocr)
schritt("4/5 Dokumentdatum ermitteln", "datieren.py")
u = ["--ziel", ziel]
for flag in ("--ausschliessen", "--ohne-typen", "--paket"):
    if opt(flag):
        u += [flag, opt(flag)]
if "--anwenden" in args:
    u.append("--anwenden")
schritt("5/5 Uebernahme " + ("KOPIEREN" if "--anwenden" in args else "PLAN"), "uebernehmen.py", *u)
if opt("--chronik"):
    schritt("Chronologie schreiben", "chronologie.py", "--ziel", opt("--chronik"))
print("\nFertig. Pruefen mit: python tools/pruefen.py", wurzel)

"""Gemeinsame Funktionen fuer das Aktenarchiv (nur Standardbibliothek)."""
import csv, hashlib, os
from datetime import datetime

ORDNER = [
    "00_Eingang_ungeprueft",
    "01_Verfahren",
    "02_Behoerden",
    "03_Medizin_Gutachten",
    "04_Korrespondenz",
    "05_Beweise",
    "06_Eigene_Texte",
    "99_Duplikate_Quarantaene",
    "index",
]
SPALTEN = ["id", "pfad", "name", "sha256", "bytes", "geaendert", "erfasst_am",
           "typ", "datum", "aktenzeichen", "beschreibung", "status", "duplikat_von"]
IGNORIERT_ORDNER = {"index", "tools", ".git"}
IGNORIERT_DATEIEN = {"AGENTS.md", "README.md", ".gitignore", "desktop.ini", "Thumbs.db"}


def sha256(pfad):
    h = hashlib.sha256()
    with open(pfad, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def dateien(wurzel):
    for dirpath, dirnames, files in os.walk(wurzel):
        dirnames[:] = [d for d in dirnames if d not in IGNORIERT_ORDNER and not d.startswith(".")]
        for name in files:
            if name in IGNORIERT_DATEIEN or name.startswith("~$"):
                continue
            yield os.path.join(dirpath, name)


def index_pfad(wurzel):
    return os.path.join(wurzel, "index", "dokumente.csv")


def lese_index(wurzel):
    p = index_pfad(wurzel)
    if not os.path.exists(p):
        return []
    with open(p, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f, delimiter=";"))


def schreibe_index(wurzel, zeilen):
    p = index_pfad(wurzel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=SPALTEN, delimiter=";", extrasaction="ignore")
        w.writeheader()
        for z in zeilen:
            w.writerow({k: z.get(k, "") for k in SPALTEN})


def rel(wurzel, pfad):
    return os.path.relpath(pfad, wurzel).replace(os.sep, "/")


def jetzt():
    return datetime.now().strftime("%Y-%m-%d %H:%M")

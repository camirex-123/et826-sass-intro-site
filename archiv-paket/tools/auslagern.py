"""Lagert einen Ordner des Archivs auf ein anderes Laufwerk aus (z. B. Fremdprojekte). Mit Pruefsummen-Kontrolle.
- Kopiert jede Datei, vergleicht den SHA-256 von Quelle und Kopie und ueberschreibt NIE etwas im Ziel.
- Vermerkt die Dokumente im Index als status 'ausgelagert' (mit neuem Ort in 'beschreibung'). Sie erscheinen dann
  nicht mehr in Chronologie, Duplikat-Bewertung und Uebernahme.
- Die Quelle bleibt standardmaessig UNVERAENDERT. Erst mit --quelle-loeschen werden die geprueften Quelldateien entfernt
  (nur die, deren Kopie verifiziert ist; leere Ordner werden mit entfernt). Das ist nicht rueckgaengig zu machen.
- Standard ist ein Probelauf: zeigt Anzahl, Groesse und freien Platz, kopiert nichts.
Aufruf:
  python tools/auslagern.py ARCHIV_WURZEL --quelle ALTARCHIV_C --ziel H:\\Projekten              (Probelauf)
  python tools/auslagern.py ARCHIV_WURZEL --quelle ALTARCHIV_C --ziel H:\\Projekten --anwenden    (kopieren + pruefen)
  ... --anwenden --quelle-loeschen                                                              (danach Quelle entfernen)
Das Ziel ist <ZIEL>\\<Name des Quellordners>, hier also H:\\Projekten\\ALTARCHIV_C."""
import os, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from archiv_lib import *


def opt(args, name):
    return args[args.index(name) + 1] if name in args else None


args = sys.argv[1:]
quelle = (opt(args, "--quelle") or "").replace("\\", "/").strip("/")
ziel_basis = opt(args, "--ziel")
anwenden, loeschen = "--anwenden" in args, "--quelle-loeschen" in args
rest = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or args[i - 1] not in ("--quelle", "--ziel"))]
if not quelle or not ziel_basis:
    sys.exit('FEHLER: --quelle und --ziel angeben, z. B. --quelle ALTARCHIV_C --ziel H:\\Projekten')
wurzel = os.path.abspath(rest[0] if rest else os.getcwd())
src = os.path.join(wurzel, *quelle.split("/"))
if not os.path.isdir(src):
    sys.exit(f"FEHLER: Quellordner nicht gefunden: {src}")
if not os.path.isdir(os.path.dirname(os.path.abspath(ziel_basis)) if not os.path.isdir(ziel_basis) else ziel_basis):
    sys.exit(f"FEHLER: Ziel-Laufwerk oder Ordner nicht erreichbar: {ziel_basis}")
dst = os.path.join(os.path.abspath(ziel_basis), os.path.basename(src))
if os.path.abspath(dst).lower().startswith(wurzel.lower()):
    sys.exit("FEHLER: Das Ziel darf nicht innerhalb des Archivs liegen.")

dateien_liste = []
for dp, _, fs in os.walk(src):
    for n in fs:
        dateien_liste.append(os.path.join(dp, n))
gesamt = sum(os.path.getsize(p) for p in dateien_liste)
frei = shutil.disk_usage(ziel_basis if os.path.isdir(ziel_basis) else os.path.dirname(os.path.abspath(ziel_basis))).free
print(f"Quelle: {src}\nZiel:   {dst}")
print(f"{len(dateien_liste)} Dateien, {gesamt / 1e6:.0f} MB; frei am Ziel: {frei / 1e9:.1f} GB")
if gesamt > frei:
    sys.exit("FEHLER: Nicht genug Platz am Ziel.")
if not anwenden:
    print("Probelauf: nichts kopiert. Mit --anwenden ausfuehren.")
    sys.exit(0)

zeilen = lese_index(wurzel)
nach_pfad = {z["pfad"]: z for z in zeilen}
fehler = geprueft = uebersprungen = 0
ok_quellen = []
for p in dateien_liste:
    r = os.path.relpath(p, src)
    zp = os.path.join(dst, r)
    try:
        h = sha256(p)
        if os.path.exists(zp):
            if sha256(zp) == h:
                uebersprungen += 1
                ok_quellen.append(p)
                continue
            print("FEHLER Ziel existiert mit anderem Inhalt, nicht ueberschrieben:", zp)
            fehler += 1
            continue
        os.makedirs(os.path.dirname(zp), exist_ok=True)
        shutil.copy2(p, zp)
        if sha256(zp) != h:
            print("FEHLER Pruefsumme der Kopie stimmt nicht:", zp)
            os.remove(zp)
            fehler += 1
            continue
        geprueft += 1
        ok_quellen.append(p)
    except OSError as e:
        print("FEHLER", p, e)
        fehler += 1

ok_pfade = {rel(wurzel, p) for p in ok_quellen}
for pfad in ok_pfade:
    z = nach_pfad.get(pfad)
    if z:
        z["status"] = "ausgelagert"
        z["beschreibung"] = (z["beschreibung"] + " | " if z["beschreibung"] else "") + "ausgelagert nach: " + os.path.join(dst, os.path.relpath(os.path.join(wurzel, pfad), src))
schreibe_index(wurzel, zeilen)
print(f"{geprueft} kopiert und geprueft, {uebersprungen} schon vorhanden und identisch, {fehler} Fehler.")
if fehler:
    print("Wegen Fehlern wird nichts geloescht. Bitte Meldungen pruefen und den Befehl wiederholen.")
    sys.exit(1)
if loeschen:
    n = 0
    for p in ok_quellen:
        os.remove(p)
        n += 1
    for dp, dn, fs in sorted(os.walk(src, topdown=False), key=lambda t: -len(t[0])):
        if not os.listdir(dp):
            os.rmdir(dp)
    print(f"{n} Quelldateien entfernt (Kopien auf {dst} sind verifiziert).")
else:
    print("Quelle unveraendert. Nach eigener Kontrolle der Kopien kannst du mit --quelle-loeschen die Quelle entfernen.")

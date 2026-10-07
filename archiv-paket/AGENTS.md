# Arbeitsregeln fuer Codex: Aktenarchiv Amtshaftungsklage

Kontext: Archiv juristischer Unterlagen (Gerichts- und Behoerdenakten, Korrespondenz, Beweise) zur
Weitergabe an die beauftragte Rechtsanwaltskanzlei. Die Daten betreffen Minderjaehrige und sind hoechst
sensibel. Rechtliche Bewertungen trifft ausschliesslich der Rechtsanwalt.
Fallspezifische Angaben (Verfahren, Beteiligte) stehen NUR in der lokalen Kopie dieser Datei, nie im Repo.

## Unverrueckbare Regeln
1. **Originale nie veraendern.** Nicht bearbeiten, kuerzen, umwandeln oder ueberschreiben. Bearbeitete
   Fassungen sind neue Dateien mit Verweis auf die ID des Originals (Spalte `beschreibung`).
2. **Nichts loeschen.** Duplikate werden nach `99_Duplikate_Quarantaene/` verschoben und im Index als
   `duplikat` mit `duplikat_von` markiert.
3. **Nichts hochladen, senden oder veroeffentlichen.** Kein Push in oeffentliche Repos, keine Cloud-Dienste,
   keine Mails ohne ausdrueckliche Anweisung des Nutzers.
4. **Nichts erfinden.** Fehlt ein Datum, Aktenzeichen oder Absender, bleibt das Feld leer oder `unklar`.
   Keine Schlussfolgerungen als Tatsachen darstellen. Unsichere Angaben mit `?` kennzeichnen.
5. **Quelle immer festhalten** (Gericht, Behoerde, Mail, ChatGPT-Export, Screenshot von wem).

## Struktur
- `00_Eingang_ungeprueft/` neue, noch nicht einsortierte Dateien
- `01_Verfahren/` Klagen, Beschluesse, Schriftsaetze, je Unterordner pro Aktenzeichen
- `02_Behoerden/` Jugendamt, Gesundheitsamt, Staatsanwaltschaft
- `03_Medizin_Gutachten/`
- `04_Korrespondenz/` Mails und Anwaltsschriftverkehr
- `05_Beweise/` Screenshots, Fotos, Chats
- `06_Eigene_Texte/` Statements, Entwuerfe
- `99_Duplikate_Quarantaene/`
- `index/dokumente.csv` Hauptverzeichnis (Trennzeichen `;`), `index/chronologie.md`

## Dateinamen
`JJJJ-MM-TT_Typ_Aktenzeichen_Titel.ext`, z. B. `2022-08-11_Beschluss_F-84-22_AG-Berg.pdf`.
Unbekanntes Datum: `0000-00-00`. Unbekanntes Aktenzeichen: `ohne-az`. Keine Umlaute oder Leerzeichen.
Umbenennen nur auf Anweisung; der alte Name kommt in `beschreibung`.

## Arbeitsablauf
1. Neue Dateien nach `00_Eingang_ungeprueft/` legen.
2. `python tools/inventar.py` ausfuehren (erfasst, hasht, erkennt exakte Duplikate).
3. `python tools/ocr.py` liest alle Dokumente aus (PDF-Textebene, docx, Mails) und fuehrt bei Scans/Bildern lokale OCR aus.
   Ergebnis: `index/text/<ID>.txt` mit Seitenmarken. `text_status` im Index: text, ocr, ocr-schwach, leer, fehler.
   Dokumente mit `ocr-schwach`, `leer` oder `fehler` dem Nutzer zur manuellen Pruefung vorlegen, nie als gelesen behandeln.
   OCR nur lokal ausfuehren, nie ueber Cloud-Dienste.
4. `python tools/sortieren.py` erzeugt einen Zuordnungsvorschlag (`index/zuordnung_vorschlag.csv`), nichts wird verschoben. Nach Pruefung `--anwenden` (nur Konfidenz hoch). Unklare Dateien (niedrig) bleiben im Eingang und werden NIE geraten, sondern dem Nutzer vorgelegt.
   Danach pro Datei `typ`, `datum`, `aktenzeichen`, `beschreibung` ergaenzen, dann in den passenden Ordner verschieben
   (Pfad im Index nachziehen) und `status` auf `geprueft` setzen.
5. Inhaltlich gleiche, aber nicht byte-gleiche Dateien (z. B. Doc und PDF derselben Schrift) NICHT automatisch
   loeschen. Als Kandidat in `status = "dublette-pruefen"` setzen und dem Nutzer melden.
6. `python tools/pruefen.py` muss ohne FEHLER laufen, bevor etwas weitergegeben wird.
7. `index/chronologie.md` aus dem Index pflegen: Datum, Ereignis, Dokument-IDs. Nur belegte Fakten.

## Status-Werte
`neu`, `zugeordnet-auto`, `geprueft`, `duplikat`, `dublette-pruefen`, `unleserlich`, `klaeren`

## Inhaltsanalyse
- Grundlage sind nur die Textdateien in `index/text/`. Jede Aussage nennt Dokument-ID und Seite, z. B. `[D-00012, S. 3]`.
- OCR-Fehler moeglich: Namen, Daten, Aktenzeichen und Betraege bei Scans mit dem Original vergleichen und als
  `(OCR, ungeprueft)` kennzeichnen, bis der Nutzer sie bestaetigt.
- Fakten (steht im Dokument), Bewertung (Meinung) und Luecken (fehlt/unklar) getrennt darstellen.
- Widersprueche zwischen Dokumenten nennen, nicht aufloesen. Rechtliche Wuerdigung nur durch den Rechtsanwalt.

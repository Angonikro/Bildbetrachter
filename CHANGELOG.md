## Changelog

## 0.1.19
- Vollständige Migration der grafischen Benutzeroberfläche von Tkinter auf Qt 6 (PySide6).
- Neugestaltung der Programmoberfläche mit modernem blauem Design.
- Überarbeitung der Menüführung, Werkzeugleisten und Dialogfenster.
- Neue, größere und farbige Symbole in der oberen Werkzeugleiste.
- Fenstergröße und Fensterposition werden dauerhaft gespeichert.

## 0.1.18 
- Kontextmenü wird erst beim Loslassen der rechten Maustaste geöffnet.
- Verhindert, dass das Loslassen des auslösenden Rechtsklicks direkt den obersten Menüeintrag auswählt.
- Rechtsklick-Kontextmenü mit Bildnavigation, Speichern, Transformationen und Ansicht.
- Virtuelle Vorschauliste: maximal 20 sichtbare/nahe Vorschaubilder gleichzeitig.
- Dateiargumente werden beim Start geöffnet (Doppelklick/Öffnen mit).
- Bildanzeige und Dateizuordnung
- Bilder lassen sich über die normale Programmoberfläche öffnen.
- Unterstützung für den Start über „Öffnen mit“ und die Dateizuordnung wurde eingebaut.
- Die übergebene Bilddatei wird beim Programmstart geladen.
- Die Speichern-Schaltfläche in der Symbolleiste verwendet jetzt „Speichern“ und überschreibt damit die geöffnete Originaldatei.
- „Speichern unter“ bleibt separat und erstellt weiterhin eine neue Datei.

## 0.1.17
- Fehler behoben: Der Farbauswahldialog im Zeichenmodus wurde wegen eines fehlenden `colorchooser`-Imports nicht geöffnet.

## v0.1.16
- Einstellungen werden benutzerspezifisch unter `~/.config/bildbetrachter/settings.ini` gespeichert (XDG_CONFIG_HOME wird unterstützt).
- Bestehende `settings.ini` im Programmordner und ältere JSON-Einstellungen werden beim ersten Start automatisch übernommen, wenn noch keine neue Konfiguration existiert.
- Die Migration löscht die alten Dateien nicht.
- Debian-Paket mit Menüeintrag und Anwendungssymbol ergänzt.

## v0.1.15

### Fehlerbehebung
- Zeichnungen werden jetzt korrekt in den Rückgängig-/Wiederholen-Verlauf übernommen.
- Nach dem ersten Zeichenstrich wird die Rückgängig-/Wiederholen-Funktion sofort aktualisiert.

### Fehlerbehebung
- Toolbar-Symbole sind im hellen Theme jetzt deutlich sichtbar.
- Symbole werden beim Wechsel zwischen hellem und dunklem Theme automatisch passend neu aufgebaut.


## v0.1.15
- Erweiterte Bildformat-Unterstützung für robuste, in Pillow standardmäßig verfügbare Formate.
- Öffnen-Dialog erkennt jetzt BMP/DIB, JPEG-Varianten, PNG, GIF, WebP, TIFF, ICO, PPM/PGM/PBM/PNM, XBM/XPM, TGA und PCX.
- Speichern unter unterstützt die zusätzlichen Formate, soweit sie von Pillow direkt bereitgestellt werden.
- Die bewährten Funktionen aus v0.1.13 bleiben erhalten.

## v0.1.13
- Helligkeit, Kontrast und Sättigung korrigiert.
- Nachfrage bei ungespeicherten Änderungen beim Bildwechsel und Beenden.
- Anleitung aktualisiert.

## v0.1.12
- Zuschneiden korrigiert; falscher Versatz bzw. Abschneiden am linken Bildrand behoben.
- Anleitung aktualisiert.

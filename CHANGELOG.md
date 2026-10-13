## 0.1.16
- Anleitung und Info-Dialog zeigen jetzt korrekt Version 0.1.16.

# CHANGELOG

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

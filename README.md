# Bildbetrachter v0.1.17

Ein Bildbetrachter mit einfachen Bearbeitungsfunktionen, dunklem/hellem Theme und Diashow.

## Funktionen

- Bilder öffnen und speichern
- Drehen, spiegeln, zuschneiden und einfache Bildkorrekturen
- Zeichnen sowie Rückgängig/Wiederholen
- Dunkles und helles Theme
- Diashow und Navigation im Bildordner
- Unterstützung für BMP/DIB, JPEG, PNG, GIF, WebP, TIFF, ICO, PPM/PGM/PBM/PNM, XBM/XPM, TGA und PCX (abhängig von Pillow)

## Voraussetzungen

- Python 3
- Tkinter
- Pillow

## Installation unter Debian

Für Debian/Raspberry Pi OS:

```bash
sudo apt install ./bildbetrachter_0.1.17_all.deb
```

Alternativ können die Abhängigkeiten aus `requirements.txt` installiert und `python3 Bildbetrachter.py` gestartet werden.

## Speicherorte

Einstellungen werden benutzerspezifisch gespeichert unter:

`~/.config/bildbetrachter/settings.ini`

Falls `XDG_CONFIG_HOME` gesetzt ist, wird stattdessen `$XDG_CONFIG_HOME/bildbetrachter/settings.ini` verwendet.

Bisherige Einstellungen werden beim ersten Start übernommen, sofern die neue Konfigurationsdatei noch nicht existiert:
- `settings.ini` im bisherigen Programmordner
- `~/.bildbetrachter_settings.json` aus älteren Versionen

Die alten Dateien bleiben dabei unverändert. Bilder werden nicht automatisch in den Programmordner kopiert; zuletzt verwendete Ordner und die übrigen Optionen stehen in der Konfigurationsdatei.


## Projektdateien

- `Bildbetrachter.py` – Anwendung
- `settings.ini` – alte Standard-/Migrationsdatei für bestehende Installationen
- `requirements.txt` – Python-Abhängigkeiten
- `CHANGELOG.md` – Versionshistorie

**Bildbetrachter v0.1.17 — Goldisoft 2026**

73 de DO2QG Andreas

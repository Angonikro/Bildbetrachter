# Bildbetrachter v0.1.18

Ein Bildbetrachter mit einfachen Bearbeitungsfunktionen, dunklem/hellem Theme und Diashow.

## Funktionen

- Bilder öffnen und speichern
- Drehen, spiegeln, zuschneiden und einfache Bildkorrekturen
- Zeichnen sowie Rückgängig/Wiederholen
- Dunkles und helles Theme
- Diashow und Navigation im Bildordner
- Virtuelle Vorschaubilder: sichtbare Bilder werden nachgeladen; der Vorschaubild-Cache ist auf maximal 20 Einträge begrenzt
- Kontextmenü mit rechter Maustaste und Bildaktionen
- Unterstützung für BMP/DIB, JPEG, PNG, GIF, WebP, TIFF, ICO, PPM/PGM/PBM/PNM, XBM/XPM, TGA und PCX (abhängig von Pillow)

## Speicherorte

Einstellungen werden benutzerspezifisch gespeichert unter:

`~/.config/bildbetrachter/settings.ini`

Falls `XDG_CONFIG_HOME` gesetzt ist, wird stattdessen `$XDG_CONFIG_HOME/bildbetrachter/settings.ini` verwendet.

Bisherige Einstellungen werden beim ersten Start übernommen, sofern die neue Konfigurationsdatei noch nicht existiert:
- `settings.ini` im bisherigen Programmordner
- `~/.bildbetrachter_settings.json` aus älteren Versionen

Die alten Dateien bleiben dabei unverändert. Bilder werden nicht automatisch in den Programmordner kopiert; zuletzt verwendete Ordner und die übrigen Optionen stehen in der Konfigurationsdatei.

## Voraussetzungen

- Python 3
- Tkinter (`python3-tk`)
- Pillow (`python3-pil`)

## ZIP-Version unter Debian / Raspberry Pi OS starten

Die ZIP-Version muss nicht systemweit installiert werden. Du kannst sie in einem beliebigen Ordner entpacken und direkt mit Python starten.

### 1. ZIP-Datei entpacken

Entpacke `Bildbetrachter_0.1.18_GITHUB.zip`. Im entpackten Ordner befindet sich der Unterordner `Bild`.

### 2. Benötigte Pakete installieren

Öffne ein Terminal und führe einmalig aus:

```bash
sudo apt update
sudo apt install python3 python3-tk python3-pil
```

### 3. Anwendung starten

Wechsle im Terminal in den Ordner `Bild` (den Pfad gegebenenfalls an deinen Entpack-Ort anpassen):

```bash
cd ~/Downloads/Bild
python3 Bildbetrachter.py
```

Wenn du die ZIP-Datei an einem anderen Ort entpackt hast, passe den `cd`-Pfad entsprechend an. Das Terminal kann nach dem Start geöffnet bleiben.

### 4. Optional: Desktop-Verknüpfung erstellen

Im Ordner `Bild` liegt das Skript `install_desktop_launcher.sh`. Es erstellt eine Desktop-Verknüpfung mit dem mitgelieferten Bildbetrachter-Icon. Starte es so:

```bash
cd ~/Downloads/Bild
chmod +x install_desktop_launcher.sh
./install_desktop_launcher.sh
```

Passe auch hier den Pfad an, falls du die ZIP-Datei an einem anderen Ort entpackt hast. Anschließend kannst du den Bildbetrachter über das Symbol auf dem Desktop starten.

## DEB-Version installieren

Wenn du statt der ZIP-Version das Debian-Paket verwendest, installiere es im Verzeichnis mit der DEB-Datei so:

```bash
sudo apt install ./bildbetrachter_0.1.18_all.deb
```

Danach kannst du den Bildbetrachter über das Anwendungsmenü starten.

## Projektdateien

- `Bildbetrachter.py` – Anwendung
- `settings.ini` – alte Standard-/Migrationsdatei für bestehende Installationen
- `requirements.txt` – Python-Abhängigkeiten
- `install_desktop_launcher.sh` – erstellt eine Desktop-Verknüpfung
- `CHANGELOG.md` – Versionshistorie

**Bildbetrachter v0.1.18 — Goldisoft 2026**

73 de DO2QG Andreas

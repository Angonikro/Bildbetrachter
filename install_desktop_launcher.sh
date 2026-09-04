#!/bin/bash
set -e

# Chess-Pionier-style desktop launcher installer for Bildbetrachter.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$SCRIPT_DIR"
APP_FILE="$APP_DIR/Bildbetrachter.py"
DESKTOP_DIR="${XDG_DESKTOP_DIR:-$HOME/Desktop}"
DESKTOP_FILE="$DESKTOP_DIR/Bildbetrachter.desktop"
ICON_FILE="$APP_DIR/icons/bild_icon_512.png"

if [ ! -f "$APP_FILE" ]; then
    echo "Fehler: Bildbetrachter.py wurde nicht gefunden."
    echo "Bitte dieses Skript direkt aus dem Ordner 'Bild' starten."
    exit 1
fi

mkdir -p "$DESKTOP_DIR"

if [ ! -f "$ICON_FILE" ]; then
    echo "Fehler: Das Bildbetrachter-Icon wurde nicht gefunden."
    exit 1
fi

# Create a launcher that always uses the Python file from this exact folder.
cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Bildbetrachter
Comment=Bildbetrachter und einfacher Bildeditor
Exec=python3 "$APP_FILE"
Path=$APP_DIR
Terminal=false
Icon=$ICON_FILE
Categories=Graphics;Viewer;Utility;
EOF

chmod +x "$DESKTOP_FILE"

echo
echo "Desktop-Verknüpfung wurde erstellt:"
echo "$DESKTOP_FILE"
echo
echo "Du kannst den Bildbetrachter jetzt über das Desktop-Symbol starten."
echo "Das eigene Bildbetrachter-Icon wurde eingebunden."

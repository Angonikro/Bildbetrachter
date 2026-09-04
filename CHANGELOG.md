# Changelog

## 0.1.13
- Helligkeit, Kontrast und Sättigung korrigiert; die Bearbeitungsfunktionen wenden den gewählten Faktor jetzt tatsächlich auf das aktuelle Bild an.
- Änderungen werden als ungespeichert erkannt. Beim Öffnen eines anderen Bildes, beim Wechsel zum vorherigen/nächsten Bild oder beim Beenden wird gefragt, ob das bearbeitete Bild gespeichert werden soll.
- Speichern kann bestätigt, abgelehnt oder abgebrochen werden; bei „Abbrechen“ bleibt das aktuelle Bild geöffnet.
- Zuschneiden bleibt gegenüber v0.1.12 unverändert und funktioniert weiterhin korrekt.
- Versionsangaben auf v0.1.13 aktualisiert.


## 0.1.12
- Zuschneiden korrigiert: Die tatsächliche Position des Bildes im Canvas wird bei der Auswahl berücksichtigt.
- Der bisherige Versatz im Fit-Modus, durch den beim Zuschneiden auf der linken Seite Bildinhalt verloren gehen konnte, ist behoben.
- Die Zuschneideauswahl wird sicher auf den sichtbaren Bildbereich begrenzt.
- Versionsangaben in Programm, README und VERSION auf v0.1.12 aktualisiert; die PDF-Anleitung wurde auf v0.1.12 aktualisiert und passend umbenannt.

## 0.1.11
- Erste öffentliche GitHub-Release des Bildbetrachters.
- Miniaturbildleiste mit Dateiname, Bildabmessungen und Dateigröße.
- Bild wird beim Anklicken in der großen Hauptanzeige geöffnet.
- „Gespeicherten Bildordner laden“ übernimmt den gespeicherten Ordner direkt als aktuellen Ordner.
- „Bildinformationen“ erscheint nur nach ausdrücklichem Aufruf und kann geschlossen werden.
- Tastenkürzel und Symbolleiste für wichtige Funktionen.
- README vollständig überarbeitet, inklusive ausführlicher Windows- und Linux-Installation.
- Aktuelle PDF-Anleitung v0.1.11 mit Windows-/Linux-Installationshinweisen.
- Release-Paket bereinigt: nur aktuelle Projekt- und Dokumentationsdateien.

## 0.1.11 – Erste GitHub-Release-Version

- Miniaturbildleiste zeigt neben jeder Vorschau den Dateinamen, die Bildabmessungen und die Dateigröße.
- Klick auf ein Vorschaubild öffnet das Bild weiterhin ausschließlich in der großen Hauptanzeige.
- Klick auf die Angaben neben einer Vorschau öffnet ebenfalls das zugehörige Bild.
- Das Fenster „Bildinformationen...“ bleibt beim Start verborgen und erscheint nur nach ausdrücklichem Aufruf.
- Bildinformationen können über die Schließen-Schaltfläche oder `Esc` geschlossen werden.
- Das Informationsfenster aktualisiert sich beim Bildwechsel, solange es geöffnet ist.
- Die Seitenleiste ist breit genug für Ordneranzeige und gespeicherten Bildordner-Button.
- Moderne Symbolleiste mit sichtbaren Symbolen und Tastenkürzeln.
- Gespeicherter Bildordner kann direkt als aktueller Ordner im Programm geladen werden.
- README, integrierte Anleitung, PDF-Anleitung und Versionsdateien auf v0.1.11 aktualisiert.

## 0.1.10

- Das optionale Fenster „Bildinformationen“ kann über die Schließen-Schaltfläche geschlossen werden.
- `Esc` schließt das Informationsfenster; wenn es nicht geöffnet ist, verlässt `Esc` den Vollbildmodus.
- Beim Schließen bleibt das aktuell angezeigte Bild unverändert.

## 0.1.9

- Bildinformationen werden beim Programmstart und beim normalen Anklicken von Vorschaubildern nicht automatisch angezeigt.
- „Bildinformationen...“ wird ausschließlich über das Menü aufgerufen.
- Vorschaubilder öffnen weiterhin direkt die große Hauptanzeige.

## 0.1.8

- „Bildinformationen...“ als Informationsbereich innerhalb des Programms umgesetzt.
- Informationen werden beim Bildwechsel aktualisiert.

## 0.1.7

- Seitenleiste verbreitert.
- Moderne Symbole für die wichtigsten Funktionen ergänzt.

## 0.1.6

- Gespeicherter Bildordner wird direkt als aktueller Ordner im Programm geladen.
- Aktueller Ordner wird in der Seitenleiste angezeigt.

## 0.1.5

- Button zum Öffnen des gespeicherten Bildordners ergänzt.

## 0.1.4

- Tastenkürzel für wichtige Menüfunktionen ergänzt und im Menü sichtbar gemacht.

## 0.1.3

- Ordner- und Einstellungslogik verbessert.
- Letzter verwendeter Ordner wird gespeichert.
- Bildinformationen um Änderungsdatum und Uhrzeit ergänzt.

## 0.1.2

- Hell/Dunkel-Theme eingeführt.
- Theme-Auswahl unter Werkzeuge → Einstellungen.

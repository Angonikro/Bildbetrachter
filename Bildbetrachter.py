import json
import configparser
import os
import platform
import subprocess
import tkinter as tk
from pathlib import Path
from datetime import datetime
from tkinter import filedialog, messagebox, simpledialog, ttk

from PIL import Image, ImageEnhance, ImageFilter, ImageOps, ImageTk


APP_NAME = "Bildbetrachter"
APP_VERSION = "0.1.13"
SUPPORTED = {".bmp", ".gif", ".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}
SETTINGS_FILE = Path(__file__).resolve().parent / "settings.ini"
LEGACY_SETTINGS_FILE = Path.home() / ".bildbetrachter_settings.json"


class ImageViewerApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("1200x760")
        self.root.minsize(900, 600)

        self.image = None
        self.original_image = None
        self.image_path = None
        self.dirty = False
        self.photo = None
        # Position des angezeigten Bildes im Canvas. Wird für exakte
        # Koordinatenumrechnung beim Zuschneiden benötigt.
        self.image_display_x = 0
        self.image_display_y = 0
        self.zoom_factor = 1.0
        self.fit_mode = True
        self.history = []
        self.redo_history = []
        self.folder_images = []
        self.folder_index = -1
        self.thumbnails = []
        self.thumb_buttons = []
        self.status_var = tk.StringVar(value="Kein Bild geöffnet")
        self.zoom_var = tk.StringVar(value="100 %")
        self.lang = "de"
        self.settings = self.load_settings()
        self.theme = self.settings.get("theme", "dark")
        # Settings must be loaded before the startup folder is determined.
        self.current_folder = self.get_start_folder()

        self.build_style()
        self.build_menu()
        self.build_ui()
        self.bind_keys()
        self.load_language()
        self.update_ui()
        self.prepare_start_folder()

        if self.settings.get("geometry"):
            try:
                self.root.geometry(self.settings["geometry"])
            except tk.TclError:
                pass

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ---------- UI ----------

    def build_style(self):
        self.style = ttk.Style(self.root)
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass
        self.apply_theme()

    def apply_theme(self):
        """Apply the selected light/dark theme immediately to the whole UI."""
        dark = self.theme == "dark"
        if dark:
            colors = {
                "bg": "#202124", "surface": "#2b2d31", "surface2": "#303238",
                "fg": "#f1f3f4", "muted": "#b8bcc4", "border": "#4a4d53",
                "active": "#45474d", "canvas": "#18191c", "select": "#5b7cfa",
            }
        else:
            colors = {
                "bg": "#f2f4f7", "surface": "#ffffff", "surface2": "#e7ebf0",
                "fg": "#202124", "muted": "#5f6368", "border": "#c8cdd4",
                "active": "#dce3eb", "canvas": "#e8ebef", "select": "#4b6ee8",
            }
        self.colors = colors
        self.root.configure(bg=colors["bg"])
        self.root.option_add("*Font", "TkDefaultFont 10")
        self.root.option_add("*Menu.background", colors["surface"])
        self.root.option_add("*Menu.foreground", colors["fg"])
        self.root.option_add("*Menu.activeBackground", colors["active"])
        self.root.option_add("*Menu.activeForeground", colors["fg"])
        self.root.option_add("*Menu.borderWidth", 0)
        self.root.option_add("*TearOff", False)

        try:
            self.style.configure("TFrame", background=colors["bg"])
            self.style.configure("Toolbar.TFrame", background=colors["surface"], padding=7)
            self.style.configure("Tool.TButton", background=colors["surface2"], foreground=colors["fg"],
                                 borderwidth=0, padding=(10, 7), relief="flat")
            self.style.map("Tool.TButton", background=[("active", colors["active"]), ("pressed", colors["active"])],
                           foreground=[("disabled", colors["muted"])])
            self.style.configure("Sidebar.TFrame", background=colors["surface"], padding=7)
            self.style.configure("Title.TLabel", background=colors["surface"], foreground=colors["fg"],
                                 font=("TkDefaultFont", 11, "bold"))
            self.style.configure("ThumbInfo.TLabel", background=colors["surface"], foreground=colors["muted"],
                                 font=("TkDefaultFont", 9), justify="left")
            self.style.configure("ThumbName.TLabel", background=colors["surface"], foreground=colors["fg"],
                                 font=("TkDefaultFont", 9, "bold"), justify="left")
            self.style.configure("Status.TLabel", background=colors["surface"], foreground=colors["muted"],
                                 padding=(10, 5))
            self.style.configure("TLabel", background=colors["bg"], foreground=colors["fg"])
            self.style.configure("TButton", background=colors["surface2"], foreground=colors["fg"],
                                 borderwidth=0, padding=(9, 6))
            self.style.map("TButton", background=[("active", colors["active"]), ("pressed", colors["active"])])
            self.style.configure("TCombobox", fieldbackground=colors["surface"], background=colors["surface2"],
                                 foreground=colors["fg"], arrowcolor=colors["fg"])
            self.style.map("TCombobox", fieldbackground=[("readonly", colors["surface"])],
                           foreground=[("readonly", colors["fg"])])
            self.style.configure("TEntry", fieldbackground=colors["surface"], foreground=colors["fg"])
        except tk.TclError:
            pass

        for name in ("main", "content", "viewer_frame"):
            widget = getattr(self, name, None)
            if widget is not None:
                try:
                    widget.configure(style="TFrame")
                except tk.TclError:
                    pass
        if hasattr(self, "toolbar"):
            self.toolbar.configure(style="Toolbar.TFrame")
        if hasattr(self, "sidebar"):
            self.sidebar.configure(style="Sidebar.TFrame")
        if hasattr(self, "sidebar_title"):
            self.sidebar_title.configure(style="Title.TLabel")
        if hasattr(self, "status"):
            self.status.configure(style="Status.TLabel")
        if hasattr(self, "canvas"):
            self.canvas.configure(background=colors["canvas"])
        if hasattr(self, "thumb_canvas"):
            self.thumb_canvas.configure(background=colors["surface"])

    def setup_modern_style(self):
        """Modern, compact dark UI styling without changing editor behavior."""
        self.root.configure(bg="#202124")
        self.root.option_add("*Font", "TkDefaultFont 10")
        self.root.option_add("*Menu.background", "#2b2d31")
        self.root.option_add("*Menu.foreground", "#f1f3f4")
        self.root.option_add("*Menu.activeBackground", "#45474d")
        self.root.option_add("*Menu.activeForeground", "#ffffff")
        self.root.option_add("*TearOff", False)

        # ttk styling, when ttk widgets are present
        try:
            style = ttk.Style(self.root)
            style.theme_use("clam")
            style.configure(
                "Modern.TButton",
                background="#303238",
                foreground="#f1f3f4",
                borderwidth=0,
                padding=(10, 7),
                relief="flat",
            )
            style.map(
                "Modern.TButton",
                background=[("active", "#45474d"), ("pressed", "#55585f")],
                foreground=[("disabled", "#777a80")],
            )
            style.configure(
                "Modern.TFrame",
                background="#202124",
            )
            style.configure(
                "Modern.TLabel",
                background="#202124",
                foreground="#dfe1e5",
            )
        except Exception:
            pass

    def show_manual(self):
        de = self.lang == "de"
        dialog = tk.Toplevel(self.root)
        dialog.title("Anleitung" if de else "User Guide")
        dialog.transient(self.root)
        dialog.geometry("760x620")

        frame = tk.Frame(dialog, bg=self.colors["bg"], padx=12, pady=12)
        frame.pack(fill="both", expand=True)

        guide_de = """BILDBETRACHTER v0.1.12 – ANLEITUNG

1. Bilder öffnen
Über Datei → Öffnen wählst du ein Bild aus. Das Bild wird im Hauptfenster angezeigt.

2. Bilder speichern
Über Datei → Speichern bzw. Speichern unter kannst du das bearbeitete Bild sichern.
Beim Speichern unter wird das gewünschte Bildformat verwendet.

3. Größe ändern
Über Bild → Größe ändern kannst du Breite und Höhe exakt in Pixeln eingeben, zum Beispiel:
800 × 600
Die eingegebenen Werte werden direkt übernommen.

4. Bildbearbeitung
Die vorhandenen Bearbeitungsfunktionen stehen im Menü Bearbeiten bzw. Bild zur Verfügung.
Änderungen können – soweit von der jeweiligen Funktion unterstützt – rückgängig gemacht
und wiederholt werden.

5. Ansicht und Zoom
Die Ansicht kann über das Menü Ansicht angepasst werden. Der Zoom erleichtert das
Betrachten kleiner oder großer Bilder.

6. Diashow
Wenn die Diashow-Funktion vorhanden ist, kann sie über die entsprechenden Bedienelemente
gestartet und beendet werden. Das Intervall wird in den Einstellungen gespeichert.

7. Sprache
Unter den Spracheinstellungen kann zwischen Deutsch und English gewechselt werden.
Die Auswahl wird dauerhaft in settings.ini gespeichert.

8. Einstellungen
Alle dauerhaft gespeicherten Programmeinstellungen liegen in:
Bild/settings.ini
Dort werden unter anderem Sprache, Fenstergröße, Fensterstatus, Zoom, Diashow-Intervall
und der zuletzt verwendete Ordner sowie der festgelegte Bildordner gespeichert.

9. Bildordner
Unter Werkzeuge → Einstellungen kann ein fester Bildordner eingetragen oder über Durchsuchen ausgewählt werden.
Beim Start wird zuerst dieser Ordner verwendet. Ist er nicht vorhanden, wird der zuletzt verwendete Ordner genutzt;
ist auch dieser nicht vorhanden, wird der Programmordner Bild verwendet.

10. Theme / Darstellung
Unter Werkzeuge → Einstellungen kann zwischen Hell und Dunkel gewählt werden. Das Theme
wird sofort übernommen und dauerhaft in den Einstellungen gespeichert.

11. Desktop-Verknüpfung
Unter Linux kann install_desktop_launcher.sh verwendet werden, um eine Desktop-
Verknüpfung für den Bildbetrachter anzulegen.

12. Miniaturbilder und Bildinformationen
Neben den Miniaturbildern werden Dateiname, Bildabmessungen und Dateigröße angezeigt.
Ein Klick auf ein Vorschaubild öffnet es ausschließlich in der großen Hauptanzeige.
Das Fenster „Bildinformationen...“ erscheint nur nach ausdrücklichem Aufruf über Datei.
Es kann über die Schließen-Schaltfläche oder Esc geschlossen werden.

13. Installation
Benötigte Python-Abhängigkeiten werden über requirements.txt installiert:
python3 -m pip install -r requirements.txt

Danach kann das Programm mit folgendem Befehl gestartet werden:
python3 Bildbetrachter.py

Info
Bildbetrachter v0.1.12
By Goldisoft 2026
"""
        guide_en = """IMAGE VIEWER v0.1.12 – USER GUIDE

1. Opening images
Use File → Open to select an image. The image is displayed in the main window.

2. Saving images
Use File → Save or Save As to save the edited image. Save As lets you choose the
desired image format.

3. Resize
Use Image → Resize to enter an exact width and height in pixels, for example:
800 × 600
The entered values are applied directly.

4. Image editing
The available editing functions are provided in the Edit and Image menus.
Changes can be undone and redone where supported by the respective function.

5. View and zoom
Use the View menu to adjust the display. Zoom makes it easier to inspect small or large images.

6. Slideshow
If the slideshow function is available, it can be started and stopped using the corresponding
controls. The interval is stored in the settings.

7. Language
The language can be changed between German and English. The selection is stored permanently
in settings.ini.

8. Settings
All persistent application settings are stored in:
Bild/settings.ini
This includes language, window size, window state, zoom, slideshow interval and the last folder.

9. Theme / Appearance
Under Tools → Settings you can choose between Light and Dark. The theme is applied immediately
and stored permanently in the settings.

10. Desktop shortcut
On Linux, install_desktop_launcher.sh can be used to create a desktop shortcut.

11. Thumbnails and image information
The thumbnail list shows the filename, image dimensions and file size beside each preview.
Clicking a thumbnail opens the image only in the large main view.
The Image Information window appears only when explicitly requested from the File menu.
It can be closed with its close button or Esc.

12. Installation
Install the required Python dependencies with:
python3 -m pip install -r requirements.txt

Then start the application with:
python3 Bildbetrachter.py

About
Bildbetrachter v0.1.12
By Goldisoft 2026
"""
        text_box = tk.Text(frame, wrap="word", font=("TkDefaultFont", 10),
                           bg=self.colors["surface"], fg=self.colors["fg"],
                           insertbackground=self.colors["fg"], selectbackground=self.colors["select"],
                           relief="flat", padx=10, pady=10)
        text_box.pack(side="left", fill="both", expand=True)
        scroll = tk.Scrollbar(frame, command=text_box.yview,
                              bg=self.colors["surface2"], troughcolor=self.colors["bg"],
                              activebackground=self.colors["active"], relief="flat", bd=0)
        scroll.pack(side="right", fill="y")
        text_box.configure(yscrollcommand=scroll.set)
        text_box.insert("1.0", guide_de if de else guide_en)
        text_box.configure(state="disabled")
        dialog.bind("<Escape>", lambda _event: dialog.destroy())

    def show_about_dialog(self):
        de = self.lang == "de"
        dialog = tk.Toplevel(self.root)
        dialog.title("Info" if de else "About")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)

        frame = tk.Frame(dialog, bg=self.colors["bg"], padx=28, pady=24)
        frame.pack(fill="both", expand=True)

        tk.Label(
            frame,
            text=f"Bildbetrachter v0.1.12",
            font=("TkDefaultFont", 16, "bold"),
            bg=self.colors["bg"], fg=self.colors["fg"]
        ).pack(pady=(0, 10))

        tk.Label(
            frame,
            text="By Goldisoft 2026",
            font=("TkDefaultFont", 11),
            bg=self.colors["bg"], fg=self.colors["muted"]
        ).pack(pady=(0, 18))

        tk.Button(
            frame,
            text="OK",
            width=10,
            command=dialog.destroy
        ).pack()

        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{max(0, x)}+{max(0, y)}")
        dialog.bind("<Escape>", lambda _event: dialog.destroy())

    def build_menu(self):
        self.menubar = tk.Menu(self.root)

        self.file_menu = tk.Menu(self.menubar, tearoff=False)
        self.edit_menu = tk.Menu(self.menubar, tearoff=False)
        self.image_menu = tk.Menu(self.menubar, tearoff=False)
        self.view_menu = tk.Menu(self.menubar, tearoff=False)
        self.help_menu = tk.Menu(self.menubar, tearoff=False)

        self.menubar.add_cascade(label="Datei" if self.lang == "de" else "File",
                                 menu=self.file_menu)
        self.menubar.add_cascade(label="Bearbeiten" if self.lang == "de" else "Edit",
                                 menu=self.edit_menu)
        self.menubar.add_cascade(label="Bild" if self.lang == "de" else "Image",
                                 menu=self.image_menu)
        self.menubar.add_cascade(label="Ansicht" if self.lang == "de" else "View",
                                 menu=self.view_menu)
        self.menubar.add_cascade(label="Hilfe" if self.lang == "de" else "Help",
                                 menu=self.help_menu)

        self.help_menu.add_command(
            label="Anleitung" if self.lang == "de" else "User Guide",
            command=self.show_manual
        )
        self.help_menu.add_separator()
        self.help_menu.add_command(
            label="Info" if self.lang == "de" else "About",
            command=self.show_about_dialog
        )
        self.root.config(menu=self.menubar)


    def rebuild_menu(self):
        de = self.lang == "de"

        self.file_menu = tk.Menu(self.menubar, tearoff=0)
        self.edit_menu = tk.Menu(self.menubar, tearoff=0)
        self.view_menu = tk.Menu(self.menubar, tearoff=0)
        self.image_menu = tk.Menu(self.menubar, tearoff=0)
        self.tools_menu = tk.Menu(self.menubar, tearoff=0)
        self.help_menu = tk.Menu(self.menubar, tearoff=0)

        self.file_menu.add_command(
            label="Öffnen..." if de else "Open...", command=self.open_image, accelerator="Ctrl+O")
        self.file_menu.add_command(
            label="Speichern unter..." if de else "Save As...", command=self.save_image_as, accelerator="Ctrl+Shift+S")
        self.file_menu.add_command(
            label="Speichern" if de else "Save", command=self.save_image, accelerator="Ctrl+S")
        self.file_menu.add_command(
            label="Bildinformationen..." if de else "Image Information...",
            command=self.show_image_information)
        self.file_menu.add_separator()
        self.file_menu.add_command(
            label="Drucken" if de else "Print", command=self.print_image, accelerator="Ctrl+P")
        self.file_menu.add_command(
            label="Als Hintergrundbild setzen" if de else "Set as wallpaper",
            command=self.set_wallpaper)
        self.file_menu.add_separator()
        self.file_menu.add_command(
            label="Beenden" if de else "Exit", command=self.on_close, accelerator="Alt+F4")

        self.edit_menu.add_command(
            label="Rückgängig" if de else "Undo", command=self.undo, accelerator="Ctrl+Z")
        self.edit_menu.add_command(
            label="Wiederholen" if de else "Redo", command=self.redo, accelerator="Ctrl+Y")
        self.edit_menu.add_separator()
        self.edit_menu.add_command(
            label="Zuschneiden" if de else "Crop", command=self.start_crop_mode, accelerator="Ctrl+Shift+X")
        self.edit_menu.add_command(
            label="Größe ändern" if de else "Resize", command=self.resize_image_dialog, accelerator="Ctrl+E")

        self.view_menu.add_command(
            label="An Fenster anpassen" if de else "Fit to window", command=self.fit_to_window, accelerator="Ctrl+F")
        self.view_menu.add_command(
            label="100 %", command=self.zoom_100, accelerator="Ctrl+0")
        self.view_menu.add_command(
            label="Vergrößern" if de else "Zoom in", command=self.zoom_in, accelerator="+")
        self.view_menu.add_command(
            label="Verkleinern" if de else "Zoom out", command=self.zoom_out, accelerator="-")
        self.view_menu.add_command(
            label="Vollbild" if de else "Fullscreen", command=self.toggle_fullscreen, accelerator="F11")
        self.view_menu.add_separator()
        self.view_menu.add_command(
            label="Diashow starten" if de else "Start slideshow",
            command=self.start_slideshow, accelerator="F5")

        self.image_menu.add_command(
            label="90° links drehen" if de else "Rotate 90° left",
            command=lambda: self.rotate(-90), accelerator="Ctrl+L")
        self.image_menu.add_command(
            label="90° rechts drehen" if de else "Rotate 90° right",
            command=lambda: self.rotate(90), accelerator="Ctrl+R")
        self.image_menu.add_command(
            label="Horizontal spiegeln" if de else "Flip horizontal",
            command=self.mirror_horizontal, accelerator="Ctrl+H")
        self.image_menu.add_command(
            label="Vertikal spiegeln" if de else "Flip vertical",
            command=self.mirror_vertical, accelerator="Ctrl+Shift+H")
        self.image_menu.add_separator()
        self.image_menu.add_command(
            label="Graustufen" if de else "Grayscale", command=self.grayscale, accelerator="Ctrl+G")
        self.image_menu.add_command(
            label="Negativ" if de else "Invert", command=self.invert, accelerator="Ctrl+I")
        self.image_menu.add_command(
            label="Schwarzweiß" if de else "Black & white", command=self.black_white, accelerator="Ctrl+B")
        self.image_menu.add_command(
            label="Schärfen" if de else "Sharpen", command=self.sharpen, accelerator="Ctrl+K")
        self.image_menu.add_command(
            label="Weichzeichnen" if de else "Blur", command=self.blur, accelerator="Ctrl+Shift+B")

        self.tools_menu.add_command(
            label="Helligkeit..." if de else "Brightness...",
            command=self.adjust_brightness, accelerator="Ctrl+1")
        self.tools_menu.add_command(
            label="Kontrast..." if de else "Contrast...",
            command=self.adjust_contrast, accelerator="Ctrl+2")
        self.tools_menu.add_command(
            label="Sättigung..." if de else "Saturation...",
            command=self.adjust_saturation, accelerator="Ctrl+3")
        self.tools_menu.add_separator()
        self.tools_menu.add_command(
            label="Sprache: Deutsch" if de else "Language: German",
            command=lambda: self.set_language("de"))
        self.tools_menu.add_command(
            label="Sprache: English" if de else "Language: English",
            command=lambda: self.set_language("en"))
        self.tools_menu.add_command(
            label="Einstellungen" if de else "Settings",
            command=self.show_settings)

        self.help_menu.add_command(
            label="Anleitung" if de else "User Guide",
            command=self.show_manual)
        self.help_menu.add_separator()
        self.help_menu.add_command(
            label="Info" if de else "About",
            command=self.show_about_dialog)

        self.menubar.delete(0, "end")
        self.menubar.add_cascade(label="Datei" if de else "File", menu=self.file_menu)
        self.menubar.add_cascade(label="Bearbeiten" if de else "Edit", menu=self.edit_menu)
        self.menubar.add_cascade(label="Ansicht" if de else "View", menu=self.view_menu)
        self.menubar.add_cascade(label="Bild" if de else "Image", menu=self.image_menu)
        self.menubar.add_cascade(label="Werkzeuge" if de else "Tools", menu=self.tools_menu)
        self.menubar.add_cascade(label="Hilfe" if de else "Help", menu=self.help_menu)

    def _make_toolbar_icons(self):
        """Create compact toolbar icons that work on Linux and Windows without external assets."""
        from PIL import ImageDraw

        size = 34
        fg = (235, 238, 242, 255)
        blue = (70, 150, 235, 255)
        yellow = (245, 193, 62, 255)
        green = (83, 185, 110, 255)

        def icon(kind):
            im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            d = ImageDraw.Draw(im)
            if kind == "open":
                d.rounded_rectangle((4, 9, 30, 28), radius=3, fill=yellow, outline=fg, width=1)
                d.polygon([(5, 9), (12, 9), (15, 13), (30, 13), (30, 28), (4, 28)], fill=yellow, outline=fg)
            elif kind == "save":
                d.rounded_rectangle((6, 4, 28, 30), radius=2, fill=blue, outline=fg, width=1)
                d.rectangle((10, 5, 24, 12), fill=(225, 232, 240, 255))
                d.rectangle((10, 18, 24, 28), fill=green, outline=fg)
                d.rectangle((13, 7, 21, 11), fill=(60, 70, 80, 255))
            elif kind == "undo":
                d.arc((7, 7, 29, 29), 45, 285, fill=fg, width=3)
                d.polygon([(7, 14), (7, 6), (15, 10)], fill=fg)
            elif kind == "redo":
                d.arc((5, 7, 27, 29), 255, 135, fill=fg, width=3)
                d.polygon([(27, 14), (27, 6), (19, 10)], fill=fg)
            elif kind in ("left", "right"):
                if kind == "left":
                    d.arc((5, 6, 29, 30), 65, 285, fill=fg, width=3)
                    d.polygon([(7, 16), (13, 10), (14, 18)], fill=fg)
                else:
                    d.arc((5, 6, 29, 30), 255, 115, fill=fg, width=3)
                    d.polygon([(27, 16), (21, 10), (20, 18)], fill=fg)
            elif kind == "mirror_h":
                d.line((5, 17, 29, 17), fill=fg, width=2)
                d.polygon([(5,17),(11,11),(11,23)], fill=fg)
                d.polygon([(29,17),(23,11),(23,23)], fill=fg)
            elif kind == "mirror_v":
                d.line((17, 5, 17, 29), fill=fg, width=2)
                d.polygon([(17,5),(11,11),(23,11)], fill=fg)
                d.polygon([(17,29),(11,23),(23,23)], fill=fg)
            elif kind == "fit":
                d.line((6, 12, 6, 6, 12, 6), fill=fg, width=2)
                d.line((22, 6, 28, 6, 28, 12), fill=fg, width=2)
                d.line((6, 22, 6, 28, 12, 28), fill=fg, width=2)
                d.line((22, 28, 28, 28, 28, 22), fill=fg, width=2)
                d.line((12, 17, 22, 17), fill=fg, width=2)
                d.line((17, 12, 17, 22), fill=fg, width=2)
            elif kind == "zoom_out":
                d.ellipse((5, 5, 24, 24), outline=fg, width=3)
                d.line((20, 20, 29, 29), fill=fg, width=3)
                d.line((10, 15, 19, 15), fill=fg, width=2)
            elif kind == "zoom_in":
                d.ellipse((5, 5, 24, 24), outline=fg, width=3)
                d.line((20, 20, 29, 29), fill=fg, width=3)
                d.line((10, 15, 19, 15), fill=fg, width=2)
                d.line((14, 10, 14, 20), fill=fg, width=2)
            elif kind == "fullscreen":
                d.line((5,12,5,5,12,5), fill=fg, width=2)
                d.line((22,5,29,5,29,12), fill=fg, width=2)
                d.line((5,22,5,29,12,29), fill=fg, width=2)
                d.line((22,29,29,29,29,22), fill=fg, width=2)
            return ImageTk.PhotoImage(im)

        kinds = ["open", "save", "undo", "redo", "left", "right", "mirror_h", "mirror_v", "fit", "zoom_out", "zoom_in", "fullscreen"]
        self.toolbar_icons = {k: icon(k) for k in kinds}
        self.toolbar_icons["folder"] = self.toolbar_icons["open"]
        return self.toolbar_icons

    def build_ui(self):
        self.main = ttk.Frame(self.root)
        self.main.pack(fill="both", expand=True)

        self.toolbar = ttk.Frame(self.main, style="Toolbar.TFrame")
        self.toolbar.pack(fill="x")
        self._make_toolbar_icons()

        self.btn_open = ttk.Button(self.toolbar, style="Tool.TButton", command=self.open_image, image=self.toolbar_icons["open"], compound="top")
        self.btn_save = ttk.Button(self.toolbar, style="Tool.TButton", command=self.save_image_as, image=self.toolbar_icons["save"], compound="top")
        self.btn_undo = ttk.Button(self.toolbar, style="Tool.TButton", command=self.undo, image=self.toolbar_icons["undo"], compound="top")
        self.btn_redo = ttk.Button(self.toolbar, style="Tool.TButton", command=self.redo, image=self.toolbar_icons["redo"], compound="top")
        self.btn_left = ttk.Button(self.toolbar, style="Tool.TButton", command=lambda: self.rotate(-90), image=self.toolbar_icons["left"], compound="top")
        self.btn_right = ttk.Button(self.toolbar, style="Tool.TButton", command=lambda: self.rotate(90), image=self.toolbar_icons["right"], compound="top")
        self.btn_mirror_h = ttk.Button(self.toolbar, style="Tool.TButton", command=self.mirror_horizontal, image=self.toolbar_icons["mirror_h"], compound="top")
        self.btn_mirror_v = ttk.Button(self.toolbar, style="Tool.TButton", command=self.mirror_vertical, image=self.toolbar_icons["mirror_v"], compound="top")
        self.btn_fit = ttk.Button(self.toolbar, style="Tool.TButton", command=self.fit_to_window, image=self.toolbar_icons["fit"], compound="top")
        self.btn_100 = ttk.Button(self.toolbar, style="Tool.TButton", command=self.zoom_100, text="100 %", image=self.toolbar_icons["zoom_in"], compound="top")
        self.btn_full = ttk.Button(self.toolbar, style="Tool.TButton", command=self.toggle_fullscreen, image=self.toolbar_icons["fullscreen"], compound="top")

        for b in (
            self.btn_open, self.btn_save, self.btn_undo, self.btn_redo,
            self.btn_left, self.btn_right, self.btn_mirror_h, self.btn_mirror_v,
            self.btn_fit, self.btn_100, self.btn_full
        ):
            b.pack(side="left", padx=2, ipadx=8, ipady=3)

        self.content = ttk.Frame(self.main)
        self.content.pack(fill="both", expand=True)

        self.sidebar = ttk.Frame(self.content, width=320, style="Sidebar.TFrame")
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        self.sidebar_title = ttk.Label(self.sidebar, style="Title.TLabel")
        self.sidebar_title.pack(fill="x", pady=(0, 2))

        self.current_folder_var = tk.StringVar(value="")
        self.current_folder_label = ttk.Label(
            self.sidebar, textvariable=self.current_folder_var,
            style="Status.TLabel", justify="left", anchor="w",
            wraplength=295
        )
        self.current_folder_label.pack(fill="x", pady=(0, 5))

        self.btn_open_image_folder = ttk.Button(
            self.sidebar, style="Tool.TButton",
            command=self.load_configured_image_folder,
            image=self.toolbar_icons["folder"], compound="left"
        )
        self.btn_open_image_folder.pack(fill="x", padx=6, pady=(0, 8))

        self.thumb_canvas = tk.Canvas(self.sidebar, highlightthickness=0)
        self.thumb_scroll = ttk.Scrollbar(self.sidebar, orient="vertical", command=self.thumb_canvas.yview)
        self.thumb_canvas.configure(yscrollcommand=self.thumb_scroll.set)
        self.thumb_canvas.pack(side="left", fill="both", expand=True)
        self.thumb_scroll.pack(side="right", fill="y")

        self.thumb_frame = ttk.Frame(self.thumb_canvas)
        self.thumb_window = self.thumb_canvas.create_window((0, 0), window=self.thumb_frame, anchor="nw")
        self.thumb_frame.bind(
            "<Configure>",
            lambda e: self.thumb_canvas.configure(scrollregion=self.thumb_canvas.bbox("all"))
        )
        self.thumb_canvas.bind(
            "<Configure>",
            lambda e: self.thumb_canvas.itemconfigure(self.thumb_window, width=e.width)
        )

        # Mausrad für die komplette Miniaturbild-Leiste aktivieren.
        # Die Bindings werden auch an die Vorschau-Buttons gesetzt, damit
        # das Scrollen funktioniert, wenn der Mauszeiger direkt über einem Bild steht.
        def _scroll_thumbnails(event):
            if getattr(event, "num", None) == 4:
                self.thumb_canvas.yview_scroll(-3, "units")
            elif getattr(event, "num", None) == 5:
                self.thumb_canvas.yview_scroll(3, "units")
            elif getattr(event, "delta", 0):
                # Windows/macOS: delta ist ein Vielfaches von 120.
                steps = int(-event.delta / 120)
                if steps == 0:
                    steps = -1 if event.delta > 0 else 1
                self.thumb_canvas.yview_scroll(steps, "units")
            return "break"

        self.thumb_canvas.bind("<MouseWheel>", _scroll_thumbnails)
        self.thumb_canvas.bind("<Button-4>", _scroll_thumbnails)
        self.thumb_canvas.bind("<Button-5>", _scroll_thumbnails)
        self.thumb_frame.bind("<MouseWheel>", _scroll_thumbnails)
        self.thumb_frame.bind("<Button-4>", _scroll_thumbnails)
        self.thumb_frame.bind("<Button-5>", _scroll_thumbnails)

        self._scroll_thumbnails = _scroll_thumbnails

        # Informationsbereich: standardmäßig verborgen. Er wird nur über
        # Datei → Bildinformationen eingeblendet und bleibt anschließend
        # sichtbar, auch wenn ein anderes Vorschaubild angeklickt wird.
        self.info_panel = ttk.Frame(self.content, width=315, style="Sidebar.TFrame")
        self.info_panel.pack_propagate(False)
        self.info_panel_visible = False

        self.info_header = ttk.Frame(self.info_panel, style="Sidebar.TFrame")
        self.info_header.pack(fill="x", pady=(2, 8))
        self.info_title = ttk.Label(
            self.info_header, text="Bildinformationen", style="Title.TLabel"
        )
        self.info_title.pack(side="left", fill="x", expand=True)
        self.info_close_button = ttk.Button(
            self.info_header, text="✕", width=3, command=self.hide_image_information
        )
        self.info_close_button.pack(side="right")

        self.info_body = tk.Text(
            self.info_panel, wrap="word", state="disabled",
            bg=self.colors["surface"], fg=self.colors["fg"],
            insertbackground=self.colors["fg"], relief="flat",
            padx=12, pady=10, font=("TkDefaultFont", 10)
        )
        self.info_body.pack(fill="both", expand=True)

        self.viewer_frame = ttk.Frame(self.content)
        self.viewer_frame.pack(side="left", fill="both", expand=True)

        self.canvas = tk.Canvas(self.viewer_frame, background="#252525", highlightthickness=0)
        self.hbar = ttk.Scrollbar(self.viewer_frame, orient="horizontal", command=self.canvas.xview)
        self.vbar = ttk.Scrollbar(self.viewer_frame, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=self.hbar.set, yscrollcommand=self.vbar.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.vbar.grid(row=0, column=1, sticky="ns")
        self.hbar.grid(row=1, column=0, sticky="ew")
        self.viewer_frame.rowconfigure(0, weight=1)
        self.viewer_frame.columnconfigure(0, weight=1)

        self.status = ttk.Label(self.main, textvariable=self.status_var, style="Status.TLabel", anchor="w")
        self.status.pack(fill="x")

        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        self.canvas.bind("<Button-4>", self.on_mouse_wheel)
        self.canvas.bind("<Button-5>", self.on_mouse_wheel)
        self.canvas.bind("<ButtonPress-1>", self.pan_start)
        self.canvas.bind("<B1-Motion>", self.pan_move)

        self.crop_start = None
        self.crop_rect = None

    def bind_keys(self):
        # Tastenkürzel der Menüpunkte. Die gleichen Kürzel werden zusätzlich
        # über ``accelerator`` im Menü sichtbar angezeigt.
        bindings = {
            "<Control-o>": self.open_image,
            "<Control-Shift-s>": self.save_image_as,
            "<Control-s>": self.save_image,
            "<Control-p>": self.print_image,
            "<Control-z>": self.undo,
            "<Control-y>": self.redo,
            "<Control-Shift-z>": self.redo,
            "<Control-Shift-x>": self.start_crop_mode,
            "<Control-e>": self.resize_image_dialog,
            "<Control-f>": self.fit_to_window,
            "<Control-Key-0>": self.zoom_100,
            "<Control-r>": lambda: self.rotate(90),
            "<Control-l>": lambda: self.rotate(-90),
            "<Control-h>": self.mirror_horizontal,
            "<Control-Shift-h>": self.mirror_vertical,
            "<Control-g>": self.grayscale,
            "<Control-i>": self.invert,
            "<Control-b>": self.black_white,
            "<Control-k>": self.sharpen,
            "<Control-Shift-b>": self.blur,
            "<Control-Key-1>": self.adjust_brightness,
            "<Control-Key-2>": self.adjust_contrast,
            "<Control-Key-3>": self.adjust_saturation,
            "<F5>": self.start_slideshow,
            "<plus>": self.zoom_in,
            "<equal>": self.zoom_in,
            "<minus>": self.zoom_out,
            "<Escape>": self.handle_escape,
            "<Left>": self.previous_image,
            "<Right>": self.next_image,
            "<F11>": self.toggle_fullscreen,
        }
        for sequence, command in bindings.items():
            self.root.bind(sequence, lambda e, cmd=command: cmd())

    def handle_escape(self):
        """Close image information first; otherwise leave fullscreen mode."""
        if getattr(self, "info_panel_visible", False):
            self.hide_image_information()
        else:
            self.exit_fullscreen()

    # ---------- Language ----------

    def load_language(self):
        self.settings = self.load_settings()
        self.lang = self.settings.get("language", "de")
        self.theme = self.settings.get("theme", "dark")
        try:
            self.root.geometry(
                f'{self.settings["window_width"]}x{self.settings["window_height"]}'
            )
            if self.settings.get("maximized"):
                self.root.state("zoomed")
        except Exception:
            pass
        self.zoom = self.settings.get("zoom", 100)
        self.slideshow_interval = self.settings.get("slideshow_interval", 3)
        self.retranslate()

    def retranslate(self):
        de = self.lang == "de"

        self.root.title("Bildbetrachter" if de else "Image Viewer")
        self.rebuild_menu()
        self.apply_theme()

        self.btn_open.configure(text="Öffnen" if de else "Open")
        self.btn_save.configure(text="Speichern" if de else "Save")
        self.btn_undo.configure(text="Rückgängig" if de else "Undo")
        self.btn_redo.configure(text="Wiederholen" if de else "Redo")
        self.btn_left.configure(text="Links drehen" if de else "Rotate left")
        self.btn_right.configure(text="Rechts drehen" if de else "Rotate right")
        self.btn_mirror_h.configure(text="Horizontal" if de else "Horizontal")
        self.btn_mirror_v.configure(text="Vertikal" if de else "Vertical")
        self.btn_fit.configure(text="Anpassen" if de else "Fit")
        self.btn_100.configure(text="100 %")
        self.btn_full.configure(text="Vollbild" if de else "Fullscreen")
        if hasattr(self, "info_title"):
            self.info_title.configure(text="Bildinformationen" if de else "Image Information")
        if hasattr(self, "info_close_button"):
            self.info_close_button.configure(text="✕")
        self.sidebar_title.configure(
            text="Bilder im Ordner" if de else "Folder images"
        )
        self.btn_open_image_folder.configure(
            text="📂 Gespeicherten Bildordner laden" if de else "📂 Load saved image folder"
        )
        self.update_current_folder_display()

        self.update_ui()

    def set_language(self, language):
        self.lang = "en" if language == "en" else "de"
        self.save_settings()
        self.retranslate()


    def get_start_folder(self):
        """Return the startup folder: last used, configured image folder, then app folder."""
        last = str(self.settings.get("last_folder", "")).strip()
        configured = str(self.settings.get("image_folder", "")).strip()

        # The last actually used folder always has priority.
        # If it no longer exists, fall back to the configured image folder.
        # If that also fails, use the program's Bild folder.
        candidates = [last, configured, str(Path(__file__).resolve().parent)]

        for value in candidates:
            if value:
                folder = Path(value).expanduser()
                if folder.is_dir():
                    return folder

        return Path(__file__).resolve().parent

    def prepare_start_folder(self):
        """Remember and display the folder used at startup without forcing an image open."""
        folder = self.get_start_folder()
        self.current_folder = folder
        self.load_folder_images(folder)
        self.settings["last_folder"] = str(folder)
        self.save_settings()

    def open_image(self):
        filetypes = [
            ("Bilddateien", "*.bmp *.gif *.jpg *.jpeg *.png *.webp *.tif *.tiff"),
            ("Alle Dateien", "*.*"),
        ]
        initialdir = self.get_start_folder()
        path = filedialog.askopenfilename(
            title="Bild öffnen" if self.lang == "de" else "Open image",
            initialdir=str(initialdir),
            filetypes=filetypes,
        )
        if not path:
            return
        self.load_image(path)

    def load_image(self, path, add_history=False):
        if not self.confirm_unsaved_changes():
            return False
        try:
            img = Image.open(path).convert("RGBA")
            if add_history and self.image is not None:
                self.push_history()
            self.image = img
            self.original_image = img.copy()
            self.image_path = str(path)
            self.dirty = False
            self.current_folder = Path(path).parent
            self.settings["last_folder"] = str(self.current_folder)
            self.save_settings()
            self.zoom_factor = 1.0
            self.fit_mode = True
            self.history.clear()
            self.redo_history.clear()
            self.load_folder_images(Path(path).parent)
            self.folder_index = self.folder_images.index(str(path)) if str(path) in self.folder_images else -1
            self.show_image()
            if getattr(self, "info_panel_visible", False):
                self.update_image_information_panel()
            self.update_ui()
            return True
        except Exception as exc:
            messagebox.showerror(
                "Fehler" if self.lang == "de" else "Error",
                f"Bild konnte nicht geöffnet werden:\n{exc}",
            )
            return False

    def save_image(self):
        if self.image is None:
            self.info_no_image()
            return False
        if not self.image_path:
            return self.save_image_as()
        return self.save_to_path(self.image_path)

    def save_image_as(self):
        if self.image is None:
            self.info_no_image()
            return False

        path = filedialog.asksaveasfilename(
            title="Bild speichern unter" if self.lang == "de" else "Save image as",
            filetypes=[
                ("PNG", "*.png"),
                ("JPEG", "*.jpg"),
                ("JPEG", "*.jpeg"),
                ("BMP", "*.bmp"),
                ("GIF", "*.gif"),
                ("WebP", "*.webp"),
                ("TIFF", "*.tif"),
                ("TIFF", "*.tiff"),
            ],
        )
        if not path:
            return False

        ext = Path(path).suffix.lower()
        if not ext:
            ext = ".png"
            path += ext

        return self.save_to_path(path)

    def save_to_path(self, path):
        try:
            ext = Path(path).suffix.lower()
            image = self.image
            if ext in (".jpg", ".jpeg"):
                image.convert("RGB").save(path, "JPEG", quality=95)
            elif ext == ".bmp":
                image.convert("RGB").save(path, "BMP")
            elif ext == ".gif":
                image.convert("RGB").save(path, "GIF")
            elif ext == ".webp":
                image.save(path, "WEBP", quality=95)
            elif ext in (".tif", ".tiff"):
                image.save(path, "TIFF")
            elif ext == ".png":
                image.save(path, "PNG")
            else:
                raise ValueError(f"Nicht unterstütztes Format: {ext}")

            self.image_path = str(path)
            self.dirty = False
            self.status_var.set(
                ("Gespeichert: " if self.lang == "de" else "Saved: ") + str(path)
            )
            return True
        except Exception as exc:
            messagebox.showerror(
                "Fehler" if self.lang == "de" else "Error",
                f"Bild konnte nicht gespeichert werden:\n{exc}",
            )
            return False

    def confirm_unsaved_changes(self):
        """Ask whether unsaved edits should be saved before leaving the image."""
        if not self.dirty or self.image is None:
            return True

        de = self.lang == "de"
        answer = messagebox.askyesnocancel(
            "Bild geändert" if de else "Image changed",
            "Das Bild wurde verändert. Soll es gespeichert werden?" if de
            else "The image has been changed. Do you want to save it?",
            parent=self.root,
        )
        if answer is True:
            return self.save_image()
        if answer is False:
            return True
        return False

    def load_configured_image_folder(self):
        """Make the folder saved in Settings the active folder inside the program."""
        configured = str(self.settings.get("image_folder", "")).strip()
        de = self.lang == "de"

        if not configured:
            messagebox.showinfo(
                "Bildordner" if de else "Image folder",
                "Unter Einstellungen ist noch kein Bildordner festgelegt." if de else
                "No image folder has been configured in Settings yet."
            )
            return

        folder = Path(configured).expanduser()
        if not folder.is_dir():
            messagebox.showwarning(
                "Ordner nicht gefunden" if de else "Folder not found",
                "Der in den Einstellungen gespeicherte Bildordner existiert nicht mehr." if de else
                "The image folder saved in Settings no longer exists."
            )
            return

        folder = folder.resolve()
        self.current_folder = folder
        self.settings["last_folder"] = str(folder)
        self.save_settings()
        self.load_folder_images(folder)

        # Keep the currently displayed image, but make the selected folder the
        # active navigation folder. If the image belongs to it, select it.
        if self.image_path and Path(self.image_path).parent.resolve() == folder:
            image_path = str(Path(self.image_path).resolve())
            self.folder_index = self.folder_images.index(image_path) if image_path in self.folder_images else -1
        else:
            self.folder_index = -1

        self.update_current_folder_display()
        self.status_var.set(
            (f"Aktueller Bildordner: {folder}" if de else f"Current image folder: {folder}")
        )

    def update_current_folder_display(self):
        folder = getattr(self, "current_folder", None)
        if not hasattr(self, "current_folder_var"):
            return
        de = self.lang == "de"
        if folder:
            self.current_folder_var.set(
                ("Aktueller Ordner:\n" if de else "Current folder:\n") + str(folder)
            )
        else:
            self.current_folder_var.set(
                "Kein Ordner" if de else "No folder"
            )

    def load_folder_images(self, folder):
        try:
            self.folder_images = sorted(
                str(p) for p in folder.iterdir()
                if p.is_file() and p.suffix.lower() in SUPPORTED
            )
        except OSError:
            self.folder_images = []
        self.build_thumbnails()

    # ---------- History ----------

    def push_history(self):
        if self.image is not None:
            self.history.append(self.image.copy())
            if len(self.history) > 30:
                self.history.pop(0)
            self.redo_history.clear()

    def apply_edit(self, new_image):
        if self.image is None:
            return
        self.push_history()
        self.image = new_image.convert("RGBA")
        self.dirty = True
        self.zoom_factor = 1.0
        self.fit_mode = True
        self.show_image()
        self.update_ui()

    def undo(self):
        if not self.history or self.image is None:
            return
        self.redo_history.append(self.image.copy())
        self.image = self.history.pop()
        self.dirty = True
        self.zoom_factor = 1.0
        self.fit_mode = True
        self.show_image()
        self.update_ui()

    def redo(self):
        if not self.redo_history or self.image is None:
            return
        self.history.append(self.image.copy())
        self.image = self.redo_history.pop()
        self.dirty = True
        self.zoom_factor = 1.0
        self.fit_mode = True
        self.show_image()
        self.update_ui()

    # ---------- Display ----------

    def show_image(self):
        if self.image is None:
            self.canvas.delete("all")
            self.image_display_x = 0
            self.image_display_y = 0
            return

        w, h = self.image.size
        new_w = max(1, int(w * self.zoom_factor))
        new_h = max(1, int(h * self.zoom_factor))
        resized = self.image.resize((new_w, new_h), Image.Resampling.LANCZOS)
        self.photo = ImageTk.PhotoImage(resized)

        self.canvas.delete("all")
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        x = max(0, (cw - new_w) // 2) if self.fit_mode and cw > new_w else 0
        y = max(0, (ch - new_h) // 2) if self.fit_mode and ch > new_h else 0
        # Merken, wo das Bild tatsächlich im Canvas beginnt. Das ist wichtig,
        # weil das Bild im Fit-Modus mittig stehen kann.
        self.image_display_x = x
        self.image_display_y = y
        self.canvas.create_image(x, y, anchor="nw", image=self.photo)
        self.canvas.configure(scrollregion=(0, 0, max(cw, new_w), max(ch, new_h)))
        self.zoom_var.set(f"{round(self.zoom_factor * 100)} %")

    def fit_to_window(self):
        if self.image is None:
            return
        self.root.update_idletasks()
        cw = max(1, self.canvas.winfo_width() - 10)
        ch = max(1, self.canvas.winfo_height() - 10)
        iw, ih = self.image.size
        self.zoom_factor = min(cw / iw, ch / ih)
        self.zoom_factor = max(0.01, min(self.zoom_factor, 10))
        self.fit_mode = True
        self.show_image()

    def zoom_100(self):
        if self.image is None:
            return
        self.zoom_factor = 1.0
        self.fit_mode = False
        self.show_image()

    def zoom_in(self):
        if self.image is None:
            return
        self.zoom_factor = min(10.0, self.zoom_factor * 1.2)
        self.fit_mode = False
        self.show_image()

    def zoom_out(self):
        if self.image is None:
            return
        self.zoom_factor = max(0.01, self.zoom_factor / 1.2)
        self.fit_mode = False
        self.show_image()

    def on_mouse_wheel(self, event):
        delta = event.delta if hasattr(event, "delta") and event.delta else (120 if event.num == 4 else -120)
        if delta > 0:
            self.zoom_in()
        else:
            self.zoom_out()

    def pan_start(self, event):
        self.canvas.scan_mark(event.x, event.y)

    def pan_move(self, event):
        self.canvas.scan_dragto(event.x, event.y, gain=1)

    # ---------- Crop ----------

    def start_crop_mode(self):
        if self.image is None:
            self.info_no_image()
            return
        messagebox.showinfo(
            "Zuschneiden" if self.lang == "de" else "Crop",
            "Ziehe mit der linken Maustaste einen Bereich auf dem Bild auf."
            if self.lang == "de"
            else "Drag a rectangle over the image with the left mouse button.",
        )
        self.canvas.bind("<ButtonPress-1>", self.crop_start_event)
        self.canvas.bind("<B1-Motion>", self.crop_move_event)
        self.canvas.bind("<ButtonRelease-1>", self.crop_finish_event)

    def crop_start_event(self, event):
        self.crop_start = (self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))
        if self.crop_rect:
            self.canvas.delete(self.crop_rect)
        self.crop_rect = self.canvas.create_rectangle(
            *self.crop_start, *self.crop_start, outline="red", width=2
        )

    def crop_move_event(self, event):
        if not self.crop_start:
            return
        x0, y0 = self.crop_start
        x1, y1 = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        self.canvas.coords(self.crop_rect, x0, y0, x1, y1)

    def crop_finish_event(self, event):
        if not self.crop_start or self.image is None:
            return

        # Canvas-Koordinaten in Bild-Koordinaten umrechnen.
        # Wichtig: Im Fit-Modus kann das Bild innerhalb des Canvas zentriert
        # sein. Deshalb müssen image_display_x/y vor der Zoom-Umrechnung
        # abgezogen werden. Genau hier entstand bisher das Abschneiden links.
        x0, y0 = self.crop_start
        x1, y1 = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)

        display_left = self.image_display_x
        display_top = self.image_display_y
        display_right = display_left + self.image.width * self.zoom_factor
        display_bottom = display_top + self.image.height * self.zoom_factor

        # Auswahl auf den tatsächlich sichtbaren Bildbereich begrenzen.
        x0 = min(max(x0, display_left), display_right)
        x1 = min(max(x1, display_left), display_right)
        y0 = min(max(y0, display_top), display_bottom)
        y1 = min(max(y1, display_top), display_bottom)

        left, right = sorted((x0, x1))
        top, bottom = sorted((y0, y1))

        left = max(0, min(self.image.width, int((left - display_left) / self.zoom_factor)))
        top = max(0, min(self.image.height, int((top - display_top) / self.zoom_factor)))
        right = max(0, min(self.image.width, int((right - display_left) / self.zoom_factor)))
        bottom = max(0, min(self.image.height, int((bottom - display_top) / self.zoom_factor)))

        if right > left and bottom > top:
            self.apply_edit(self.image.crop((left, top, right, bottom)))

        self.crop_start = None
        if self.crop_rect:
            self.canvas.delete(self.crop_rect)
            self.crop_rect = None
        self.canvas.bind("<ButtonPress-1>", self.pan_start)
        self.canvas.bind("<B1-Motion>", self.pan_move)
        self.canvas.unbind("<ButtonRelease-1>")

    # ---------- Image operations ----------

    def rotate(self, degrees):
        if self.image is not None:
            self.apply_edit(self.image.rotate(-degrees, expand=True))

    def mirror_horizontal(self):
        if self.image is not None:
            self.apply_edit(ImageOps.mirror(self.image))

    def mirror_vertical(self):
        if self.image is not None:
            self.apply_edit(ImageOps.flip(self.image))

    def resize_image_dialog(self):
        """Dialog für eine frei wählbare exakte Bildgröße in Pixeln."""
        if self.image is None:
            self.info_no_image()
            return

        de = self.lang == "de"
        w, h = self.image.size

        dialog = tk.Toplevel(self.root)
        dialog.title("Größe ändern" if de else "Resize")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)

        frame = tk.Frame(dialog, padx=18, pady=16)
        frame.pack(fill="both", expand=True)

        tk.Label(
            frame,
            text=("Exakte Größe in Pixeln" if de else "Exact size in pixels"),
            font=("TkDefaultFont", 11, "bold"),
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 12))

        tk.Label(frame, text="Breite:" if de else "Width:").grid(
            row=1, column=0, sticky="e", padx=(0, 6), pady=4
        )
        width_var = tk.StringVar(value=str(w))
        width_entry = tk.Entry(frame, textvariable=width_var, width=10, justify="center")
        width_entry.grid(row=1, column=1, sticky="w", pady=4)
        tk.Label(frame, text="px").grid(row=1, column=2, sticky="w", padx=(5, 0))

        tk.Label(frame, text="Höhe:" if de else "Height:").grid(
            row=2, column=0, sticky="e", padx=(0, 6), pady=4
        )
        height_var = tk.StringVar(value=str(h))
        height_entry = tk.Entry(frame, textvariable=height_var, width=10, justify="center")
        height_entry.grid(row=2, column=1, sticky="w", pady=4)
        tk.Label(frame, text="px").grid(row=2, column=2, sticky="w", padx=(5, 0))

        tk.Label(
            frame,
            text=(f"Aktuell: {w} × {h} Pixel" if de else f"Current: {w} × {h} pixels"),
            fg="gray",
        ).grid(row=3, column=0, columnspan=3, sticky="w", pady=(8, 4))

        def apply_resize():
            try:
                new_w = int(width_var.get().strip())
                new_h = int(height_var.get().strip())
                if not (1 <= new_w <= 20000 and 1 <= new_h <= 20000):
                    raise ValueError
            except ValueError:
                messagebox.showerror(
                    "Ungültige Größe" if de else "Invalid size",
                    ("Bitte gültige positive Pixelwerte eingeben."
                     if de else "Please enter valid positive pixel values."),
                    parent=dialog,
                )
                return

            self.apply_edit(
                self.image.resize((new_w, new_h), Image.Resampling.LANCZOS)
            )
            dialog.destroy()

        buttons = tk.Frame(frame)
        buttons.grid(row=4, column=0, columnspan=3, sticky="e", pady=(14, 0))

        tk.Button(
            buttons,
            text="Abbrechen" if de else "Cancel",
            command=dialog.destroy,
        ).pack(side="right", padx=(8, 0))

        tk.Button(
            buttons,
            text="Ändern" if de else "Resize",
            command=apply_resize,
        ).pack(side="right")

        width_entry.focus_set()
        width_entry.select_range(0, "end")
        dialog.bind("<Return>", lambda _event: apply_resize())
        dialog.bind("<Escape>", lambda _event: dialog.destroy())

    def adjust(self, title_de, title_en, prompt_de, prompt_en, func):
        if self.image is None:
            self.info_no_image()
            return
        value = simpledialog.askfloat(
            title_de if self.lang == "de" else title_en,
            prompt_de if self.lang == "de" else prompt_en,
            initialvalue=1.0,
            minvalue=0.0,
            maxvalue=3.0,
        )
        if value is not None:
            self.apply_edit(func(value))

    def adjust_brightness(self):
        self.adjust("Helligkeit", "Brightness", "Faktor (1,0 = unverändert):",
                    "Factor (1.0 = unchanged):", ImageEnhance.Brightness(self.image).enhance)

    def adjust_contrast(self):
        self.adjust("Kontrast", "Contrast", "Faktor (1,0 = unverändert):",
                    "Factor (1.0 = unchanged):", ImageEnhance.Contrast(self.image).enhance)

    def adjust_saturation(self):
        self.adjust("Sättigung", "Saturation", "Faktor (1,0 = unverändert):",
                    "Factor (1.0 = unchanged):", ImageEnhance.Color(self.image).enhance)

    def grayscale(self):
        if self.image is not None:
            self.apply_edit(ImageOps.grayscale(self.image).convert("RGBA"))

    def invert(self):
        if self.image is not None:
            rgb = ImageOps.invert(self.image.convert("RGB"))
            self.apply_edit(rgb.convert("RGBA"))

    def black_white(self):
        if self.image is not None:
            gray = ImageOps.grayscale(self.image)
            self.apply_edit(gray.point(lambda p: 255 if p >= 128 else 0).convert("RGBA"))

    def sharpen(self):
        if self.image is not None:
            self.apply_edit(self.image.filter(ImageFilter.SHARPEN))

    def blur(self):
        if self.image is not None:
            self.apply_edit(self.image.filter(ImageFilter.GaussianBlur(radius=2)))

    # ---------- Folder navigation / thumbnails ----------

    def build_thumbnails(self):
        for child in self.thumb_frame.winfo_children():
            child.destroy()
        self.thumbnails.clear()
        self.thumb_buttons.clear()

        for index, path in enumerate(self.folder_images):
            try:
                with Image.open(path) as source_img:
                    width, height = source_img.size
                    img = source_img.convert("RGB")
                    img.thumbnail((145, 100), Image.Resampling.LANCZOS)

                photo = ImageTk.PhotoImage(img)
                self.thumbnails.append(photo)

                # Kompakte Bildkarte: Vorschau links, Dateiname und
                # Bildabmessungen/Dateigröße rechts daneben.
                card = ttk.Frame(self.thumb_frame, style="Sidebar.TFrame")
                card.pack(fill="x", padx=2, pady=3)

                btn = ttk.Button(
                    card,
                    image=photo,
                    command=lambda p=path: self.load_image(p),
                )
                btn.pack(side="left", padx=(2, 8), pady=2)

                try:
                    size_bytes = Path(path).stat().st_size
                    if size_bytes < 1024:
                        file_size = f"{size_bytes} B"
                    elif size_bytes < 1024 * 1024:
                        file_size = f"{size_bytes / 1024:.1f} KB"
                    else:
                        file_size = f"{size_bytes / (1024 * 1024):.1f} MB"
                except OSError:
                    file_size = "?"

                name = Path(path).name
                # Sehr lange Dateinamen bleiben lesbar, ohne die Seitenleiste
                # unnötig zu verbreitern.
                if len(name) > 22:
                    name = name[:19] + "..."

                info_frame = ttk.Frame(card, style="Sidebar.TFrame")
                info_frame.pack(side="left", fill="both", expand=True, pady=4)

                name_label = ttk.Label(
                    info_frame, text=name, style="ThumbName.TLabel",
                    wraplength=135, anchor="w"
                )
                name_label.pack(fill="x", pady=(4, 6))

                details = (
                    f"{width} × {height} Pixel\n"
                    f"{file_size}"
                )
                detail_label = ttk.Label(
                    info_frame, text=details, style="ThumbInfo.TLabel",
                    anchor="w"
                )
                detail_label.pack(fill="x")

                # Klick auf die Informationsbeschriftung soll ebenfalls
                # das zugehörige Bild öffnen.
                name_label.bind("<Button-1>", lambda _e, p=path: self.load_image(p))
                detail_label.bind("<Button-1>", lambda _e, p=path: self.load_image(p))
                info_frame.bind("<Button-1>", lambda _e, p=path: self.load_image(p))

                # Mausrad über der gesamten Bildkarte.
                for widget in (card, btn, info_frame, name_label, detail_label):
                    widget.bind("<MouseWheel>", self._scroll_thumbnails, add="+")
                    widget.bind("<Button-4>", self._scroll_thumbnails, add="+")
                    widget.bind("<Button-5>", self._scroll_thumbnails, add="+")

                self.thumb_buttons.append(btn)
            except Exception:
                continue

    def previous_image(self):
        if not self.folder_images:
            return
        self.folder_index = (self.folder_index - 1) % len(self.folder_images)
        self.load_image(self.folder_images[self.folder_index])

    def next_image(self):
        if not self.folder_images:
            return
        self.folder_index = (self.folder_index + 1) % len(self.folder_images)
        self.load_image(self.folder_images[self.folder_index])

    # ---------- Slideshow ----------

    def start_slideshow(self):
        if not self.folder_images:
            self.info_no_image()
            return
        self.slideshow_running = True
        self.slideshow_step()

    def slideshow_step(self):
        if not getattr(self, "slideshow_running", False):
            return
        self.next_image()
        self.root.after(3000, self.slideshow_step)

    def stop_slideshow(self):
        self.slideshow_running = False

    # ---------- Fullscreen ----------

    def toggle_fullscreen(self):
        current = bool(self.root.attributes("-fullscreen"))
        self.root.attributes("-fullscreen", not current)

    def exit_fullscreen(self):
        self.root.attributes("-fullscreen", False)

    # ---------- System actions ----------

    def print_image(self):
        if not self.image_path:
            self.info_no_image()
            return
        try:
            system = platform.system()
            if system == "Linux":
                subprocess.Popen(["lp", self.image_path])
            elif system == "Windows":
                os.startfile(self.image_path, "print")
            elif system == "Darwin":
                subprocess.Popen(["open", self.image_path])
            else:
                raise RuntimeError("Drucken wird auf diesem System nicht automatisch unterstützt.")
        except Exception as exc:
            messagebox.showerror(
                "Fehler" if self.lang == "de" else "Error",
                f"Drucken konnte nicht gestartet werden:\n{exc}",
            )

    def set_wallpaper(self):
        if not self.image_path:
            self.info_no_image()
            return
        path = os.path.abspath(self.image_path)
        try:
            system = platform.system()
            if system == "Windows":
                import ctypes
                ctypes.windll.user32.SystemParametersInfoW(20, 0, path, 3)
            elif system == "Linux":
                uri = Path(path).as_uri()
                subprocess.Popen(["gsettings", "set", "org.gnome.desktop.background", "picture-uri", uri])
                subprocess.Popen(["gsettings", "set", "org.gnome.desktop.background", "picture-uri-dark", uri])
            elif system == "Darwin":
                subprocess.Popen(["osascript", "-e", f'tell application "System Events" to tell every desktop to set picture to POSIX file "{path}"'])
            else:
                raise RuntimeError("Nicht unterstütztes Betriebssystem.")
        except Exception as exc:
            messagebox.showerror(
                "Fehler" if self.lang == "de" else "Error",
                f"Hintergrundbild konnte nicht gesetzt werden:\n{exc}",
            )

    # ---------- Settings ----------

    def load_settings(self):
        defaults = {
            "language": "de", "theme": "dark", "last_folder": "", "image_folder": "",
            "geometry": "", "window_width": 1200, "window_height": 760,
            "maximized": False, "zoom": 100, "slideshow_interval": 3,
        }
        try:
            if SETTINGS_FILE.exists():
                cfg = configparser.ConfigParser()
                cfg.read(SETTINGS_FILE, encoding="utf-8")
                sec = cfg["General"] if "General" in cfg else {}
                for key in ("language", "theme", "last_folder", "image_folder", "geometry"):
                    if key in sec:
                        defaults[key] = sec.get(key, defaults[key])
                for key in ("window_width", "window_height", "zoom", "slideshow_interval"):
                    if key in sec:
                        try:
                            defaults[key] = int(sec.get(key))
                        except ValueError:
                            pass
                if "maximized" in sec:
                    defaults["maximized"] = sec.getboolean("maximized", fallback=False)
                return defaults
        except Exception:
            pass

        # Migrate the older JSON settings file when present.
        try:
            if LEGACY_SETTINGS_FILE.exists():
                data = json.loads(LEGACY_SETTINGS_FILE.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    defaults.update({k: v for k, v in data.items() if k in defaults})
        except Exception:
            pass
        return defaults

    def save_settings(self):
        try:
            cfg = configparser.ConfigParser()
            cfg["General"] = {
                "language": str(self.settings.get("language", self.lang)),
                "theme": str(self.settings.get("theme", self.theme)),
                "last_folder": str(self.settings.get("last_folder", "")),
                "image_folder": str(self.settings.get("image_folder", "")),
                "geometry": str(self.settings.get("geometry", "")),
                "window_width": str(self.settings.get("window_width", 1200)),
                "window_height": str(self.settings.get("window_height", 760)),
                "maximized": str(bool(self.settings.get("maximized", False))),
                "zoom": str(self.settings.get("zoom", 100)),
                "slideshow_interval": str(self.settings.get("slideshow_interval", 3)),
            }
            SETTINGS_FILE.write_text("; Bildbetrachter Einstellungen\n" + "\n".join(
                ["[General]"] + [f"{k}={v}" for k, v in cfg["General"].items()]
            ) + "\n", encoding="utf-8")
        except Exception:
            pass
    def show_settings(self):
        de = self.lang == "de"
        dialog = tk.Toplevel(self.root)
        dialog.title("Einstellungen" if de else "Settings")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)
        dialog.configure(bg=self.colors["bg"])

        frame = tk.Frame(dialog, bg=self.colors["bg"], padx=22, pady=20)
        frame.pack(fill="both", expand=True)

        tk.Label(frame, text="Darstellung" if de else "Appearance",
                 bg=self.colors["bg"], fg=self.colors["fg"],
                 font=("TkDefaultFont", 12, "bold")).grid(
                     row=0, column=0, columnspan=3, sticky="w", pady=(0, 12))

        tk.Label(frame, text="Theme:",
                 bg=self.colors["bg"], fg=self.colors["fg"]).grid(
                     row=1, column=0, sticky="w", padx=(0, 14), pady=4)

        theme_var = tk.StringVar(value=self.theme)
        combo = ttk.Combobox(
            frame, textvariable=theme_var, state="readonly", width=18,
            values=["Dunkel" if de else "Dark", "Hell" if de else "Light"])
        combo.grid(row=1, column=1, columnspan=2, sticky="ew", pady=4)
        combo.current(0 if self.theme == "dark" else 1)

        tk.Label(frame, text="Bildordner" if de else "Image folder",
                 bg=self.colors["bg"], fg=self.colors["fg"],
                 font=("TkDefaultFont", 12, "bold")).grid(
                     row=2, column=0, columnspan=3, sticky="w", pady=(18, 8))

        folder_var = tk.StringVar(value=str(self.settings.get("image_folder", "")))
        tk.Label(frame, text="Pfad:" if de else "Path:",
                 bg=self.colors["bg"], fg=self.colors["fg"]).grid(
                     row=3, column=0, sticky="w", padx=(0, 14), pady=4)

        folder_entry = tk.Entry(
            frame, textvariable=folder_var, width=52,
            bg=self.colors["surface"], fg=self.colors["fg"],
            insertbackground=self.colors["fg"],
            relief="solid", highlightthickness=1)
        folder_entry.grid(row=3, column=1, sticky="ew", pady=4)

        def choose_folder():
            initial = folder_var.get().strip() or str(self.get_start_folder())
            selected = filedialog.askdirectory(
                parent=dialog,
                title="Bildordner auswählen" if de else "Select image folder",
                initialdir=initial if Path(initial).is_dir() else str(Path(__file__).resolve().parent))
            if selected:
                folder_var.set(selected)

        ttk.Button(
            frame, text="Durchsuchen..." if de else "Browse...",
            command=choose_folder).grid(row=3, column=2, padx=(8, 0), pady=4)

        last_folder = str(self.settings.get("last_folder", "")).strip()
        last_display = last_folder if last_folder else (
            "Noch kein Ordner gespeichert." if de else "No folder saved yet.")

        tk.Label(
            frame,
            text=("Zuletzt verwendeter Ordner: " if de else "Last used folder: ") + last_display,
            bg=self.colors["bg"], fg=self.colors["muted"],
            justify="left", anchor="w", wraplength=560
        ).grid(row=4, column=0, columnspan=3, sticky="w", pady=(10, 4))

        tk.Label(
            frame,
            text=("Beim Start wird zuerst der zuletzt verwendete Ordner geöffnet. "
                  "Ist er nicht vorhanden, wird der eingestellte Bildordner verwendet. "
                  "Falls auch dieser fehlt, wird der Programmordner „Bild“ verwendet."
                  if de else
                  "At startup, the last used folder is opened first. "
                  "If it no longer exists, the configured image folder is used. "
                  "If that is also unavailable, the program folder „Bild“ is used."),
            bg=self.colors["bg"], fg=self.colors["muted"],
            justify="left", anchor="w", wraplength=560
        ).grid(row=5, column=0, columnspan=3, sticky="w", pady=(0, 14))

        def apply_and_close():
            selected_theme = theme_var.get()
            dark = selected_theme in ("Dunkel", "Dark")
            self.theme = "dark" if dark else "light"
            self.settings["theme"] = self.theme

            folder = folder_var.get().strip()
            if folder and Path(folder).expanduser().is_dir():
                folder = str(Path(folder).expanduser().resolve())
                self.settings["image_folder"] = folder
                self.current_folder = Path(folder)
                self.load_folder_images(self.current_folder)
            elif folder:
                messagebox.showwarning(
                    "Ungültiger Ordner" if de else "Invalid folder",
                    "Der angegebene Bildordner existiert nicht." if de else
                    "The selected image folder does not exist.",
                    parent=dialog)
                return

            self.save_settings()
            self.apply_theme()
            self.build_menu()
            self.update_ui()
            dialog.destroy()

        ttk.Button(
            frame, text="Übernehmen" if de else "Apply",
            command=apply_and_close).grid(
                row=6, column=1, columnspan=2, sticky="e", pady=(4, 0))

        folder_entry.focus_set()


        def select_theme(_event=None):
            value = "dark" if combo.current() == 0 else "light"
            self.theme = value
            self.settings["theme"] = value
            self.save_settings()
            self.apply_theme()
            dialog.configure(bg=self.colors["bg"])
            frame.configure(bg=self.colors["bg"])
            for child in frame.winfo_children():
                if isinstance(child, tk.Label):
                    child.configure(bg=self.colors["bg"], fg=self.colors["fg"])

        combo.bind("<<ComboboxSelected>>", select_theme)

        tk.Label(frame, text="Bildordner" if de else "Image folder",
                 bg=self.colors["bg"], fg=self.colors["fg"],
                 font=("TkDefaultFont", 12, "bold")).grid(row=2, column=0, columnspan=3, sticky="w", pady=(22, 10))
        tk.Label(frame, text="Pfad:" if de else "Path:",
                 bg=self.colors["bg"], fg=self.colors["fg"]).grid(row=3, column=0, sticky="w", padx=(0, 14))

        folder_var = tk.StringVar(value=self.settings.get("image_folder", ""))
        folder_entry = tk.Entry(frame, textvariable=folder_var, width=42,
                                bg=self.colors["surface"], fg=self.colors["fg"],
                                insertbackground=self.colors["fg"], relief="flat", bd=0)
        folder_entry.grid(row=3, column=1, sticky="ew", ipady=6)

        def choose_folder():
            selected = filedialog.askdirectory(
                title="Bildordner auswählen" if de else "Select image folder",
                initialdir=str(self.get_start_folder())
            )
            if selected:
                folder_var.set(selected)

        tk.Button(frame, text="Durchsuchen..." if de else "Browse...", command=choose_folder,
                  bg=self.colors["surface2"], fg=self.colors["fg"],
                  activebackground=self.colors["active"], activeforeground=self.colors["fg"],
                  relief="flat", bd=0, padx=10, pady=6).grid(row=3, column=2, padx=(8, 0))

        last_folder = self.settings.get("last_folder", "")
        last_text = last_folder if last_folder else ("Noch kein Ordner gespeichert." if de else "No folder saved yet.")
        tk.Label(frame, text=("Zuletzt verwendet: " if de else "Last used: ") + last_text,
                 bg=self.colors["bg"], fg=self.colors["muted"], wraplength=520, justify="left").grid(
                     row=4, column=0, columnspan=3, sticky="w", pady=(10, 6))
        tk.Label(frame, text=(
            "Beim Start wird zuerst der hier eingestellte Bildordner verwendet. Ist er nicht vorhanden, "
            "wird der zuletzt verwendete Ordner geöffnet. Falls auch dieser fehlt, wird der Programmordner 'Bild' verwendet."
            if de else
            "At startup, the configured image folder is used first. If it is unavailable, the last used folder is used. "
            "If that folder is also unavailable, the program folder 'Bild' is used."),
            bg=self.colors["bg"], fg=self.colors["muted"], wraplength=520, justify="left"
        ).grid(row=5, column=0, columnspan=3, sticky="w", pady=(0, 16))

        def save_and_close():
            folder = folder_var.get().strip()
            if folder:
                folder_path = Path(folder).expanduser()
                if not folder_path.is_dir():
                    messagebox.showwarning(
                        "Ordner nicht gefunden" if de else "Folder not found",
                        "Der eingegebene Bildordner existiert nicht." if de else "The entered image folder does not exist.",
                        parent=dialog
                    )
                    return
                folder = str(folder_path.resolve())
                self.settings["image_folder"] = folder
                self.settings["last_folder"] = folder
            else:
                self.settings["image_folder"] = ""
            self.save_settings()
            self.prepare_start_folder()
            dialog.destroy()

        tk.Button(frame, text="OK", width=10, command=save_and_close,
                  bg=self.colors["surface2"], fg=self.colors["fg"],
                  activebackground=self.colors["active"], activeforeground=self.colors["fg"],
                  relief="flat", bd=0, padx=10, pady=6).grid(row=6, column=2, sticky="e")

        dialog.bind("<Escape>", lambda _event: dialog.destroy())
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{max(0, x)}+{max(0, y)}")

    # ---------- Misc ----------

    def show_image_information(self):
        """Show the information panel only when explicitly requested.

        Selecting a thumbnail always opens the image in the main preview.
        The panel stays hidden until this action is invoked from the menu.
        Once opened, it remains visible and updates for subsequently selected images.
        """
        if self.image is None or not self.image_path:
            self.info_no_image()
            return

        if not self.info_panel_visible:
            # Insert the information panel between thumbnails and main preview.
            self.info_panel.pack(side="left", fill="y", padx=(0, 1))
            self.info_panel_visible = True
        self.update_image_information_panel()

    def hide_image_information(self):
        """Close the optional information panel without changing the image."""
        if getattr(self, "info_panel_visible", False):
            self.info_panel.pack_forget()
            self.info_panel_visible = False


    def update_image_information_panel(self):
        """Refresh the visible information panel without changing the image view."""
        if not hasattr(self, "info_body") or self.image is None or not self.image_path:
            return
        try:
            p = Path(self.image_path)
            stat = p.stat()
            size_bytes = stat.st_size
            if size_bytes < 1024:
                file_size = f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                file_size = f"{size_bytes / 1024:.1f} KB"
            else:
                file_size = f"{size_bytes / (1024 * 1024):.2f} MB"

            width, height = self.image.size
            fmt = self.image.format or p.suffix.lstrip(".").upper()
            mode = self.image.mode
            modified = datetime.fromtimestamp(stat.st_mtime).strftime("%d.%m.%Y %H:%M:%S")
            transparency = "Ja" if "A" in mode else "Nein"

            if self.lang == "de":
                info = (
                    f"Dateiname:\n{p.name}\n\n"
                    f"Ordner:\n{p.parent}\n\n"
                    f"Abmessungen:\n{width} × {height} Pixel\n\n"
                    f"Dateigröße:\n{file_size}\n({size_bytes:,} Bytes)\n\n"
                    f"Dateityp:\n{fmt}-Bild\n\n"
                    f"Letzte Änderung:\n{modified}\n\n"
                    f"Transparenz:\n{transparency}"
                )
            else:
                transparency = "Yes" if "A" in mode else "No"
                info = (
                    f"Filename:\n{p.name}\n\n"
                    f"Folder:\n{p.parent}\n\n"
                    f"Dimensions:\n{width} × {height} pixels\n\n"
                    f"File size:\n{file_size}\n({size_bytes:,} bytes)\n\n"
                    f"File type:\n{fmt} image\n\n"
                    f"Modified:\n{modified}\n\n"
                    f"Transparency:\n{transparency}"
                )

            self.info_body.configure(state="normal")
            self.info_body.delete("1.0", "end")
            self.info_body.insert("1.0", info)
            self.info_body.configure(state="disabled")
        except Exception as exc:
            self.info_body.configure(state="normal")
            self.info_body.delete("1.0", "end")
            self.info_body.insert("1.0", str(exc))
            self.info_body.configure(state="disabled")

    def info_no_image(self):
        messagebox.showinfo(
            "Hinweis" if self.lang == "de" else "Information",
            "Kein Bild geladen." if self.lang == "de" else "No image loaded.",
        )

    def about(self):
        messagebox.showinfo(
            "Über Bildbetrachter" if self.lang == "de" else "About Image Viewer",
            "Bildbetrachter\n\nEin kompakter Bildbetrachter und einfacher Bildeditor."
            if self.lang == "de"
            else "Image Viewer\n\nA compact image viewer and simple image editor.",
        )

    def update_ui(self):
        self.btn_undo.configure(state="normal" if self.history else "disabled")
        self.btn_redo.configure(state="normal" if self.redo_history else "disabled")

        if self.image is None:
            self.status_var.set("Kein Bild geöffnet" if self.lang == "de" else "No image open")
            return

        w, h = self.image.size
        name = Path(self.image_path).name if self.image_path else "-"
        self.status_var.set(
            f"{name}  |  {w} × {h} px  |  {self.zoom_var.get()}"
        )

    def on_close(self):
        if not self.confirm_unsaved_changes():
            return
        self.settings["geometry"] = self.root.geometry()
        if getattr(self, "current_folder", None):
            self.settings["last_folder"] = str(self.current_folder)
        self.save_settings()
        self.stop_slideshow()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = ImageViewerApp(root)
    root.after(150, app.fit_to_window)
    root.mainloop()

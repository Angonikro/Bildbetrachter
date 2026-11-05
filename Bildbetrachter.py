#!/usr/bin/env python3
"""Bildbetrachter 0.1.19 - Qt 6 / PySide6 edition."""
import os, sys, json, configparser, subprocess, platform
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageEnhance, ImageFilter, ImageOps, ImageDraw
from PySide6.QtCore import Qt, QSize, QTimer, QSettings, QByteArray, QTranslator, QLocale, QLibraryInfo
from PySide6.QtGui import QAction, QIcon, QPixmap, QImage, QKeySequence, QPainter, QPen, QColor
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, QPushButton, QToolButton,
    QFileDialog, QMessageBox, QVBoxLayout, QHBoxLayout, QSplitter, QListWidget, QListWidgetItem,
    QScrollArea, QFrame, QMenu, QDialog, QFormLayout, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox,
    QCheckBox, QDialogButtonBox, QInputDialog, QColorDialog, QSlider, QStatusBar, QToolBar, QStyle,
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsRectItem, QDockWidget, QTextBrowser,
    QProgressDialog, QAbstractItemView)

APP_NAME='Bildbetrachter'; APP_VERSION='0.1.19'
SUPPORTED={'.bmp','.dib','.gif','.jpg','.jpeg','.jpe','.jfif','.png','.webp','.tif','.tiff','.ico','.ppm','.pgm','.pbm','.pnm','.xbm','.xpm','.tga','.pcx'}
CONFIG_DIR=Path(os.environ.get('XDG_CONFIG_HOME',str(Path.home()/'.config')))/'bildbetrachter'
SETTINGS_FILE=CONFIG_DIR/'settings.ini'

class ImageCanvas(QGraphicsView):
    def __init__(self, app):
        super().__init__(); self.app=app; self.setScene(QGraphicsScene(self)); self.setBackgroundBrush(QColor('#10152b'))
        self.setDragMode(QGraphicsView.NoDrag); self.setCursor(Qt.ArrowCursor); self.setRenderHints(QPainter.Antialiasing|QPainter.SmoothPixmapTransform)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse); self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
    def wheelEvent(self,e):
        # Mausrad direkt zum Zoomen verwenden; Scrollen der Bildansicht
        # erfolgt weiterhin per gedrueckter mittlerer Maustaste/Scroll-Hand.
        delta = e.angleDelta().y()
        if delta:
            steps = delta / 120.0
            self.app.zoom(1.15 ** steps)
            e.accept()
        else:
            e.ignore()
    def contextMenuEvent(self,e):
        if self.app.draw_mode:
            self.app.draw_mode=False; self.app.status.showMessage('Zeichenmodus beendet',2500); e.accept(); return
        self.app.show_context_menu(e.globalPos())
    def mousePressEvent(self,e):
        if self.app.draw_mode and e.button()==Qt.LeftButton:
            self.app.draw_begin(self.mapToScene(e.position().toPoint())); e.accept(); return
        if self.app.crop_mode and e.button()==Qt.LeftButton:
            self.app.crop_begin(self.mapToScene(e.position().toPoint())); e.accept(); return
        super().mousePressEvent(e)
    def mouseMoveEvent(self,e):
        if self.app.draw_mode and self.app.draw_active:
            self.app.draw_continue(self.mapToScene(e.position().toPoint())); e.accept(); return
        if self.app.crop_mode and self.app.crop_active:
            self.app.crop_update(self.mapToScene(e.position().toPoint())); e.accept(); return
        super().mouseMoveEvent(e)
    def mouseReleaseEvent(self,e):
        if self.app.draw_mode and e.button()==Qt.LeftButton:
            self.app.draw_end(); e.accept(); return
        if self.app.crop_mode and e.button()==Qt.LeftButton:
            self.app.crop_finish(); e.accept(); return
        super().mouseReleaseEvent(e)

class ImageViewer(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle(f'{APP_NAME} {APP_VERSION}'); self.resize(1400,850); self.setMinimumSize(900,600)
        self.image=None; self.path=None; self.folder=[]; self.index=-1; self.dirty=False; self.zoom_factor=1.0; self.fit_mode=True
        self.draw_mode=False; self.draw_active=False; self.crop_mode=False; self.crop_active=False; self.crop_origin=None; self.crop_rect=None; self.draw_color='#ff2020'; self.draw_size=5; self.draw_last=None; self._draw_before=None
        self.undo_stack=[]; self.redo_stack=[]; self.thumb_cache={}; self.thumb_limit=20; self._thumb_queue=[]; self._thumb_worker=QTimer(self); self._thumb_worker.setInterval(15); self._thumb_worker.timeout.connect(self._thumb_batch); self.slideshow_active=False
        self.lang='de'; self.theme='blue'; self.settings=self.read_settings(); self.slideshow_interval=max(1,min(60,int(self.settings.get('slideshow_interval','3')))); self._thumb_timer=QTimer(self); self._thumb_timer.setSingleShot(True); self._thumb_timer.timeout.connect(self.refresh_thumbs)
        self.lang=self.settings.get('language','de'); self.theme=self.settings.get('theme','blue')
        if self.theme == 'violet': self.theme = 'blue'
        self.build_ui(); self.build_menus(); self.apply_theme(); self.update_actions()
        geometry=self.settings.get('window_geometry','')
        if geometry:
            try:self.restoreGeometry(QByteArray.fromHex(geometry.encode('ascii')))
            except Exception:pass
        QTimer.singleShot(100,self.load_start_folder)
        if len(sys.argv)>1 and Path(sys.argv[1]).is_file(): QTimer.singleShot(150,lambda:self.open_path(sys.argv[1]))

    def read_settings(self):
        CONFIG_DIR.mkdir(parents=True,exist_ok=True); cp=configparser.ConfigParser()
        if SETTINGS_FILE.exists(): cp.read(SETTINGS_FILE,encoding='utf-8')
        return dict(cp['general']) if cp.has_section('general') else {}
    def save_settings(self):
        CONFIG_DIR.mkdir(parents=True,exist_ok=True); cp=configparser.ConfigParser(); cp['general']={'theme':self.theme,'language':self.lang,'slideshow_interval':str(getattr(self,'slideshow_interval',3)),'window_geometry':bytes(self.saveGeometry().toHex()).decode('ascii'),'last_folder':str(Path(self.path).parent) if self.path else self.settings.get('last_folder',str(Path.home()/'Pictures'))}
        with SETTINGS_FILE.open('w',encoding='utf-8') as f: cp.write(f)

    def build_ui(self):
        central=QWidget(); root=QVBoxLayout(central); root.setContentsMargins(7,7,7,5); root.setSpacing(7)
        self.toolbar=QFrame(); self.toolbar.setObjectName('toolbar'); tl=QHBoxLayout(self.toolbar); tl.setContentsMargins(7,6,7,6); tl.setSpacing(6)
        specs=[('open.svg','Öffnen','Open',self.open_dialog),('save.svg','Speichern','Save',self.save_image),('undo.svg','Rückgängig','Undo',self.undo),('redo.svg','Wiederholen','Redo',self.redo),('rotate-left.svg','Links drehen','Rotate left',lambda:self.rotate(90)),('rotate-right.svg','Rechts drehen','Rotate right',lambda:self.rotate(-90)),('flip-h.svg','Horizontal','Flip H',self.mirror_h),('flip-v.svg','Vertikal','Flip V',self.mirror_v),('fit.svg','Anpassen','Fit',self.fit),('zoom.svg','100 %','100 %',self.zoom100),('fullscreen.svg','Vollbild','Fullscreen',self.toggle_fullscreen)]
        self.toolbar_buttons=[]
        for icon_name,label,en_label,fn in specs:
            b=QToolButton(); b.setIcon(QIcon(str(Path(__file__).parent/'icons'/'toolbar'/icon_name))); b.setIconSize(QSize(48,48)); b.setText(self.tr(label,en_label)); b.setProperty('de_text',label); b.setProperty('en_text',en_label); self.toolbar_buttons.append(b); b.setToolButtonStyle(Qt.ToolButtonTextUnderIcon); b.setMinimumSize(104,96); b.setStyleSheet('QToolButton { font-size: 12pt; font-weight: 600; padding: 5px; } QToolButton::icon { width: 48px; height: 48px; }'); b.clicked.connect(fn); tl.addWidget(b)
            if label=='Speichern': self.save_button=b
        tl.addStretch(1); root.addWidget(self.toolbar)
        split=QSplitter(Qt.Horizontal); split.setChildrenCollapsible(False)
        side=QFrame(); side.setObjectName('sidebar'); side.setMinimumWidth(250); side.setMaximumWidth(420); sl=QVBoxLayout(side); sl.setContentsMargins(9,9,9,9)
        title=QLabel(self.tr('▣  Bilder im Ordner','▣  Images in folder')); title.setObjectName('sideTitle'); self.side_title=title; sl.addWidget(title)
        self.folder_label=QLabel(self.tr('Aktueller Ordner: —','Current folder: —'));  self.folder_label.setWordWrap(True); sl.addWidget(self.folder_label)
        self.folder_btn=QPushButton(self.tr('📁  Gespeicherten Bildordner laden','📁  Load saved image folder'));  self.folder_btn.clicked.connect(self.choose_folder); sl.addWidget(self.folder_btn)
        self.list=QListWidget(); self.list.setIconSize(QSize(100,72)); self.list.setSpacing(5); self.list.setUniformItemSizes(False); self.list.currentRowChanged.connect(self.select_row); self.list.verticalScrollBar().valueChanged.connect(lambda _v:self._thumb_timer.start(80)); self.list.setContextMenuPolicy(Qt.CustomContextMenu); self.list.customContextMenuRequested.connect(self.thumb_context); sl.addWidget(self.list,1)
        split.addWidget(side)
        self.canvas=ImageCanvas(self); split.addWidget(self.canvas); split.setStretchFactor(1,1); split.setSizes([300,1050]); root.addWidget(split,1)
        self.setCentralWidget(central); self.status=QStatusBar(); self.setStatusBar(self.status); self.status.showMessage('Kein Bild geöffnet')
        self.info=QDockWidget(self.tr('Bildinformationen','Image information'),self); self.info.setObjectName('infoDock'); self.info.setAllowedAreas(Qt.RightDockWidgetArea|Qt.LeftDockWidgetArea)
        self.info_text=QLabel('Kein Bild geöffnet'); self.info_text.setWordWrap(True); self.info.setWidget(self.info_text); self.addDockWidget(Qt.RightDockWidgetArea,self.info); self.info.hide()

    def action(self,menu,text,fn,shortcut=None):
        a=QAction(text,self); a.triggered.connect(lambda checked=False, callback=fn: callback())
        if shortcut: a.setShortcut(QKeySequence(shortcut))
        menu.addAction(a); return a
    def build_menus(self):
        t=self.tr; bar=self.menuBar()
        m=bar.addMenu(t('Datei','File'))
        self.action(m,t('Öffnen…','Open…'),self.open_dialog,'Ctrl+O'); self.action(m,t('Ordner öffnen…','Open folder…'),self.choose_folder,'Ctrl+Shift+O'); self.action(m,t('Speichern','Save'),self.save_image,'Ctrl+S'); self.action(m,t('Speichern unter…','Save as…'),self.save_as,'Ctrl+Shift+S'); m.addSeparator(); self.action(m,t('Drucken…','Print…'),self.print_image); self.action(m,t('Als Hintergrundbild setzen','Set as wallpaper'),self.wallpaper); m.addSeparator(); self.action(m,t('Beenden','Quit'),self.close,'Ctrl+Q')
        m=bar.addMenu(t('Bearbeiten','Edit')); self.action(m,t('Rückgängig','Undo'),self.undo,'Ctrl+Z'); self.action(m,t('Wiederholen','Redo'),self.redo,'Ctrl+Y'); m.addSeparator(); self.action(m,t('Zeichnen…','Draw…'),self.draw_dialog); self.action(m,t('Zeichenmodus beenden','Exit drawing mode'),self.stop_draw); self.action(m,t('Zuschneiden (mit Maus)','Crop (with mouse)'),self.start_crop_mode,'Ctrl+Shift+X'); self.action(m,t('Größe ändern…','Resize…'),self.resize_dialog)
        m=bar.addMenu(t('Ansicht','View')); self.action(m,t('An Fenster anpassen','Fit to window'),self.fit,'F'); self.action(m,'100 %',self.zoom100,'1'); self.action(m,t('Vergrößern','Zoom in'),lambda:self.zoom(1.2),'Ctrl++'); self.action(m,t('Verkleinern','Zoom out'),lambda:self.zoom(1/1.2),'Ctrl+-'); self.action(m,t('Vollbild','Fullscreen'),self.toggle_fullscreen,'F11'); self.action(m,t('Bildinformationen','Image information'),self.toggle_info,'Ctrl+I')
        m=bar.addMenu(t('Bild','Image')); self.action(m,t('Links drehen','Rotate left'),lambda:self.rotate(90)); self.action(m,t('Rechts drehen','Rotate right'),lambda:self.rotate(-90)); self.action(m,t('Horizontal spiegeln','Flip horizontally'),self.mirror_h); self.action(m,t('Vertikal spiegeln','Flip vertically'),self.mirror_v); m.addSeparator(); self.action(m,t('Helligkeit…','Brightness…'),lambda:self.adjust(t('Helligkeit','Brightness'),ImageEnhance.Brightness)); self.action(m,t('Kontrast…','Contrast…'),lambda:self.adjust(t('Kontrast','Contrast'),ImageEnhance.Contrast)); self.action(m,t('Farbsättigung…','Saturation…'),lambda:self.adjust(t('Farbsättigung','Saturation'),ImageEnhance.Color)); self.action(m,t('Graustufen','Grayscale'),self.grayscale); self.action(m,t('Schwarz-Weiß','Black and white'),self.black_white); self.action(m,t('Invertieren','Invert'),self.invert); self.action(m,t('Schärfen','Sharpen'),self.sharpen); self.action(m,t('Weichzeichnen','Blur'),self.blur)
        m=bar.addMenu(t('Werkzeuge','Tools')); self.action(m,t('Diashow starten/stoppen','Start/stop slideshow'),self.slideshow); self.action(m,t('Bildinformationen','Image information'),self.toggle_info); self.action(m,t('Einstellungen','Preferences'),self.preferences); m.addSeparator(); self.action(m,t('Sprache: Deutsch','Language: German'),lambda:self.set_language('de')); self.action(m,t('Sprache: Englisch','Language: English'),lambda:self.set_language('en'))
        m=bar.addMenu(t('Design','Theme')); self.action(m,t('Blau (bunt)','Blue (colorful)'),lambda:self.set_theme('blue')); self.action(m,t('Dunkel','Dark'),lambda:self.set_theme('dark')); self.action(m,t('Hell','Light'),lambda:self.set_theme('light'))
        m=bar.addMenu(t('Hilfe','Help')); self.action(m,t('Anleitung','User guide'),self.manual); self.action(m,t(self.tr('Über Bildbetrachter','About Image Viewer'),'About Image Viewer'),self.about)

    def set_language(self, language):
        self.lang = 'en' if language == 'en' else 'de'
        self.settings['language'] = self.lang
        self.save_settings()
        self.menuBar().clear()
        self.build_menus()
        self.setWindowTitle(f'{APP_NAME} {APP_VERSION}')
        if hasattr(self,'toolbar_buttons'):
            for b in self.toolbar_buttons: b.setText(b.property('en_text') if self.lang=='en' else b.property('de_text'))
            self.side_title.setText(self.tr('▣  Bilder im Ordner','▣  Images in folder'))
            self.folder_label.setText(self.tr('Aktueller Ordner: —','Current folder: —') if not self.path else self.tr('Aktueller Ordner:','Current folder:')+'\n'+str(Path(self.path).parent))
            self.folder_btn.setText(self.tr('📁  Gespeicherten Bildordner laden','📁  Load saved image folder'))
            self.info.setWindowTitle(self.tr('Bildinformationen','Image information'))
            self.update_info()
        self.status.showMessage(self.tr('Sprache geändert','Language changed'),2500)

    def tr(self, de, en):
        return en if self.lang == 'en' else de

    def localize_buttons(self, box, accept=None, reject=None, close=None):
        if box.button(QDialogButtonBox.Ok): box.button(QDialogButtonBox.Ok).setText(accept or self.tr('OK','OK'))
        if box.button(QDialogButtonBox.Cancel): box.button(QDialogButtonBox.Cancel).setText(reject or self.tr('Abbrechen','Cancel'))
        if box.button(QDialogButtonBox.Close): box.button(QDialogButtonBox.Close).setText(close or self.tr('Schließen','Close'))

    def apply_theme(self):
        themes={'blue':('#071629','#102b4a','#16436b','#1687e8','#28d7f2','#f4f8ff'),'dark':('#17191f','#242731','#303541','#5b7cfa','#38bdf8','#f2f4f8'),'light':('#edf1f8','#ffffff','#e5eaf4','#7357df','#16a6c4','#202638')}
        bg,surface,raised,purple,cyan,fg=themes.get(self.theme,themes['blue'])
        self.setStyleSheet(f"""
        QMainWindow,QWidget{{background:{bg};color:{fg};font-size:10pt}} QMenuBar{{background:{surface};padding:5px}} QMenuBar::item{{padding:7px 10px;border-radius:5px}} QMenuBar::item:selected{{background:{purple}}}
        QMenu{{background:{surface};border:1px solid {purple};padding:5px}} QMenu::item{{padding:7px 28px;border-radius:4px}} QMenu::item:selected{{background:{purple}}}
        QFrame#toolbar{{background:{surface};border:1px solid {purple};border-radius:12px}} QFrame#sidebar{{background:{surface};border:1px solid {purple};border-radius:10px}} QLabel#sideTitle{{font-size:12pt;font-weight:bold;color:{cyan};padding:5px}}
        QToolButton{{background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 {raised},stop:1 {surface});border:1px solid {purple};border-radius:9px;padding:6px;font-weight:bold}} QToolButton:hover{{background:{purple};border:1px solid {cyan}}} QToolButton:pressed{{background:{cyan};color:#071020}}
        QPushButton{{background:{raised};border:1px solid {purple};border-radius:7px;padding:8px}} QPushButton:hover{{background:{purple}}}
        QListWidget{{background:{bg};border:1px solid {raised};border-radius:8px;outline:0}} QListWidget::item{{background:{surface};border:1px solid {raised};border-radius:7px;padding:6px;margin:2px}} QListWidget::item:selected{{background:{purple};border:2px solid {cyan}}}
        QStatusBar{{background:{surface};border-top:1px solid {purple}}} QDockWidget{{font-weight:bold}} QDockWidget::title{{background:{surface};padding:7px;color:{cyan}}}
        QLineEdit,QComboBox,QSpinBox,QDoubleSpinBox,QTextBrowser{{background:{surface};border:1px solid {purple};border-radius:5px;padding:5px}}
        QScrollBar:vertical{{background:{surface};width:12px}} QScrollBar::handle:vertical{{background:{purple};border-radius:5px;min-height:25px}}
        """)

    def set_theme(self,t): self.theme=t; self.apply_theme(); self.save_settings()
    def load_start_folder(self):
        folder=self.settings.get('last_folder',str(Path.home()/'Pictures')); self.load_folder(folder)
    def load_folder(self,folder):
        p=Path(folder)
        if not p.is_dir(): return
        self.folder=sorted([str(x) for x in p.iterdir() if x.is_file() and x.suffix.lower() in SUPPORTED],key=lambda x:Path(x).name.lower())
        self.list.blockSignals(True); self.list.clear(); self.thumb_cache.clear()
        for f in self.folder:
            item=QListWidgetItem(Path(f).name); item.setData(Qt.UserRole,f); item.setToolTip(f); self.list.addItem(item)
        self.list.blockSignals(False); self.folder_label.setText(self.tr('Aktueller Ordner:','Current folder:')+'\n'+str(p)); self._thumb_timer.start(100); self.settings['last_folder']=str(p)
        if self.path in self.folder: self.list.setCurrentRow(self.folder.index(self.path))
        elif self.folder: self.list.setCurrentRow(0)
        self.save_settings()
    def choose_folder(self):
        d=QFileDialog.getExistingDirectory(self,self.tr('Bildordner auswählen','Select image folder'),self.settings.get('last_folder',str(Path.home())))
        if d: self.load_folder(d)
    def open_dialog(self):
        f,_=QFileDialog.getOpenFileName(self,self.tr('Bild öffnen','Open image'),self.settings.get('last_folder',str(Path.home())),'Bilder ('+' '.join('*'+x for x in sorted(SUPPORTED))+')')
        if f:self.open_path(f)
    def open_path(self,f):
        try:
            im=Image.open(f); im.seek(0); im.load(); im=ImageOps.exif_transpose(im).convert('RGBA')
        except Exception as e: QMessageBox.critical(self,self.tr('Bild kann nicht geöffnet werden','Could not open image'),str(e)); return
        if self.dirty and not self.ask_save(): return
        self.path=str(Path(f).resolve()); self.image=im; self.undo_stack=[]; self.redo_stack=[]; self.dirty=False; self.zoom_factor=1; self.fit_mode=True
        parent=str(Path(self.path).parent)
        if parent != self.settings.get('last_folder'): self.load_folder(parent)
        else:
            try:self.list.setCurrentRow(self.folder.index(self.path))
            except ValueError: pass
        self.render(); self.update_info(); self.update_actions()
    def select_row(self,row):
        if 0<=row<len(self.folder):
            f=self.folder[row]
            if f!=self.path:self.open_path(f)
            self.make_thumb(row)
    def refresh_thumbs(self):
        """Load only thumbnails whose item rectangles intersect the viewport."""
        if not self.folder or not self.list.count(): return
        viewport = self.list.viewport().rect()
        wanted=[]
        for row in range(self.list.count()):
            rect=self.list.visualItemRect(self.list.item(row))
            if rect.isValid() and rect.intersects(viewport): wanted.append(row)
        # Keep a small buffer around the visible area for smooth scrolling.
        if wanted:
            lo=max(0,min(wanted)-1); hi=min(self.list.count(),max(wanted)+2)
            wanted=list(range(lo,hi))
        wanted=wanted[:self.thumb_limit]
        wanted_set=set(wanted)
        self._thumb_queue=[r for r in wanted if r not in self.thumb_cache]
        for row in list(self.thumb_cache):
            if row not in wanted_set:
                self.thumb_cache.pop(row,None)
                if 0<=row<self.list.count(): self.list.item(row).setIcon(QIcon())
        if self._thumb_queue and not self._thumb_worker.isActive(): self._thumb_worker.start()

    def _thumb_batch(self):
        # Decode a single thumbnail per tick so large photos never freeze scrolling.
        if not self._thumb_queue:
            self._thumb_worker.stop(); return
        row=self._thumb_queue.pop(0)
        self.make_thumb(row)
        if not self._thumb_queue: self._thumb_worker.stop()

    def make_thumb(self,row):
        if self.thumb_cache.get(row) is not None or not (0<=row<len(self.folder)): return
        try:
            with Image.open(self.folder[row]) as im:
                im.seek(0); im.thumbnail((150,100),Image.Resampling.LANCZOS)
                q=self.pil_pixmap(im.convert('RGBA'))
            self.list.item(row).setIcon(QIcon(q)); self.thumb_cache[row]=q
            while len(self.thumb_cache)>self.thumb_limit:
                old=next(iter(self.thumb_cache)); self.thumb_cache.pop(old,None)
                if old!=row and 0<=old<self.list.count(): self.list.item(old).setIcon(QIcon())
        except Exception:
            # Keep a failed item retryable after the next refresh.
            self.thumb_cache.pop(row, None)
    def pil_pixmap(self,im):
        im=im.convert('RGBA'); data=im.tobytes('raw','RGBA'); q=QImage(data,im.width,im.height,im.width*4,QImage.Format_RGBA8888).copy(); return QPixmap.fromImage(q)
    def render(self):
        self.canvas.scene().clear()
        if self.image is None:return
        pm=self.pil_pixmap(self.image); self.canvas.scene().addPixmap(pm); self.canvas.scene().setSceneRect(0,0,pm.width(),pm.height())
        if self.fit_mode:self.canvas.fitInView(self.canvas.sceneRect(),Qt.KeepAspectRatio)
        else:self.canvas.resetTransform(); self.canvas.scale(self.zoom_factor,self.zoom_factor)
        self.update_status()
    def fit(self): self.fit_mode=True; self.render()
    def zoom100(self): self.fit_mode=False; self.zoom_factor=1; self.render()
    def zoom(self,factor): self.fit_mode=False; self.zoom_factor=max(.05,min(8,self.zoom_factor*factor)); self.render()
    def rotate(self,degrees):
        if self.image is not None:self.edit(self.image.rotate(degrees,expand=True))
    def mirror_h(self):
        if self.image is not None:self.edit(ImageOps.mirror(self.image))
    def mirror_v(self):
        # Language changes must never modify the currently opened image.
        for button in getattr(self, 'toolbar_buttons', []):
            button.setText(button.property('de_text') if self.lang == 'de' else button.property('en_text'))
        self.setWindowTitle(f'{APP_NAME} {APP_VERSION}')
        self.info.setWindowTitle(self.tr('Bildinformationen','Image information'))
        if self.image is not None:
            self.update_info(); self.update_status(); self.render()
    def edit(self,new):
        if self.image is None:return
        self.undo_stack.append(self.image.copy()); self.undo_stack=self.undo_stack[-30:]; self.redo_stack.clear(); self.image=new.convert('RGBA'); self.dirty=True; self.render(); self.update_info(); self.update_actions()
    def undo(self):
        if self.undo_stack and self.image is not None:self.redo_stack.append(self.image.copy()); self.image=self.undo_stack.pop(); self.dirty=True; self.render(); self.update_info(); self.update_actions()
    def redo(self):
        if self.redo_stack and self.image is not None:self.undo_stack.append(self.image.copy()); self.image=self.redo_stack.pop(); self.dirty=True; self.render(); self.update_info(); self.update_actions()
    def save_image(self):
        if self.image is None:return
        if not self.path:self.save_as();return
        self.write_image(self.path)
    def save_as(self):
        if self.image is None:return
        f,_=QFileDialog.getSaveFileName(self,self.tr('Bild speichern unter','Save image as'),self.path or '', 'Bilder (*.png *.jpg *.jpeg *.webp *.tif *.bmp)')
        if f:self.write_image(f); self.path=f
    def write_image(self,f):
        try:
            out=self.image
            ext=Path(f).suffix.lower()
            if ext in ('.jpg','.jpeg'):out=out.convert('RGB')
            out.save(f); self.dirty=False; self.update_status(); self.status.showMessage(self.tr('Bild gespeichert: ','Image saved: ')+f,4000)
        except Exception as e:QMessageBox.critical(self,self.tr('Speichern fehlgeschlagen','Save failed'),str(e))
    def ask_save(self):
        dlg=QDialog(self); dlg.setWindowTitle(self.tr('Ungespeicherte Änderungen','Unsaved changes')); dlg.setModal(True)
        layout=QVBoxLayout(dlg); label=QLabel(self.tr('Änderungen am Bild speichern?','Save changes to the image?')); label.setWordWrap(True); layout.addWidget(label)
        buttons=QDialogButtonBox(); close_btn=buttons.addButton(self.tr('Ohne Speichern schließen','Close without saving'),QDialogButtonBox.DestructiveRole); cancel_btn=buttons.addButton(self.tr('Abbrechen','Cancel'),QDialogButtonBox.RejectRole); save_btn=buttons.addButton(self.tr('Speichern','Save'),QDialogButtonBox.AcceptRole)
        layout.addWidget(buttons); choice={'value':'cancel'}
        close_btn.clicked.connect(lambda:(choice.update(value='discard'),dlg.accept()))
        save_btn.clicked.connect(lambda:(choice.update(value='save'),dlg.accept()))
        cancel_btn.clicked.connect(dlg.reject)
        dlg.exec()
        if choice['value']=='save': self.save_image(); return not self.dirty
        return choice['value']=='discard'
    def closeEvent(self,e):
        if self.dirty and not self.ask_save():e.ignore();return
        self.save_settings();e.accept()
    def previous(self):
        if self.folder and self.list.currentRow()>=0:self.list.setCurrentRow((self.list.currentRow()-1)%len(self.folder))
    def next(self):
        if self.folder and self.list.currentRow()>=0:self.list.setCurrentRow((self.list.currentRow()+1)%len(self.folder))
    def adjust(self,name,cls):
        if self.image is None:return
        dlg=QDialog(self); dlg.setWindowTitle(name); form=QFormLayout(dlg)
        value=QDoubleSpinBox(); value.setRange(0.0,4.0); value.setDecimals(1); value.setSingleStep(.1); value.setValue(1.0)
        form.addRow(self.tr('Faktor (1,0 = unverändert):','Factor (1.0 = unchanged):'),value)
        buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel); self.localize_buttons(buttons); form.addRow(buttons)
        buttons.accepted.connect(dlg.accept); buttons.rejected.connect(dlg.reject)
        if dlg.exec():self.edit(cls(self.image).enhance(value.value()))
    def grayscale(self):
        if self.image is not None:self.edit(ImageOps.grayscale(self.image).convert('RGBA'))
    def invert(self):
        if self.image is not None:
            rgb=ImageOps.invert(self.image.convert('RGB')); self.edit(rgb.convert('RGBA'))
    def black_white(self):
        if self.image is not None:self.edit(self.image.convert('L').point(lambda p:255 if p>128 else 0).convert('RGBA'))
    def sharpen(self):
        if self.image is not None:self.edit(self.image.filter(ImageFilter.SHARPEN))
    def blur(self):
        if self.image is not None:self.edit(self.image.filter(ImageFilter.BLUR))
    def draw_dialog(self):
        if self.image is None:
            QMessageBox.information(self, self.tr('Zeichnen','Draw'), self.tr('Bitte zuerst ein Bild öffnen.','Please open an image first.'))
            return
        dlg=QDialog(self); dlg.setWindowTitle(self.tr('Zeichnen','Draw')); form=QFormLayout(dlg)
        color_btn=QPushButton(self.draw_color); color_btn.setStyleSheet(f'background:{self.draw_color};color:white;font-weight:bold;padding:8px')
        chosen={'color':self.draw_color}
        def choose_color():
            c=QColorDialog.getColor(QColor(chosen['color']),dlg,self.tr('Zeichenfarbe auswählen','Choose drawing color'))
            if c.isValid():
                chosen['color']=c.name(); color_btn.setText(c.name()); color_btn.setStyleSheet(f'background:{c.name()};color:white;font-weight:bold;padding:8px')
        color_btn.clicked.connect(choose_color); form.addRow(self.tr('Zeichenfarbe:','Drawing color:'),color_btn)
        size=QSpinBox(); size.setRange(1,100); size.setValue(self.draw_size); size.setSuffix(' px'); form.addRow(self.tr('Pinselgröße:','Brush size:'),size)
        buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel); self.localize_buttons(buttons); form.addRow(buttons); buttons.accepted.connect(dlg.accept); buttons.rejected.connect(dlg.reject)
        if dlg.exec():
            self.draw_color=chosen['color']; self.draw_size=size.value(); self.draw_mode=True; self.draw_active=False
            self.canvas.setCursor(Qt.CrossCursor); self.status.showMessage(self.tr('Zeichenmodus: linke Maustaste gedrückt halten und zeichnen · Rechtsklick beendet','Drawing mode: hold the left mouse button to draw · right-click to finish'))
    def stop_draw(self):
        self.draw_mode=False; self.draw_active=False; self.draw_last=None; self._draw_before=None
        self.canvas.setCursor(Qt.ArrowCursor); self.render(); self.status.showMessage(self.tr('Zeichenmodus beendet','Drawing mode ended'),2500)
    def _draw_point(self, scene_point):
        if self.image is None:return None
        x=int(scene_point.x()); y=int(scene_point.y())
        if 0 <= x < self.image.width and 0 <= y < self.image.height:return (x,y)
        return None
    def draw_begin(self, scene_point):
        pt=self._draw_point(scene_point)
        if pt is None:return
        self._draw_before=self.image.copy(); self.draw_active=True; self.draw_last=pt
        d=ImageDraw.Draw(self.image); r=max(0,self.draw_size//2); x,y=pt
        d.ellipse((x-r,y-r,x+r,y+r),fill=self.draw_color); self.dirty=True; self.render()
    def draw_continue(self, scene_point):
        pt=self._draw_point(scene_point)
        if pt is None or self.draw_last is None:return
        d=ImageDraw.Draw(self.image); w=max(1,self.draw_size)
        d.line([self.draw_last,pt],fill=self.draw_color,width=w)
        r=w//2; x,y=pt; d.ellipse((x-r,y-r,x+r,y+r),fill=self.draw_color)
        self.draw_last=pt; self.dirty=True; self.render()
    def draw_end(self):
        if self.draw_active and self._draw_before is not None:
            self.undo_stack.append(self._draw_before); self.undo_stack=self.undo_stack[-30:]; self.redo_stack.clear()
            self.update_info(); self.update_actions()
        self.draw_active=False; self.draw_last=None; self._draw_before=None
        self.update_status()

    def resize_dialog(self):
        if self.image is None:return
        dlg=QDialog(self); dlg.setWindowTitle(self.tr('Bildgröße ändern','Resize image')); form=QFormLayout(dlg)
        width=QSpinBox(); width.setRange(1,30000); width.setValue(self.image.width)
        height=QSpinBox(); height.setRange(1,30000); height.setValue(self.image.height)
        keep=QCheckBox(self.tr('Seitenverhältnis beibehalten','Keep aspect ratio')); keep.setChecked(True)
        ratio=self.image.width/max(1,self.image.height)
        lock={'busy':False}
        def width_changed(v):
            if keep.isChecked() and not lock['busy']:
                lock['busy']=True; height.setValue(max(1,round(v/ratio))); lock['busy']=False
        def height_changed(v):
            if keep.isChecked() and not lock['busy']:
                lock['busy']=True; width.setValue(max(1,round(v*ratio))); lock['busy']=False
        width.valueChanged.connect(width_changed); height.valueChanged.connect(height_changed)
        form.addRow(self.tr('Breite in Pixel:','Width in pixels:'),width)
        form.addRow(self.tr('Höhe in Pixel:','Height in pixels:'),height)
        form.addRow('',keep)
        buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel); self.localize_buttons(buttons); form.addRow(buttons)
        buttons.accepted.connect(dlg.accept); buttons.rejected.connect(dlg.reject)
        if dlg.exec():self.edit(self.image.resize((width.value(),height.value()),Image.Resampling.LANCZOS))
    def start_crop_mode(self):
        if self.image is None:
            QMessageBox.information(self, self.tr('Zuschneiden','Crop'), self.tr('Bitte zuerst ein Bild öffnen.','Please open an image first.'))
            return
        self.crop_mode=True; self.crop_active=False; self.crop_origin=None; self.crop_rect=None
        self.canvas.setCursor(Qt.CrossCursor)
        self.status.showMessage(self.tr('Mit der linken Maustaste einen Rahmen aufziehen; loslassen zum Zuschneiden. Esc bricht ab.','Drag a rectangle with the left mouse button; release to crop. Esc cancels.'))

    def crop_begin(self, point):
        if self.image is None:return
        self.crop_origin=point; self.crop_active=True
        if self.crop_rect is not None:
            try:self.canvas.scene().removeItem(self.crop_rect)
            except Exception:pass
        self.crop_rect=QGraphicsRectItem(); self.crop_rect.setPen(QPen(QColor('#20c8ff'),2,Qt.DashLine)); self.crop_rect.setBrush(QColor(32,160,255,45)); self.canvas.scene().addItem(self.crop_rect)
        self.crop_update(point)

    def crop_update(self, point):
        if not self.crop_active or self.crop_origin is None or self.crop_rect is None:return
        x1=max(0,min(self.image.width,self.crop_origin.x())); y1=max(0,min(self.image.height,self.crop_origin.y()))
        x2=max(0,min(self.image.width,point.x())); y2=max(0,min(self.image.height,point.y()))
        self.crop_rect.setRect(min(x1,x2),min(y1,y2),abs(x2-x1),abs(y2-y1))

    def crop_finish(self):
        if not self.crop_active:return
        rect=self.crop_rect.rect() if self.crop_rect is not None else None
        if self.crop_rect is not None:
            try:self.canvas.scene().removeItem(self.crop_rect)
            except Exception:pass
        self.crop_rect=None; self.crop_active=False; self.crop_mode=False; self.crop_origin=None; self.canvas.setCursor(Qt.ArrowCursor)
        if rect and rect.width()>=2 and rect.height()>=2:
            box=(max(0,int(rect.left())),max(0,int(rect.top())),min(self.image.width,int(rect.right())),min(self.image.height,int(rect.bottom())))
            if box[2]>box[0] and box[3]>box[1]:self.edit(self.image.crop(box))
        else:self.render()
        self.status.showMessage(self.tr('Zuschneiden beendet','Crop mode ended'),2500)

    def cancel_crop(self):
        if self.crop_rect is not None:
            try:self.canvas.scene().removeItem(self.crop_rect)
            except Exception:pass
        self.crop_rect=None; self.crop_active=False; self.crop_mode=False; self.crop_origin=None; self.canvas.setCursor(Qt.ArrowCursor); self.render()

    def crop_dialog(self):
        self.start_crop_mode()

    def slideshow(self):
        self.slideshow_active=not self.slideshow_active
        if self.slideshow_active:QTimer.singleShot(self.slideshow_interval*1000,self.slide_step)
        else:self.status.showMessage(self.tr('Diashow beendet','Slideshow stopped'),2500)
    def slide_step(self):
        if self.slideshow_active:self.next();QTimer.singleShot(self.slideshow_interval*1000,self.slide_step)
    def toggle_fullscreen(self): self.showNormal() if self.isFullScreen() else self.showFullScreen()
    def toggle_info(self): self.info.setVisible(not self.info.isVisible())
    def update_info(self):
        if self.image is None:return
        f=Path(self.path); size=f.stat().st_size if f.exists() else 0
        self.info_text.setText(f'<b>{self.tr("Datei:","File:")}</b> {f.name}<br><b>{self.tr("Pfad:","Path:")}</b> {self.path}<br><b>{self.tr("Abmessungen:","Dimensions:")}</b> {self.image.width} × {self.image.height} px<br><b>{self.tr("Dateigröße:","File size:")}</b> {size/1024:.1f} KB<br><b>{self.tr("Format:","Format:")}</b> {f.suffix.upper()}')
    def update_status(self):
        if self.image is None:self.status.showMessage(self.tr('Kein Bild geöffnet','No image open'));return
        name=Path(self.path).name if self.path else 'Unbenannt'; self.status.showMessage(f'{name}  |  {self.image.width} × {self.image.height} px  |  {self.zoom_factor*100:.0f} %'+('  |  Änderungen nicht gespeichert' if self.dirty else ''))
    def update_actions(self): self.save_button.setEnabled(self.image is not None); self.save_button.setToolTip(self.tr('Speichert Änderungen in der geöffneten Originaldatei (Strg+S)','Saves changes to the opened original file (Ctrl+S)'))
    def show_context_menu(self,pos):
        m=QMenu(self); entries=[(self.tr('Öffnen…','Open…'),self.open_dialog),(self.tr('Vorheriges Bild','Previous image'),self.previous),(self.tr('Nächstes Bild','Next image'),self.next),None,(self.tr('Speichern','Save'),self.save_image),(self.tr('Speichern unter…','Save as…'),self.save_as),None,(self.tr('Links drehen','Rotate left'),lambda:self.rotate(90)),(self.tr('Rechts drehen','Rotate right'),lambda:self.rotate(-90)),(self.tr('Horizontal spiegeln','Flip horizontally'),self.mirror_h),(self.tr('Vertikal spiegeln','Flip vertically'),self.mirror_v),None,(self.tr('An Fenster anpassen','Fit to window'),self.fit),('100 %',self.zoom100),(self.tr('Bildinformationen','Image information'),self.toggle_info)]
        for entry in entries:
            if entry is None:m.addSeparator()
            else:
                a=m.addAction(entry[0]); a.triggered.connect(entry[1])
        m.exec(pos)
    def thumb_context(self,p):
        item=self.list.itemAt(p)
        if item:self.list.setCurrentItem(item);self.show_context_menu(self.list.mapToGlobal(p))
    def manual(self):
        de = """<h1>Bildbetrachter 0.1.19 – Anleitung</h1>
<h2>1. Überblick</h2><p>Links befindet sich die Dateiliste des geöffneten Bildordners. Rechts sehen Sie das aktuelle Bild. Oben liegt die Werkzeugleiste; unten zeigt die Statusleiste Dateiname, Bildgröße und Zoomstufe. Das Fenster kann in der Größe verändert werden; die Fenstergeometrie wird beim Beenden gespeichert.</p>
<h2>2. Bilder und Ordner öffnen</h2><ul><li><b>Datei → Öffnen</b> oder <b>Strg+O</b>: einzelne Bilddatei auswählen.</li><li><b>Datei → Ordner öffnen</b> oder <b>Strg+Umschalt+O</b>: Ordner laden. Die unterstützten Bilder erscheinen links in der Liste.</li><li>Ein Bild in der Liste anklicken, um es anzuzeigen. Mit den Pfeiltasten bzw. den Funktionen Vorheriges/Nächstes im Kontextmenü zwischen Bildern wechseln.</li><li>Ein Bild kann auch als Programmargument über „Öffnen mit“ gestartet werden.</li></ul>
<h2>3. Speichern – wichtig</h2><ul><li><b>Datei → Speichern</b> oder <b>Strg+S</b>: schreibt die Bearbeitung in die aktuell geöffnete Originaldatei. Das Original wird überschrieben.</li><li><b>Datei → Speichern unter</b> oder <b>Strg+Umschalt+S</b>: speichert eine neue Datei unter einem anderen Namen/Ort.</li><li>Beim Beenden mit ungespeicherten Änderungen fragt das Programm, ob gespeichert, ohne Speichern geschlossen oder abgebrochen werden soll.</li><li>JPEG speichert ohne Transparenz; transparente Bereiche werden beim JPEG-Export in RGB umgewandelt.</li></ul>
<h2>4. Bearbeiten</h2><ul><li><b>Rückgängig – Strg+Z:</b> nimmt den letzten Bearbeitungsschritt zurück.</li><li><b>Wiederholen – Strg+Y:</b> stellt einen zurückgenommenen Schritt wieder her.</li><li><b>Zeichnen:</b> Bearbeiten → Zeichnen. Farbe im Farbdialog wählen und Pinselgröße in Pixeln einstellen. Danach im Bild die linke Maustaste gedrückt halten und zeichnen. Rechtsklick bzw. „Zeichenmodus beenden“ beendet das Zeichnen. Zeichnungen lassen sich über Rückgängig zurücknehmen.</li><li><b>Zuschneiden:</b> Bearbeiten → Zuschneiden (mit Maus) oder Strg+Umschalt+X. Mit linker Maustaste einen Rahmen über den gewünschten Bildbereich ziehen und loslassen. Esc bricht den Modus ab.</li><li><b>Größe ändern:</b> Bearbeiten → Größe ändern. Breite und Höhe in einem Dialog eingeben. Das Seitenverhältnis kann beibehalten oder aufgehoben werden. Das Bild wird auf diese Maße skaliert.</li></ul>
<h2>5. Bildkorrekturen (Menü „Bild“)</h2><ul><li><b>Links/Rechts drehen:</b> dreht das Bild um 90 Grad.</li><li><b>Horizontal/Vertikal spiegeln:</b> spiegelt das Bild an der entsprechenden Achse.</li><li><b>Helligkeit, Kontrast, Farbsättigung:</b> Faktor eingeben. 1,0 bedeutet unverändert; kleinere Werte reduzieren, größere Werte verstärken den Effekt.</li><li><b>Graustufen:</b> entfernt die Farbinformation.</li><li><b>Schwarz-Weiß:</b> wandelt anhand eines Schwellenwerts in reines Schwarz und Weiß um.</li><li><b>Invertieren:</b> kehrt die RGB-Farbwerte um.</li><li><b>Schärfen/Weichzeichnen:</b> wendet einen entsprechenden Filter an.</li></ul>
<h2>6. Ansicht und Zoom</h2><ul><li><b>Mausrad nach oben/unten:</b> hinein- bzw. herauszoomen; der Zoom orientiert sich am Mauszeiger.</li><li><b>Ansicht → An Fenster anpassen</b> oder F: skaliert das ganze Bild passend in den verfügbaren Anzeigebereich.</li><li><b>100 %</b> oder Taste 1: zeigt das Bild in Originalpixelgröße.</li><li><b>Vergrößern/Verkleinern:</b> Strg++ / Strg+-.</li><li><b>Vollbild:</b> F11. Erneut F11 stellt das normale Fenster wieder her.</li><li><b>Bildinformationen:</b> Strg+I oder Ansicht/Werkzeuge → Bildinformationen. Zeigt Dateiname, Pfad, Abmessungen, Dateigröße und Format.</li><li>Zum Verschieben der vergrößerten Ansicht die mittlere Maustaste bzw. die Hand-Verschiebefunktion der Bildfläche verwenden.</li></ul>
<h2>7. Diashow</h2><p>Werkzeuge → Diashow starten/stoppen. Die Diashow wechselt durch die Bilder des geladenen Ordners. Das Intervall wird unter Werkzeuge → Einstellungen zwischen 1 und 60 Sekunden festgelegt und dauerhaft gespeichert. Zum Beenden den Diashow-Befehl erneut wählen.</p>
<h2>8. Kontextmenü</h2><p>Rechtsklick auf die Bildfläche oder einen Eintrag der Vorschauliste öffnet das Kontextmenü. Es bietet Öffnen, vorheriges/nächstes Bild, Speichern/Speichern unter, Drehen, Spiegeln, An Fenster anpassen, 100 % und Bildinformationen.</p>
<h2>9. Einstellungen, Sprache und Design</h2><ul><li><b>Werkzeuge → Einstellungen:</b> Sprache, Design und Diashow-Intervall festlegen. Übernehmen speichert die Auswahl.</li><li><b>Sprache:</b> Deutsch oder English. Alternativ stehen im Menü Werkzeuge direkte Spracheinträge zur Verfügung.</li><li><b>Design:</b> Blau (bunt), Dunkel oder Hell.</li><li>Einstellungen und Fenstergeometrie werden in <code>~/.config/bildbetrachter/settings.ini</code> gespeichert.</li></ul>
<h2>10. Drucken und Hintergrundbild</h2><ul><li><b>Datei → Drucken:</b> übergibt die aktuell geöffnete Datei an die im System zugeordnete Anwendung. Der eigentliche Druckdialog hängt von dieser Anwendung ab.</li><li><b>Als Hintergrundbild setzen:</b> zeigt einen Hinweis; das Hintergrundbild wird über die Desktop-Einstellungen des Systems festgelegt.</li></ul>
<h2>11. Unterstützte Formate</h2><p>Unter anderem BMP, DIB, GIF, JPG/JPEG, PNG, WebP, TIFF, ICO, PPM/PGM/PBM/PNM, XBM, XPM, TGA und PCX. Ob ein spezielles Dateiprofil korrekt gelesen wird, hängt auch von der installierten Pillow-Version ab.</p>
<h2>12. Tastenkürzel</h2><table border='1' cellspacing='0' cellpadding='5'><tr><th>Taste</th><th>Funktion</th></tr><tr><td>Strg+O</td><td>Bild öffnen</td></tr><tr><td>Strg+Umschalt+O</td><td>Ordner öffnen</td></tr><tr><td>Strg+S</td><td>Original überschreiben</td></tr><tr><td>Strg+Umschalt+S</td><td>Speichern unter</td></tr><tr><td>Strg+Z / Strg+Y</td><td>Rückgängig / Wiederholen</td></tr><tr><td>F</td><td>An Fenster anpassen</td></tr><tr><td>1</td><td>100 %</td></tr><tr><td>Strg++ / Strg+-</td><td>Zoom hinein / heraus</td></tr><tr><td>F11</td><td>Vollbild umschalten</td></tr><tr><td>Strg+I</td><td>Bildinformationen</td></tr><tr><td>Strg+Umschalt+X</td><td>Zuschneiden</td></tr><tr><td>Strg+Q</td><td>Beenden</td></tr><tr><td>Esc</td><td>Zuschneidemodus abbrechen</td></tr></table>
<p><b>Hinweis:</b> Speichern überschreibt absichtlich die Originaldatei. Wenn Sie das Original behalten möchten, verwenden Sie vor dem Bearbeiten oder Speichern „Speichern unter“.</p>"""
        en = """<h1>Image Viewer 0.1.19 – User Guide</h1>
<h2>1. Overview</h2><p>The folder's image list is on the left and the current image is on the right. The toolbar is at the top; the status bar shows the file name, image dimensions and zoom level. Window size and position are saved when you exit.</p>
<h2>2. Open images and folders</h2><ul><li><b>File → Open</b> or <b>Ctrl+O</b>: choose one image.</li><li><b>File → Open folder</b> or <b>Ctrl+Shift+O</b>: load a folder. Supported images appear in the left list.</li><li>Click an item in the list to display it. Use previous/next navigation or the context menu to move between images.</li><li>You can also launch the application with an image path, including via the desktop “Open With” action.</li></ul>
<h2>3. Saving – important</h2><ul><li><b>File → Save</b> or <b>Ctrl+S</b>: writes edits to the currently opened original file and overwrites it.</li><li><b>File → Save As</b> or <b>Ctrl+Shift+S</b>: saves a separate copy at another path/name.</li><li>When closing with unsaved edits, the application asks whether to save, discard changes or cancel closing.</li><li>JPEG does not support transparency; transparent images are converted to RGB when exported as JPEG.</li></ul>
<h2>4. Editing</h2><ul><li><b>Undo – Ctrl+Z:</b> reverses the most recent edit.</li><li><b>Redo – Ctrl+Y:</b> reapplies an undone edit.</li><li><b>Draw:</b> Edit → Draw. Choose a color and brush width in pixels. Then hold the left mouse button and draw on the image. Right-click or choose “Exit drawing mode” to stop. Use Undo to remove a drawing.</li><li><b>Crop:</b> Edit → Crop (with mouse) or Ctrl+Shift+X. Drag a rectangle with the left mouse button and release to crop. Esc cancels crop mode.</li><li><b>Resize:</b> Edit → Resize. Enter the new width and height in pixels.</li></ul>
<h2>5. Image adjustments (Image menu)</h2><ul><li><b>Rotate left/right:</b> rotate by 90 degrees.</li><li><b>Flip horizontally/vertically:</b> mirror along the selected axis.</li><li><b>Brightness, Contrast, Saturation:</b> enter a factor. 1.0 means unchanged; lower values reduce and higher values increase the effect.</li><li><b>Grayscale:</b> removes color information.</li><li><b>Black and white:</b> converts the image to pure black and white using a threshold.</li><li><b>Invert:</b> inverts RGB color values.</li><li><b>Sharpen/Blur:</b> applies the corresponding image filter.</li></ul>
<h2>6. View and zoom</h2><ul><li><b>Mouse wheel up/down:</b> zoom in/out, anchored around the pointer.</li><li><b>View → Fit to window</b> or F: fit the whole image into the available viewing area.</li><li><b>100%</b> or 1: show the image at native pixel size.</li><li><b>Zoom in/out:</b> Ctrl++ / Ctrl+-.</li><li><b>Fullscreen:</b> F11 toggles fullscreen.</li><li><b>Image information:</b> Ctrl+I or View/Tools → Image information. Shows file name, path, dimensions, file size and format.</li><li>Pan a zoomed image using the middle mouse button or the view's hand-drag behavior.</li></ul>
<h2>7. Slideshow</h2><p>Choose Tools → Start/stop slideshow. The slideshow advances through images in the loaded folder. Set the interval from 1 to 60 seconds in Tools → Preferences; the value is saved.</p>
<h2>8. Context menu</h2><p>Right-click the image area or an item in the thumbnail list. The menu provides Open, Previous/Next, Save/Save As, Rotate, Flip, Fit to window, 100% and Image information.</p>
<h2>9. Preferences, language and theme</h2><ul><li><b>Tools → Preferences:</b> choose language, theme and slideshow interval. Apply saves the settings.</li><li><b>Language:</b> German or English. Direct language commands are also available in the Tools menu.</li><li><b>Theme:</b> Blue (colorful), Dark or Light.</li><li>Settings and window geometry are stored in <code>~/.config/bildbetrachter/settings.ini</code>.</li></ul>
<h2>10. Print and wallpaper</h2><ul><li><b>File → Print:</b> hands the current file to the system-associated application; the actual print dialog depends on that application.</li><li><b>Set as wallpaper:</b> displays a note; configure the wallpaper through your desktop environment's settings.</li></ul>
<h2>11. Supported formats</h2><p>Including BMP, DIB, GIF, JPG/JPEG, PNG, WebP, TIFF, ICO, PPM/PGM/PBM/PNM, XBM, XPM, TGA and PCX. Support for special profiles also depends on the installed Pillow version.</p>
<h2>12. Keyboard shortcuts</h2><table border='1' cellspacing='0' cellpadding='5'><tr><th>Shortcut</th><th>Action</th></tr><tr><td>Ctrl+O</td><td>Open image</td></tr><tr><td>Ctrl+Shift+O</td><td>Open folder</td></tr><tr><td>Ctrl+S</td><td>Overwrite original</td></tr><tr><td>Ctrl+Shift+S</td><td>Save As</td></tr><tr><td>Ctrl+Z / Ctrl+Y</td><td>Undo / Redo</td></tr><tr><td>F</td><td>Fit to window</td></tr><tr><td>1</td><td>100%</td></tr><tr><td>Ctrl++ / Ctrl+-</td><td>Zoom in / out</td></tr><tr><td>F11</td><td>Toggle fullscreen</td></tr><tr><td>Ctrl+I</td><td>Image information</td></tr><tr><td>Ctrl+Shift+X</td><td>Crop</td></tr><tr><td>Ctrl+Q</td><td>Quit</td></tr><tr><td>Esc</td><td>Cancel crop mode</td></tr></table>
<p><b>Note:</b> Save intentionally overwrites the original file. Use Save As if you want to keep the original unchanged.</p>"""
        dlg=QDialog(self); dlg.setWindowTitle(self.tr('Ausführliche Anleitung','Full user guide')); dlg.resize(820,720)
        layout=QVBoxLayout(dlg); browser=QTextBrowser(); browser.setOpenExternalLinks(True); browser.setHtml(de if self.lang=='de' else en); layout.addWidget(browser)
        close=QDialogButtonBox(QDialogButtonBox.Close); self.localize_buttons(close); close.rejected.connect(dlg.reject); close.accepted.connect(dlg.accept); layout.addWidget(close); dlg.exec()
    def about(self): QMessageBox.about(self,self.tr('Über Bildbetrachter','About Image Viewer'),f'<h2>Bildbetrachter {APP_VERSION}</h2><p>Qt 6 / PySide6 · Goldisoft 2026</p><p>{self.tr("Bildanzeige und Bearbeitung mit Pillow.","Image viewing and editing powered by Pillow.")}</p>')
    def preferences(self):
        dlg=QDialog(self);dlg.setWindowTitle(self.tr('Einstellungen','Preferences'));form=QFormLayout(dlg)
        language=QComboBox();language.addItem('Deutsch','de');language.addItem('English','en');language.setCurrentIndex(max(0,language.findData(self.lang)));form.addRow(self.tr('Sprache:','Language:'),language)
        theme=QComboBox();theme.addItem('Blau (bunt)','blue');theme.addItem('Dunkel','dark');theme.addItem('Hell','light');theme.setCurrentIndex(max(0,theme.findData(self.theme)));form.addRow(self.tr('Design:','Theme:'),theme)
        interval=QSpinBox();interval.setRange(1,60);interval.setSuffix(' Sekunden' if self.lang=='de' else ' seconds');interval.setValue(self.slideshow_interval);form.addRow(self.tr('Diashow – Bildwechsel alle:','Slideshow – change image every:'),interval)
        buttons=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel);self.localize_buttons(buttons,accept=self.tr('Übernehmen','Apply'));form.addRow(buttons);buttons.accepted.connect(dlg.accept);buttons.rejected.connect(dlg.reject)
        if dlg.exec():
            self.slideshow_interval=interval.value();self.set_theme(theme.currentData());self.set_language(language.currentData());self.save_settings()
    def print_image(self):
        if self.path:subprocess.Popen(['xdg-open',self.path])
    def wallpaper(self):
        if self.path:self.status.showMessage(self.tr('Hintergrundbild: bitte über die Desktop-Einstellungen festlegen.','Set the wallpaper in your desktop settings.'),5000)
    def keyPressEvent(self,e):
        if e.key()==Qt.Key_Left:self.previous()
        elif e.key()==Qt.Key_Right:self.next()
        elif e.key()==Qt.Key_Escape and self.crop_mode:self.cancel_crop()
        elif e.key()==Qt.Key_Escape and self.draw_mode:self.stop_draw()
        elif e.key()==Qt.Key_Escape and self.isFullScreen():self.showNormal()
        else:super().keyPressEvent(e)

if __name__=='__main__':
    # Use Qt's own file dialog instead of the desktop-native GTK/portal dialog,
    # whose button labels can remain English regardless of the app language.
    QApplication.setAttribute(Qt.AA_DontUseNativeDialogs, True)
    app=QApplication(sys.argv); app.setApplicationName(APP_NAME); app.setApplicationVersion(APP_VERSION)
    # Load Qt's German widget translations when available (Debian package:
    # qt6-translations-l10n). Keep the translator alive for the app lifetime.
    qt_translator = QTranslator(app)
    translations_path = QLibraryInfo.path(QLibraryInfo.TranslationsPath)
    if qt_translator.load('qtbase_de', translations_path):
        app.installTranslator(qt_translator)
    QLocale.setDefault(QLocale(QLocale.German, QLocale.Germany))
    icon=Path(__file__).parent/'icons'/'bild_icon_128.png'
    if icon.exists():app.setWindowIcon(QIcon(str(icon)))
    w=ImageViewer();w.show();sys.exit(app.exec())

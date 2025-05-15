import os
import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QToolBar, QAction, QLineEdit, QWidget,
    QVBoxLayout, QTabWidget, QPushButton, QListWidget, QLabel,
    QColorDialog, QSizePolicy, QFileDialog, QMessageBox
)
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile, QWebEngineSettings, QWebEnginePage
from PyQt5.QtCore import QUrl, Qt, QSize, QFileInfo
from PyQt5.QtGui import QFont

os.environ['QTWEBENGINE_PROFILE_STORAGE'] = os.path.join(os.getcwd(), 'browser_cache')

THEME_FILE = "theme_settings.txt"
HISTORY_FILE = "history.txt"
BOOKMARKS_FILE = "bookmarks.txt"
SESSION_FILE = "session.txt"  # NEW for session restore

def read_about_file():
    about_file_path = os.path.join(os.getcwd(), 'about.py')
    if os.path.exists(about_file_path):
        with open(about_file_path, 'r') as file:
            return file.read()
    return "About file not found."

class BrowserTab(QWidget):
    def __init__(self, parent=None, incognito=False):
        super().__init__(parent)
        self.incognito = incognito
        self.browser = QWebEngineView()

        if self.incognito:
            self.profile = QWebEngineProfile()
            self.profile.setPersistentCookiesPolicy(QWebEngineProfile.NoPersistentCookies)
            self.profile.setCachePath("")
            self.profile.setPersistentStoragePath("")
            self.profile.settings().setAttribute(QWebEngineSettings.LocalStorageEnabled, False)
            self.browser.setPage(QWebEnginePage(self.profile, self.browser))
        else:
            # Normal profile
            self.profile = QWebEngineProfile.defaultProfile()

        # Enable plugins and JS
        self.browser.settings().setAttribute(QWebEngineSettings.PluginsEnabled, True)
        self.browser.settings().setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        self.browser.settings().setAttribute(QWebEngineSettings.FullScreenSupportEnabled, True)
        self.browser.settings().setAttribute(QWebEngineSettings.LocalStorageEnabled, True)
        self.browser.settings().setAttribute(QWebEngineSettings.XSSAuditingEnabled, True)
        self.browser.settings().setAttribute(QWebEngineSettings.ErrorPageEnabled, True)
        self.browser.settings().setAttribute(QWebEngineSettings.WebGLEnabled, True)

        # NEW: Block popups by default (basic)
        self.profile.setHttpUserAgent("PhoenixRoseWeb/1.0")
        self.profile.setRequestInterceptor(self)  # We'll add a dummy interceptor below

        self.browser.page().featurePermissionRequested.connect(self.onFeaturePermissionRequested)  # Allow features like geolocation

        self.browser.setUrl(QUrl("https://www.google.com"))
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.browser)
        self.setLayout(layout)

    def onFeaturePermissionRequested(self, url, feature):
        # Auto deny any feature requests for privacy/security
        self.browser.page().setFeaturePermission(url, feature, QWebEnginePage.PermissionDeniedByUser)

class Browser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PhoenixRose Web")
        self.setGeometry(100, 100, 1200, 800)
        self.dark_mode = False
        self.incognito_mode = False
        self.custom_primary_color = None  # store custom theme color

        self.history = []
        self.bookmarks = []

        self._create_menu_bar()
        self._create_navbar()
        self._create_bookmarks_bar()
        self._create_tab_widget()
        self._create_download_manager()  # NEW

        self.load_history()
        self.load_bookmarks()
        self.load_theme()
        self.load_session()  # NEW: restore tabs

        if self.tabs.count() == 0:
            self.add_new_tab()
        self.update_bookmarks_bar()

    def closeEvent(self, event):
        self.save_history()
        self.save_bookmarks()
        self.save_session()  # NEW save session on close
        event.accept()

    # ====== SESSION RESTORE NEW =======
    def save_session(self):
        try:
            with open(SESSION_FILE, "w") as f:
                for i in range(self.tabs.count()):
                    tab = self.tabs.widget(i)
                    url = tab.browser.url().toString()
                    incognito = "1" if tab.incognito else "0"
                    f.write(f"{url},{incognito}\n")
        except Exception as e:
            print(f"Error saving session: {e}")

    def load_session(self):
        if os.path.exists(SESSION_FILE):
            try:
                with open(SESSION_FILE, "r") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        parts = line.split(",", 1)
                        url = parts[0]
                        incognito = parts[1] == "1" if len(parts) > 1 else False
                        self.add_new_tab(url=url, incognito=incognito)
            except Exception as e:
                print(f"Error loading session: {e}")

    # ====== DOWNLOAD MANAGER NEW =======
    def _create_download_manager(self):
        self.downloads = []  # keep track of ongoing downloads

    def _create_menu_bar(self):
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("File")
        new_tab_action = QAction("New Tab", self)
        new_tab_action.triggered.connect(lambda: self.add_new_tab())
        file_menu.addAction(new_tab_action)

        close_tab_action = QAction("Close Tab", self)
        close_tab_action.triggered.connect(lambda: self.close_tab(self.tabs.currentIndex()))
        file_menu.addAction(close_tab_action)

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        bookmarks_menu = menu_bar.addMenu("Bookmarks")
        add_bookmark_action = QAction("Add Bookmark", self)
        add_bookmark_action.triggered.connect(self.add_bookmark)
        bookmarks_menu.addAction(add_bookmark_action)

        manage_bookmarks_action = QAction("Manage Bookmarks", self)
        manage_bookmarks_action.triggered.connect(self.manage_bookmarks)
        bookmarks_menu.addAction(manage_bookmarks_action)

        history_menu = menu_bar.addMenu("History")
        show_history_action = QAction("Show History", self)
        show_history_action.triggered.connect(self.show_history)
        history_menu.addAction(show_history_action)

        view_menu = menu_bar.addMenu("View")
        toggle_incognito_action = QAction("Toggle Incognito Mode", self)
        toggle_incognito_action.triggered.connect(self.toggle_incognito_mode)
        view_menu.addAction(toggle_incognito_action)

        toggle_dark_mode_action = QAction("Toggle Dark Mode", self)
        toggle_dark_mode_action.triggered.connect(self.toggle_dark_mode)
        view_menu.addAction(toggle_dark_mode_action)

        dev_tools_action = QAction("Toggle Developer Tools", self)  # NEW
        dev_tools_action.triggered.connect(self.toggle_dev_tools)
        view_menu.addAction(dev_tools_action)

        themes_menu = menu_bar.addMenu("Themes")
        light_theme_action = QAction("Light", self)
        light_theme_action.triggered.connect(lambda: self.apply_preset_theme("light"))
        themes_menu.addAction(light_theme_action)

        dark_theme_action = QAction("Dark", self)
        dark_theme_action.triggered.connect(lambda: self.apply_preset_theme("dark"))
        themes_menu.addAction(dark_theme_action)

        blue_theme_action = QAction("Blue", self)
        blue_theme_action.triggered.connect(lambda: self.apply_preset_theme("blue"))
        themes_menu.addAction(blue_theme_action)

        purple_theme_action = QAction("Purple", self)
        purple_theme_action.triggered.connect(lambda: self.apply_preset_theme("purple"))
        themes_menu.addAction(purple_theme_action)

        custom_theme_action = QAction("Custom Color...", self)
        custom_theme_action.triggered.connect(self.open_color_picker)
        themes_menu.addAction(custom_theme_action)

        help_menu = menu_bar.addMenu("Help")
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def _create_navbar(self):
        navbar = QToolBar()
        navbar.setMovable(False)
        navbar.setIconSize(QSize(16, 16))
        self.addToolBar(navbar)

        self.back_btn = QAction("←", self)
        self.back_btn.triggered.connect(self.go_back)
        navbar.addAction(self.back_btn)

        self.forward_btn = QAction("→", self)
        self.forward_btn.triggered.connect(self.go_forward)
        navbar.addAction(self.forward_btn)

        self.reload_btn = QAction("⟳", self)
        self.reload_btn.triggered.connect(self.reload_page)
        navbar.addAction(self.reload_btn)

        self.stop_btn = QAction("✕", self)  # NEW stop button to replace reload when loading
        self.stop_btn.triggered.connect(self.stop_loading)
        navbar.addAction(self.stop_btn)
        self.stop_btn.setVisible(False)  # start hidden

        home_btn = QAction("🏠", self)
        home_btn.triggered.connect(self.navigate_home)
        navbar.addAction(home_btn)

        self.url_bar = QLineEdit()
        self.url_bar.setPlaceholderText("Search or enter website name")
        self.url_bar.setFont(QFont("San Francisco", 12))
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        self.url_bar.setMaximumWidth(900)

        navbar.addWidget(self.url_bar)

        self.new_tab_btn = QPushButton("+")
        self.new_tab_btn.setFixedSize(25, 25)
        self.new_tab_btn.setToolTip("Open new tab")
        self.new_tab_btn.clicked.connect(self.add_new_tab)
        self.new_tab_btn.setStyleSheet("""
            QPushButton {
                font-weight: bold;
                font-size: 18px;
                color: #333;
                background-color: #eee;
                border: 1px solid #ccc;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #ddd;
            }
        """)
        navbar.addWidget(self.new_tab_btn)

    def _create_bookmarks_bar(self):
        self.bookmark_toolbar = QToolBar("Bookmarks")
        self.bookmark_toolbar.setMovable(False)
        self.addToolBar(Qt.BottomToolBarArea, self.bookmark_toolbar)

    def _create_tab_widget(self):
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.current_tab_changed)
        self.setCentralWidget(self.tabs)

    def add_new_tab(self, url=None, incognito=False):
        new_tab = BrowserTab(incognito=incognito)
        if url:
            new_tab.browser.setUrl(QUrl(url))
        else:
            new_tab.browser.setUrl(QUrl("https://www.google.com"))

        i = self.tabs.addTab(new_tab, "New Tab")
        self.tabs.setCurrentIndex(i)

        # Connect signals for URL change and title update
        new_tab.browser.urlChanged.connect(lambda qurl, tab=new_tab: self.update_urlbar(qurl, tab))
        new_tab.browser.loadFinished.connect(lambda _, tab=new_tab: self.update_tab_title(tab))
        new_tab.browser.loadFinished.connect(lambda _, tab=new_tab: self.add_to_history(tab.browser.url().toString()))

        # NEW: Show stop/reload toggle
        new_tab.browser.loadStarted.connect(lambda tab=new_tab: self.toggle_reload_stop(True))
        new_tab.browser.loadFinished.connect(lambda tab=new_tab: self.toggle_reload_stop(False))

        # NEW: Hook download requests
        new_tab.browser.page().profile().downloadRequested.connect(self.handle_download)

        self.apply_theme_to_tab(new_tab)
        return new_tab

    def toggle_reload_stop(self, loading):
        self.reload_btn.setVisible(not loading)
        self.stop_btn.setVisible(loading)

    def stop_loading(self):
        current_tab = self.tabs.currentWidget()
        if current_tab:
            current_tab.browser.stop()

    def close_tab(self, i):
        if self.tabs.count() < 2:
            return
        tab = self.tabs.widget(i)
        self.tabs.removeTab(i)
        tab.deleteLater()

    def current_tab_changed(self, i):
        tab = self.tabs.widget(i)
        if tab:
            self.update_urlbar(tab.browser.url(), tab)
            self.apply_theme_to_tab(tab)

    def update_urlbar(self, qurl, tab):
        if tab != self.tabs.currentWidget():
            return
        url = qurl.toString()
        self.url_bar.setText(url)
        self.url_bar.setCursorPosition(0)

    def update_tab_title(self, tab):
        i = self.tabs.indexOf(tab)
        if i != -1:
            title = tab.browser.page().title()
            self.tabs.setTabText(i, title if title else "New Tab")

    def navigate_to_url(self):
        url = self.url_bar.text().strip()
        if not url:
            return
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "http://" + url
        current_tab = self.tabs.currentWidget()
        if current_tab:
            current_tab.browser.setUrl(QUrl(url))

    def go_back(self):
        current_tab = self.tabs.currentWidget()
        if current_tab and current_tab.browser.history().canGoBack():
            current_tab.browser.back()

    def go_forward(self):
        current_tab = self.tabs.currentWidget()
        if current_tab and current_tab.browser.history().canGoForward():
            current_tab.browser.forward()

    def reload_page(self):
        current_tab = self.tabs.currentWidget()
        if current_tab:
            current_tab.browser.reload()

    def navigate_home(self):
        current_tab = self.tabs.currentWidget()
        if current_tab:
            current_tab.browser.setUrl(QUrl("https://www.google.com"))

    # ===== BOOKMARKS =====
    def add_bookmark(self):
        current_tab = self.tabs.currentWidget()
        if current_tab:
            url = current_tab.browser.url().toString()
            title = current_tab.browser.page().title()
            if (title, url) not in self.bookmarks:
                self.bookmarks.append((title, url))
                self.update_bookmarks_bar()

    def update_bookmarks_bar(self):
        self.bookmark_toolbar.clear()
        for title, url in self.bookmarks:
            btn = QPushButton(title)
            btn.setToolTip(url)
            btn.setStyleSheet("background-color: #e0e0e0; margin: 2px; padding: 2px 8px; border-radius: 4px;")
            btn.clicked.connect(lambda checked, url=url: self.open_bookmark(url))
            self.bookmark_toolbar.addWidget(btn)

    def open_bookmark(self, url):
        self.add_new_tab(url)

    def manage_bookmarks(self):
        dlg = QWidget()
        dlg.setWindowTitle("Manage Bookmarks")
        dlg.setGeometry(300, 300, 400, 400)
        layout = QVBoxLayout()

        list_widget = QListWidget()
        for title, url in self.bookmarks:
            list_widget.addItem(f"{title} - {url}")
        layout.addWidget(list_widget)

        def remove_selected():
            selected = list_widget.currentRow()
            if selected >= 0:
                del self.bookmarks[selected]
                list_widget.takeItem(selected)
                self.update_bookmarks_bar()

        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(remove_selected)
        layout.addWidget(remove_btn)

        dlg.setLayout(layout)
        dlg.show()

    # ===== HISTORY =====
    def add_to_history(self, url):
        if url and url not in self.history:
            self.history.append(url)
            self.save_history()

    def show_history(self):
        dlg = QWidget()
        dlg.setWindowTitle("History")
        dlg.setGeometry(300, 300, 400, 400)
        layout = QVBoxLayout()
        list_widget = QListWidget()
        for url in self.history:
            list_widget.addItem(url)
        layout.addWidget(list_widget)

        def open_selected():
            selected = list_widget.currentRow()
            if selected >= 0:
                url = self.history[selected]
                self.add_new_tab(url)

        open_btn = QPushButton("Open Selected")
        open_btn.clicked.connect(open_selected)
        layout.addWidget(open_btn)

        dlg.setLayout(layout)
        dlg.show()

    def save_history(self):
        try:
            with open(HISTORY_FILE, "w") as f:
                for url in self.history:
                    f.write(url + "\n")
        except Exception as e:
            print(f"Error saving history: {e}")

    def load_history(self):
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r") as f:
                    for line in f:
                        url = line.strip()
                        if url:
                            self.history.append(url)
            except Exception as e:
                print(f"Error loading history: {e}")

    def save_bookmarks(self):
        try:
            with open(BOOKMARKS_FILE, "w") as f:
                for title, url in self.bookmarks:
                    f.write(f"{title}|||{url}\n")
        except Exception as e:
            print(f"Error saving bookmarks: {e}")

    def load_bookmarks(self):
        if os.path.exists(BOOKMARKS_FILE):
            try:
                with open(BOOKMARKS_FILE, "r") as f:
                    for line in f:
                        parts = line.strip().split("|||")
                        if len(parts) == 2:
                            self.bookmarks.append((parts[0], parts[1]))
            except Exception as e:
                print(f"Error loading bookmarks: {e}")

    # ===== THEME =====
    def load_theme(self):
        if os.path.exists(THEME_FILE):
            try:
                with open(THEME_FILE, "r") as f:
                    mode = f.readline().strip()
                    color = f.readline().strip()
                    if mode == "dark":
                        self.dark_mode = True
                    else:
                        self.dark_mode = False
                    if color:
                        self.custom_primary_color = color
                    self.apply_theme()
            except Exception as e:
                print(f"Error loading theme: {e}")

    def save_theme(self):
        try:
            with open(THEME_FILE, "w") as f:
                f.write("dark\n" if self.dark_mode else "light\n")
                f.write(self.custom_primary_color if self.custom_primary_color else "")
        except Exception as e:
            print(f"Error saving theme: {e}")

    def toggle_dark_mode(self):
        self.dark_mode = not self.dark_mode
        self.apply_theme()
        self.save_theme()

    def apply_preset_theme(self, theme):
        themes = {
            "light": (False, None),
            "dark": (True, None),
            "blue": (False, "#2196f3"),
            "purple": (False, "#9c27b0"),
        }
        if theme in themes:
            self.dark_mode, self.custom_primary_color = themes[theme]
            self.apply_theme()
            self.save_theme()

    def open_color_picker(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.custom_primary_color = color.name()
            self.apply_theme()
            self.save_theme()

    def apply_theme(self):
        if self.dark_mode:
            self.setStyleSheet("""
                QMainWindow { background-color: #121212; color: #eee; }
                QToolBar { background-color: #222; }
                QPushButton { background-color: #333; color: #eee; }
                QLineEdit { background-color: #222; color: #eee; }
            """)
        else:
            base_color = self.custom_primary_color if self.custom_primary_color else "#f0f0f0"
            self.setStyleSheet(f"""
                QMainWindow {{ background-color: {base_color}; color: #000; }}
                QToolBar {{ background-color: #ddd; }}
                QPushButton {{ background-color: #eee; color: #000; }}
                QLineEdit {{ background-color: #fff; color: #000; }}
            """)
        # Apply theme to all tabs
        for i in range(self.tabs.count()):
            self.apply_theme_to_tab(self.tabs.widget(i))

    def apply_theme_to_tab(self, tab):
        if self.dark_mode:
            tab.browser.page().setBackgroundColor(Qt.black)
        else:
            tab.browser.page().setBackgroundColor(Qt.white)

    # ===== DEVELOPER TOOLS NEW =====
    def toggle_dev_tools(self):
        current_tab = self.tabs.currentWidget()
        if not current_tab:
            return
        page = current_tab.browser.page()
        if hasattr(self, "_dev_tools") and self._dev_tools is not None:
            self._dev_tools.close()
            self._dev_tools = None
        else:
            self._dev_tools = QWebEngineView()
            self._dev_tools.setWindowTitle("Developer Tools")
            self._dev_tools.resize(800, 600)
            page.setDevToolsPage(self._dev_tools.page())
            self._dev_tools.show()

    # ===== INCOGNITO MODE =====
    def toggle_incognito_mode(self):
        self.incognito_mode = not self.incognito_mode
        # New tab with incognito or normal
        self.add_new_tab(incognito=self.incognito_mode)

    # ===== ABOUT =====
    def show_about(self):
        about_text = read_about_file()
        dlg = QMessageBox(self)
        dlg.setWindowTitle("About PhoenixRose Web")
        dlg.setText(about_text)
        dlg.setStandardButtons(QMessageBox.Ok)
        dlg.exec_()

    # ===== DOWNLOAD HANDLER NEW =====
    def handle_download(self, download):
        path, _ = QFileDialog.getSaveFileName(self, "Save File", download.path())
        if path:
            download.setPath(path)
            download.accept()
            download.finished.connect(lambda: self.download_finished(download))

    def download_finished(self, download):
        if download.state() == download.DownloadCompleted:
            QMessageBox.information(self, "Download Completed", f"Downloaded: {download.path()}")
        elif download.state() == download.DownloadCancelled:
            QMessageBox.warning(self, "Download Cancelled", "Download was cancelled.")
        elif download.state() == download.DownloadInterrupted:
            QMessageBox.warning(self, "Download Interrupted", "Download was interrupted.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("PhoenixRose Web")
    window = Browser()
    window.show()
    sys.exit(app.exec_())

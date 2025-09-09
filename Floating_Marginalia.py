#Anton Vladimir

import sys
import os
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QTextEdit, QFileDialog
)
from PyQt6.QtGui import QFontDatabase, QFont
from PyQt6.QtCore import Qt, QSettings, QPoint, QTimer, QEvent

# --- CONFIGURATION ---
ORGANIZATION_NAME = "YourWorkshop"
APPLICATION_NAME = "ThoughtCatcher"
DEFAULT_FONT_FAMILY = " "
DEFAULT_FONT_SIZE = 20
AUTOSAVE_INTERVAL_MS = 1500


class ThoughtCatcher(QWidget):
    def __init__(self):
        super().__init__()
        self.settings = QSettings(ORGANIZATION_NAME, APPLICATION_NAME)
        # ... (rest of init is the same) ...
        self.notes_directory = ""
        self.current_session_file = ""
        self.drag_position = QPoint()
        self.autosave_timer = QTimer(self)
        self.autosave_timer.setSingleShot(True)
        self.autosave_timer.timeout.connect(self.save_current_note)
        self.init_ui()
        self.load_settings_and_start()

    def init_ui(self):
        self.setWindowTitle(APPLICATION_NAME)
        # ... (window flags are the same) ...
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.main_container = QWidget(self)
        self.main_container.setObjectName("mainContainer")
        self.main_container.setProperty("hasFocus", True)
        container_layout = QVBoxLayout(self.main_container)
        container_layout.setContentsMargins(20, 10, 20, 10)

        # We go back to a standard QTextEdit because the parent will filter its events.
        self.text_edit = QTextEdit(self)
        self.text_edit.setPlaceholderText("...")
        self.text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # --- THE CRITICAL STEP: Install the event filter ---
        self.text_edit.installEventFilter(self)

        container_layout.addWidget(self.text_edit)
        main_window_layout = QVBoxLayout(self)
        main_window_layout.setContentsMargins(0, 0, 0, 0)
        main_window_layout.addWidget(self.main_container)
        self.apply_styles()
        self.text_edit.textChanged.connect(self.on_text_changed)

    # --- THE NEW EVENT FILTER METHOD ---
    def eventFilter(self, source, event):
        # This method is the "security guard" for the text_edit.
        if source is self.text_edit:
            # Check if the event is a single mouse press
            if event.type() == QEvent.Type.MouseButtonPress:
                # If it is, we handle it and stop it from reaching the text_edit
                self.mousePressEvent(event)  # Use the main window's logic
                return True  # True means "event handled, stop processing"

            # Check if the event is a double-click
            elif event.type() == QEvent.Type.MouseButtonDblClick:
                # If it is, we let it pass through to the text_edit
                return False  # False means "let the event continue to its destination"

        # For all other events, let them pass through normally
        return super().eventFilter(source, event)

    def mousePressEvent(self, event):
        # This now handles clicks on the border AND clicks that the eventFilter
        # forwards from the text_edit.
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    # The rest of the code is identical to the previous versions.
    # ... [Paste the remaining correct methods from v7.1 here] ...
    def focusInEvent(self, event):
        self.update_focus_style(True)
        self.text_edit.setFocus()
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        self.update_focus_style(False)
        super().focusOutEvent(event)

    def update_focus_style(self, has_focus):
        self.main_container.setProperty("hasFocus", has_focus)
        self.style().polish(self.main_container)

    def on_text_changed(self):
        self.update_window_height()
        self.autosave_timer.start(AUTOSAVE_INTERVAL_MS)

    def apply_styles(self):
        self.setStyleSheet("""
            #mainContainer[hasFocus="true"] {
                background-color: rgba(26, 26, 26, 0.95); border: 1px solid #777; border-radius: 6px;
            }
            #mainContainer[hasFocus="false"] {
                background-color: rgba(26, 26, 26, 0.85); border: 1px solid #444; border-radius: 6px;
            }
            QTextEdit {
                background-color: transparent; border: none; color: #E0E0E0; padding: 0px;
                font-family: '""" + DEFAULT_FONT_FAMILY + """'; font-size: """ + str(DEFAULT_FONT_SIZE) + """px;
            }
        """)
        font = QFont(DEFAULT_FONT_FAMILY, DEFAULT_FONT_SIZE)
        self.text_edit.setFont(font)

    def load_settings_and_start(self):
        self.notes_directory = self.settings.value("notes_directory", "")
        if not self.notes_directory or not os.path.isdir(self.notes_directory):
            self.notes_directory = QFileDialog.getExistingDirectory(self, "Select a folder to store your notes")
            if self.notes_directory:
                self.settings.setValue("notes_directory", self.notes_directory)
            else:
                QApplication.quit(); return
        pos = self.settings.value("window_position", QPoint(100, 100))
        self.move(pos)
        self.load_last_note()
        self.update_window_height()
        self.text_edit.setFocus()

    def load_last_note(self):
        try:
            files = [os.path.join(self.notes_directory, f) for f in os.listdir(self.notes_directory) if
                     f.startswith("note_") and f.endswith(".md")]
            if not files: self.start_new_session(save_previous=False); return
            latest_file = max(files, key=os.path.getmtime)
            self.current_session_file = latest_file
            with open(latest_file, 'r', encoding='utf-8') as f:
                self.text_edit.setPlainText(f.read())
            self.text_edit.moveCursor(self.text_edit.textCursor().MoveOperation.End)
            print(f"Loaded last session: {os.path.basename(latest_file)}")
        except Exception as e:
            print(f"Could not load last note, starting new session. Error: {e}")
            self.start_new_session(save_previous=False)

    def start_new_session(self, save_previous=True):
        if save_previous: self.save_current_note()
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.current_session_file = os.path.join(self.notes_directory, f"note_{timestamp}.md")
        self.text_edit.clear()
        self.save_current_note()
        print(f"New session started. Saving to: {self.current_session_file}")

    def save_current_note(self):
        content = self.text_edit.toPlainText()
        if self.current_session_file:
            try:
                with open(self.current_session_file, 'w', encoding='utf-8') as f:
                    f.write(content)
            except Exception as e:
                print(f"Error autosaving note: {e}")

    def update_window_height(self):
        font_metrics = self.text_edit.fontMetrics()
        margins = self.main_container.layout().contentsMargins()
        vertical_padding = margins.top() + margins.bottom()
        doc_height = self.text_edit.document().size().height()
        min_height = (font_metrics.height() * 1) + vertical_padding
        max_height = (font_metrics.height() * 3) + vertical_padding
        new_height = min(max(doc_height + vertical_padding, min_height), max_height)
        self.setFixedHeight(int(new_height))
        if self.width() < 300: self.setFixedWidth(500)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_F1:
            self.start_new_session()
        elif event.key() == Qt.Key.Key_Escape:
            self.hide()
        super().keyPressEvent(event)

    def closeEvent(self, event):
        self.autosave_timer.stop()
        self.save_current_note()
        self.settings.setValue("window_position", self.pos())
        super().closeEvent(event)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    QFontDatabase.addApplicationFont("GT-America-LCGV-Standard-Medium.ttf")
    catcher = ThoughtCatcher()
    catcher.show()

    sys.exit(app.exec())

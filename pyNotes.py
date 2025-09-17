import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QPlainTextEdit, QVBoxLayout, QWidget,
    QFileDialog, QMessageBox, QStatusBar, QLabel, QToolBar, QDialog,
    QLineEdit, QPushButton, QHBoxLayout, QFontDialog, QStyle, QTabWidget, QTextEdit, QFrame
)
from PyQt6.QtGui import QAction, QFont, QIcon, QTextCursor, QPainter, QColor, QTextFormat, QPalette
from PyQt6.QtCore import Qt, QRect, QSize
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog

import os

class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.codeEditor = editor

    def sizeHint(self):
        return QSize(self.codeEditor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event):
        self.codeEditor.lineNumberAreaPaintEvent(event)

class CodeEditor(QPlainTextEdit):
    def __init__(self):
        super().__init__()
        self.lineNumberArea = LineNumberArea(self)

        self.setStyleSheet("background-color: transparent; border: none;")

        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        self.cursorPositionChanged.connect(self.highlightCurrentLine)

        self.updateLineNumberAreaWidth(0)
       

    def lineNumberAreaWidth(self):
        digits = 1
        max_value = max(1, self.blockCount())
        while max_value >= 10:
            max_value /= 10
            digits += 1
        space = 3 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def updateLineNumberAreaWidth(self, _):
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

    def updateLineNumberArea(self, rect, dy):
        if dy:
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(0, rect.y(), self.lineNumberArea.width(), rect.height())

        if rect.contains(self.viewport().rect()):
            self.updateLineNumberAreaWidth(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.lineNumberArea.setGeometry(QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height()))

    def lineNumberAreaPaintEvent(self, event):
        painter = QPainter(self.lineNumberArea)

        painter.fillRect(event.rect(), QColor(0, 0, 0))

        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()

        height = self.fontMetrics().height()
        while block.isValid() and (top <= event.rect().bottom()):
            if block.isVisible() and (bottom >= event.rect().top()):
                number = str(blockNumber + 1)
                painter.setPen(QColor(255, 255, 255))
                font = QFont("Courier New", self.font().pointSize(), QFont.Weight.Bold)
                painter.setFont(font)
                rect = QRect(0, int(top), self.lineNumberArea.width(), int(height))
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, number)

            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            blockNumber += 1

    def highlightCurrentLine(self):
        extraSelections = []

        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            lineColor = QColor(0, 0, 0, 0)

            selection.format.setBackground(lineColor)
            selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extraSelections.append(selection)
        self.setExtraSelections(extraSelections)

class FindReplaceDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Find and Replace')
        self.setModal(True)

        layout = QVBoxLayout(self)

        find_layout = QHBoxLayout()
        find_layout.addWidget(QLabel('Find:'))
        self.find_edit = QLineEdit()
        find_layout.addWidget(self.find_edit)
        layout.addLayout(find_layout)

        replace_layout = QHBoxLayout()
        replace_layout.addWidget(QLabel('Replace:'))
        self.replace_edit = QLineEdit()
        replace_layout.addWidget(self.replace_edit)
        layout.addLayout(replace_layout)

        button_layout = QHBoxLayout()
        self.find_button = QPushButton('Find')
        self.find_button.clicked.connect(self.find_next)
        button_layout.addWidget(self.find_button)

        self.replace_button = QPushButton('Replace')
        self.replace_button.clicked.connect(self.replace)
        button_layout.addWidget(self.replace_button)

        self.replace_all_button = QPushButton('Replace All')
        self.replace_all_button.clicked.connect(self.replace_all)
        button_layout.addWidget(self.replace_all_button)

        self.close_button = QPushButton('Close')
        self.close_button.clicked.connect(self.close)
        button_layout.addWidget(self.close_button)

        layout.addLayout(button_layout)

        self.text_edit = parent.current_editor()

    def find_next(self):
        text = self.find_edit.text()
        if text:
            cursor = self.text_edit.textCursor()
            if cursor.hasSelection():
                cursor.setPosition(cursor.selectionEnd())
            found = self.text_edit.find(text)
            if not found:
                cursor.movePosition(QTextCursor.MoveOperation.Start)
                self.text_edit.setTextCursor(cursor)
                self.text_edit.find(text)

    def replace(self):
        if self.text_edit.textCursor().hasSelection():
            self.text_edit.insertPlainText(self.replace_edit.text())

    def replace_all(self):
        text = self.text_edit.toPlainText()
        find_text = self.find_edit.text()
        replace_text = self.replace_edit.text()
        if find_text:
            new_text = text.replace(find_text, replace_text)
            self.text_edit.setPlainText(new_text)

class NotepadApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_files = {}
        self.tab_widget = None
        self.initUI()

    def initUI(self):
        self.setWindowTitle('pyNotes | ahmetcakir-dev')
        self.setGeometry(100, 100, 800, 600)

        icon_path = os.path.join(os.path.dirname(__file__), 'images', 'note.png')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setTabBarAutoHide(False)
        self.tab_widget.setDocumentMode(True)
        self.tab_widget.setTabPosition(QTabWidget.TabPosition.North)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.tab_widget.setStyleSheet("""
            QTabBar::close-button {
                image: url(images/close_tab.png);
            }
        """)
        layout.addWidget(self.tab_widget)

        self.new_tab()

        self.create_toolbar()

        self.create_menu_bar()

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.cursor_label = QLabel("Line: 1, Column: 1")
        self.status_bar.addWidget(self.cursor_label)
        self.word_label = QLabel("Words: 0, Characters: 0")
        self.status_bar.addPermanentWidget(self.word_label)

        self.update_connections()

    def new_tab(self, file_path=None):
        editor = CodeEditor()
        editor.setFont(QFont('Arial', 12))

        tab_index = self.tab_widget.addTab(editor, "Untitled")
        self.tab_widget.setCurrentIndex(tab_index)

        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    editor.setPlainText(file.read())
                self.current_files[tab_index] = file_path
                self.tab_widget.setTabText(tab_index, os.path.basename(file_path))
            except Exception as e:
                QMessageBox.warning(self, 'Error', f'File could not be opened: {str(e)}')
        else:
            self.current_files[tab_index] = None

        self.update_connections()

    def close_tab(self, index):
        if self.maybe_save():
            editor = self.tab_widget.widget(index)
            self.tab_widget.removeTab(index)
            if index in self.current_files:
                del self.current_files[index]
            self.update_connections()

    def current_editor(self):
        current_index = self.tab_widget.currentIndex()
        if current_index >= 0:
            return self.tab_widget.widget(current_index)
        return None

    def update_connections(self):
        editor = self.current_editor()
        if editor:
            editor.cursorPositionChanged.connect(self.update_cursor_position)
            editor.textChanged.connect(self.update_word_count)

    def print_document(self):
        editor = self.current_editor()
        if editor:
            printer = QPrinter()
            dialog = QPrintDialog(printer, self)
            if dialog.exec() == QPrintDialog.DialogCode.Accepted:
                editor.print(printer)

    def create_toolbar(self):
        toolbar = self.addToolBar('Main Toolbar')

        new_action = QAction(QIcon.fromTheme('document-new'), 'New', self)
        new_action.triggered.connect(self.new_tab)
        toolbar.addAction(new_action)

        open_action = QAction(QIcon.fromTheme('document-open'), 'Open', self)
        open_action.triggered.connect(self.open_file)
        toolbar.addAction(open_action)

        save_action = QAction(QIcon.fromTheme('document-save'), 'Save', self)
        save_action.triggered.connect(self.save_file)
        toolbar.addAction(save_action)

        print_action = QAction(QIcon.fromTheme('document-print'), 'Print', self)
        print_action.triggered.connect(self.print_document)
        toolbar.addAction(print_action)

        toolbar.addSeparator()

        undo_action = QAction(QIcon.fromTheme('edit-undo'), 'Undo', self)
        undo_action.triggered.connect(self.undo)
        toolbar.addAction(undo_action)

        redo_action = QAction(QIcon.fromTheme('edit-redo'), 'Redo', self)
        redo_action.triggered.connect(self.redo)
        toolbar.addAction(redo_action)

        toolbar.addSeparator()

        cut_action = QAction(QIcon.fromTheme('edit-cut'), 'Cut', self)
        cut_action.triggered.connect(self.cut)
        toolbar.addAction(cut_action)

        copy_action = QAction(QIcon.fromTheme('edit-copy'), 'Copy', self)
        copy_action.triggered.connect(self.copy)
        toolbar.addAction(copy_action)

        paste_action = QAction(QIcon.fromTheme('edit-paste'), 'Paste', self)
        paste_action.triggered.connect(self.paste)
        toolbar.addAction(paste_action)

    def create_menu_bar(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu('&File')

        new_action = QAction('&New', self)
        new_action.setShortcut('Ctrl+N')
        new_action.triggered.connect(self.new_tab)
        file_menu.addAction(new_action)

        open_action = QAction('&Open', self)
        open_action.setShortcut('Ctrl+O')
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)

        save_action = QAction('&Save', self)
        save_action.setShortcut('Ctrl+S')
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)

        save_as_action = QAction('Save &As', self)
        save_as_action.setShortcut('Ctrl+Shift+S')
        save_as_action.triggered.connect(self.save_file_as)
        file_menu.addAction(save_as_action)

        print_action = QAction('&Print', self)
        print_action.setShortcut('Ctrl+P')
        print_action.triggered.connect(self.print_document)
        file_menu.addAction(print_action)

        file_menu.addSeparator()

        exit_action = QAction('&Exit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        edit_menu = menubar.addMenu('&Edit')

        undo_action = QAction('&Undo', self)
        undo_action.setShortcut('Ctrl+Z')
        undo_action.triggered.connect(self.undo)
        edit_menu.addAction(undo_action)

        redo_action = QAction('&Redo', self)
        redo_action.setShortcut('Ctrl+Y')
        redo_action.triggered.connect(self.redo)
        edit_menu.addAction(redo_action)

        edit_menu.addSeparator()

        cut_action = QAction('Cu&t', self)
        cut_action.setShortcut('Ctrl+X')
        cut_action.triggered.connect(self.cut)
        edit_menu.addAction(cut_action)

        copy_action = QAction('&Copy', self)
        copy_action.setShortcut('Ctrl+C')
        copy_action.triggered.connect(self.copy)
        edit_menu.addAction(copy_action)

        paste_action = QAction('&Paste', self)
        paste_action.setShortcut('Ctrl+V')
        paste_action.triggered.connect(self.paste)
        edit_menu.addAction(paste_action)

        edit_menu.addSeparator()

        select_all_action = QAction('Select &All', self)
        select_all_action.setShortcut('Ctrl+A')
        select_all_action.triggered.connect(self.select_all)
        edit_menu.addAction(select_all_action)

        edit_menu.addSeparator()

        find_action = QAction('&Find', self)
        find_action.setShortcut('Ctrl+F')
        find_action.triggered.connect(self.show_find_dialog)
        edit_menu.addAction(find_action)

        view_menu = menubar.addMenu('&View')

        font_action = QAction('&Font', self)
        font_action.triggered.connect(self.change_font)
        view_menu.addAction(font_action)

        help_menu = menubar.addMenu('&Help')

        about_action = QAction('&About', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def undo(self):
        editor = self.current_editor()
        if editor:
            editor.undo()

    def redo(self):
        editor = self.current_editor()
        if editor:
            editor.redo()

    def cut(self):
        editor = self.current_editor()
        if editor:
            editor.cut()

    def copy(self):
        editor = self.current_editor()
        if editor:
            editor.copy()

    def paste(self):
        editor = self.current_editor()
        if editor:
            editor.paste()

    def select_all(self):
        editor = self.current_editor()
        if editor:
            editor.selectAll()

    def open_file(self):
        if self.maybe_save():
            file_path, _ = QFileDialog.getOpenFileName(self, 'Open File', '', 'Text Files (*.txt);;All Files (*)')
            if file_path:
                try:
                    editor = self.current_editor()
                    if editor:
                        with open(file_path, 'r', encoding='utf-8') as file:
                            editor.setPlainText(file.read())
                        self.current_files[self.tab_widget.currentIndex()] = file_path
                        self.tab_widget.setTabText(self.tab_widget.currentIndex(), os.path.basename(file_path))
                        self.setWindowTitle(f'pyNotes | ahmetcakir-dev - {file_path}')
                except Exception as e:
                    QMessageBox.warning(self, 'Error', f'File could not be opened: {str(e)}')

    def save_file(self):
        current_index = self.tab_widget.currentIndex()
        if self.current_files.get(current_index):
            self._save_to_file(self.current_files[current_index])
        else:
            self.save_file_as()

    def save_file_as(self):
        file_path, _ = QFileDialog.getSaveFileName(self, 'Save As', '', 'Text Files (*.txt);;All Files (*)')
        if file_path:
            self._save_to_file(file_path)
            self.current_files[self.tab_widget.currentIndex()] = file_path
            self.tab_widget.setTabText(self.tab_widget.currentIndex(), os.path.basename(file_path))
            self.setWindowTitle(f'pyNotes | ahmetcakir-dev - {file_path}')

    def _save_to_file(self, file_path):
        try:
            editor = self.current_editor()
            if editor:
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.write(editor.toPlainText())
        except Exception as e:
            QMessageBox.warning(self, 'Error', f'File could not be saved: {str(e)}')

    def maybe_save(self):
        editor = self.current_editor()
        if editor and editor.document().isModified():
            reply = QMessageBox.question(self, 'Save', 'Do you want to save changes?',
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel)
            if reply == QMessageBox.StandardButton.Yes:
                self.save_file()
                return True
            elif reply == QMessageBox.StandardButton.Cancel:
                return False
            else:
                return True
        return True

    def show_find_dialog(self):
        if not hasattr(self, 'find_dialog'):
            self.find_dialog = FindReplaceDialog(self)
        self.find_dialog.show()
        self.find_dialog.raise_()
        self.find_dialog.activateWindow()

    def change_font(self):
        editor = self.current_editor()
        if editor:
            font, ok = QFontDialog.getFont(editor.font(), self)
            if ok:
                editor.setFont(font)

    def update_cursor_position(self):
        editor = self.current_editor()
        if editor:
            cursor = editor.textCursor()
            line = cursor.blockNumber() + 1
            column = cursor.positionInBlock() + 1
            self.cursor_label.setText(f"Line: {line}, Column: {column}")

    def update_word_count(self):
        editor = self.current_editor()
        if editor:
            text = editor.toPlainText()
            words = len(text.split()) if text else 0
            chars = len(text)
            self.word_label.setText(f"Words: {words}, Characters: {chars}")

    def show_about(self):
        QMessageBox.about(self, 'About pyNotes', 'pyNotes\n\nA simple notepad application built with PyQt6.\n\nDeveloped by ahmetcakir-dev\n\nVersion 1.0')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    notepad = NotepadApp()
    notepad.showMaximized()
    sys.exit(app.exec())

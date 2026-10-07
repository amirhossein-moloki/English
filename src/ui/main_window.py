import sys
from typing import List
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QPushButton, QTableWidget, QTableWidgetItem, QLabel,
    QHeaderView, QCheckBox, QDialog, QFormLayout, QLineEdit, QComboBox,
    QMessageBox, QProgressBar
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from src.core.config import get_config, setup_logging, Config
from src.database.repository import Database
from src.core.pipeline import ProcessingPipeline
from src.core.models import WordItem, ItemStatus


class WorkerThread(QThread):
    progress_signal = pyqtSignal(object, int, int)
    finished_signal = pyqtSignal(list)

    def __init__(self, pipeline: ProcessingPipeline, items: List[WordItem]):
        super().__init__()
        self.pipeline = pipeline
        self.items = items

    def run(self):
        def _cb(item, idx, total):
            self.progress_signal.emit(item, idx, total)

        processed = self.pipeline.process_items(self.items, progress_callback=_cb)
        self.finished_signal.emit(processed)


class SettingsDialog(QDialog):
    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Application Settings")
        self.setMinimumWidth(450)

        layout = QFormLayout()

        self.anki_url_input = QLineEdit(config.anki_connect_url)
        self.deck_input = QLineEdit(config.anki_default_deck)
        self.model_input = QLineEdit(config.anki_note_type)
        self.policy_combo = QComboBox()
        self.policy_combo.addItems(["SKIP", "UPDATE", "CREATE"])
        self.policy_combo.setCurrentText(config.duplicate_policy)

        self.oxford_id_input = QLineEdit(config.oxford_app_id or "")
        self.oxford_id_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.oxford_key_input = QLineEdit(config.oxford_app_key or "")
        self.oxford_key_input.setEchoMode(QLineEdit.EchoMode.Password)

        self.mw_key_input = QLineEdit(config.merriam_webster_api_key or "")
        self.mw_key_input.setEchoMode(QLineEdit.EchoMode.Password)

        layout.addRow("AnkiConnect URL:", self.anki_url_input)
        layout.addRow("Default Deck:", self.deck_input)
        layout.addRow("Default Note Type:", self.model_input)
        layout.addRow("Duplicate Policy:", self.policy_combo)
        layout.addRow("Oxford App ID:", self.oxford_id_input)
        layout.addRow("Oxford App Key:", self.oxford_key_input)
        layout.addRow("Merriam-Webster Key:", self.mw_key_input)

        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(self.accept)
        layout.addRow(save_btn)

        self.setLayout(layout)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ChatGPT to Anki Importer")
        self.resize(1000, 700)

        self.config = get_config()
        self.logger = setup_logging(self.config)
        self.db = Database(self.config.db_path)
        self.pipeline = ProcessingPipeline(self.config, self.db)

        self.analyzed_items: List[WordItem] = []

        self._init_ui()

    def _init_ui(self):
        main_widget = QWidget()
        layout = QVBoxLayout()

        # Header / Status bar banner
        top_bar = QHBoxLayout()
        self.anki_status_label = QLabel("Anki Status: Checking...")
        self.check_anki_btn = QPushButton("Check Anki")
        self.check_anki_btn.clicked.connect(self.check_anki)
        self.settings_btn = QPushButton("Settings")
        self.settings_btn.clicked.connect(self.open_settings)

        top_bar.addWidget(self.anki_status_label)
        top_bar.addStretch()
        top_bar.addWidget(self.check_anki_btn)
        top_bar.addWidget(self.settings_btn)
        layout.addLayout(top_bar)

        # Input Area
        input_label = QLabel("Paste ChatGPT Output below:")
        layout.addWidget(input_label)

        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("Paste vocabulary output from ChatGPT here...")
        self.text_input.setMaximumHeight(180)
        layout.addWidget(self.text_input)

        # Action Buttons
        btn_layout = QHBoxLayout()
        self.analyze_btn = QPushButton("Analyze Text")
        self.analyze_btn.clicked.connect(self.analyze_text)
        self.import_btn = QPushButton("Add to Anki")
        self.import_btn.setEnabled(False)
        self.import_btn.clicked.connect(self.start_import)

        btn_layout.addWidget(self.analyze_btn)
        btn_layout.addWidget(self.import_btn)
        layout.addLayout(btn_layout)

        # Stats Counters
        self.stats_label = QLabel("Detected: 0 | New: 0 | Duplicate: 0 | Success: 0")
        layout.addWidget(self.stats_label)

        # Table View
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Select", "Word", "Meaning", "Example", "Part of Speech", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        main_widget.setLayout(layout)
        self.setCentralWidget(main_widget)

        self.check_anki()

    def check_anki(self):
        connected = self.pipeline.anki_client.is_connected()
        if connected:
            self.anki_status_label.setText("Anki Status: Connected ✓")
            self.anki_status_label.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.anki_status_label.setText("Anki Status: Unreachable ✗")
            self.anki_status_label.setStyleSheet("color: red; font-weight: bold;")

    def open_settings(self):
        dialog = SettingsDialog(self.config, self)
        if dialog.exec():
            self.config.anki_connect_url = dialog.anki_url_input.text()
            self.config.anki_default_deck = dialog.deck_input.text()
            self.config.anki_note_type = dialog.model_input.text()
            self.config.duplicate_policy = dialog.policy_combo.currentText()
            self.config.oxford_app_id = dialog.oxford_id_input.text() or None
            self.config.oxford_app_key = dialog.oxford_key_input.text() or None
            self.config.merriam_webster_api_key = dialog.mw_key_input.text() or None

            # Re-initialize pipeline with updated config
            self.pipeline = ProcessingPipeline(self.config, self.db)
            self.check_anki()

    def analyze_text(self):
        text = self.text_input.toPlainText()
        if not text.strip():
            QMessageBox.warning(self, "Warning", "Please paste ChatGPT text to analyze.")
            return

        self.analyzed_items = self.pipeline.analyze_text(text)
        self.render_table()
        self.import_btn.setEnabled(len(self.analyzed_items) > 0)

    def render_table(self):
        self.table.setRowCount(len(self.analyzed_items))
        new_cnt = sum(1 for i in self.analyzed_items if i.status != ItemStatus.DUPLICATE)
        dup_cnt = len(self.analyzed_items) - new_cnt
        succ_cnt = sum(1 for i in self.analyzed_items if i.status == ItemStatus.SUCCESS)

        self.stats_label.setText(
            f"Detected: {len(self.analyzed_items)} | New: {new_cnt} | Duplicate: {dup_cnt} | Success: {succ_cnt}"
        )

        for row, item in enumerate(self.analyzed_items):
            chk = QCheckBox()
            chk.setChecked(item.status != ItemStatus.DUPLICATE)
            self.table.setCellWidget(row, 0, chk)

            self.table.setItem(row, 1, QTableWidgetItem(item.word))
            self.table.setItem(row, 2, QTableWidgetItem(item.meaning or ""))
            self.table.setItem(row, 3, QTableWidgetItem(item.example or ""))
            self.table.setItem(row, 4, QTableWidgetItem(item.part_of_speech or ""))

            status_item = QTableWidgetItem(item.status.value)
            self.table.setItem(row, 5, status_item)

    def start_import(self):
        selected_items = []
        for row in range(self.table.rowCount()):
            chk = self.table.cellWidget(row, 0)
            if isinstance(chk, QCheckBox) and chk.isChecked():
                selected_items.append(self.analyzed_items[row])

        if not selected_items:
            QMessageBox.warning(self, "Warning", "No items selected to import.")
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(selected_items))
        self.progress_bar.setValue(0)
        self.analyze_btn.setEnabled(False)
        self.import_btn.setEnabled(False)

        self.worker = WorkerThread(self.pipeline, selected_items)
        self.worker.progress_signal.connect(self.on_item_progress)
        self.worker.finished_signal.connect(self.on_import_finished)
        self.worker.start()

    def on_item_progress(self, item: WordItem, idx: int, total: int):
        self.progress_bar.setValue(idx)
        self.render_table()

    def on_import_finished(self, processed_items: List[WordItem]):
        self.progress_bar.setVisible(False)
        self.analyze_btn.setEnabled(True)
        self.import_btn.setEnabled(True)
        self.render_table()
        QMessageBox.information(self, "Success", f"Batch import completed for {len(processed_items)} items!")


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

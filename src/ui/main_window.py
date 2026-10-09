import sys
import json
from pathlib import Path
from typing import List, Dict
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QPushButton, QTableWidget, QTableWidgetItem, QLabel,
    QHeaderView, QCheckBox, QDialog, QFormLayout, QLineEdit, QComboBox,
    QMessageBox, QProgressBar, QFileDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from src.core.config import get_config, setup_logging, Config
from src.database.repository import Database
from src.core.pipeline import ProcessingPipeline, PipelineStats
from src.core.models import WordItem, ItemStatus, validate_canonical_json, CanonicalBatchSchema


class WorkerThread(QThread):
    progress_signal = pyqtSignal(object, int, int, object)
    finished_signal = pyqtSignal(list)

    def __init__(self, pipeline: ProcessingPipeline, items: List[WordItem]):
        super().__init__()
        self.pipeline = pipeline
        self.items = items

    def run(self):
        def _cb(item, idx, total, stats):
            self.progress_signal.emit(item, idx, total, stats)

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
        self.setWindowTitle("English Vocabulary Learning & Anki Integration")
        self.resize(1100, 750)

        self.config = get_config()
        self.logger = setup_logging(self.config)
        self.db = Database(self.config.db_path)
        self.pipeline = ProcessingPipeline(self.config, self.db)

        self.analyzed_items: List[WordItem] = []

        self._init_ui()

    def _init_ui(self):
        main_widget = QWidget()
        layout = QVBoxLayout()

        # Top Bar
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

        # Input Area Controls
        input_bar = QHBoxLayout()
        input_label = QLabel("Paste JSON / ChatGPT Text or Load Files:")
        self.load_files_btn = QPushButton("Load File(s)...")
        self.load_files_btn.clicked.connect(self.load_files)
        self.validate_json_btn = QPushButton("Validate JSON")
        self.validate_json_btn.clicked.connect(self.validate_pasted_json)

        input_bar.addWidget(input_label)
        input_bar.addStretch()
        input_bar.addWidget(self.validate_json_btn)
        input_bar.addWidget(self.load_files_btn)
        layout.addLayout(input_bar)

        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("Paste JSON object or vocabulary text from ChatGPT here...")
        self.text_input.setMaximumHeight(160)
        layout.addWidget(self.text_input)

        # Action Buttons
        btn_layout = QHBoxLayout()
        self.analyze_btn = QPushButton("Analyze Input")
        self.analyze_btn.clicked.connect(self.analyze_text)
        self.import_btn = QPushButton("Import Selected to Anki")
        self.import_btn.setEnabled(False)
        self.import_btn.clicked.connect(self.start_import)
        self.retry_btn = QPushButton("Retry Failed")
        self.retry_btn.setEnabled(False)
        self.retry_btn.clicked.connect(self.retry_failed)
        self.export_btn = QPushButton("Export JSON")
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self.export_json)

        btn_layout.addWidget(self.analyze_btn)
        btn_layout.addWidget(self.import_btn)
        btn_layout.addWidget(self.retry_btn)
        btn_layout.addWidget(self.export_btn)
        layout.addLayout(btn_layout)

        # Stats Counters
        self.stats_label = QLabel("Detected: 0 | Selected: 0 | Success: 0 | Duplicates: 0 | Failed: 0")
        layout.addWidget(self.stats_label)

        # Table View
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "Select", "Word", "IPA", "POS", "Meaning EN", "Meaning FA", "Example EN", "Example FA", "Source", "Status"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
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

            self.pipeline = ProcessingPipeline(self.config, self.db)
            self.check_anki()

    def validate_pasted_json(self):
        text = self.text_input.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Warning", "Text input is empty.")
            return

        report = validate_canonical_json(text)
        if report.is_valid:
            QMessageBox.information(
                self, "JSON Validation",
                f"Valid Canonical JSON!\nTotal Entries: {report.total_entries}\nValid Entries: {len(report.valid_entries)}"
            )
        else:
            err_msg = "\n".join([f"- Index {e.entry_index} [{e.field}]: {e.message}" for e in report.errors])
            QMessageBox.warning(
                self, "JSON Validation Failed",
                f"Validation Errors ({len(report.errors)}):\n{err_msg}\nValid Entries: {len(report.valid_entries)}"
            )

    def load_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Vocabulary File(s)", "", "All Supported (*.json *.txt *.md);;JSON Files (*.json);;Text Files (*.txt *.md)"
        )
        if not files:
            return

        sources: Dict[str, str] = {}
        for file_path in files:
            path = Path(file_path)
            sources[path.name] = path.read_text(encoding="utf-8")

        self.analyzed_items = self.pipeline.analyze_sources(sources)
        self.render_table()
        self.import_btn.setEnabled(len(self.analyzed_items) > 0)
        self.export_btn.setEnabled(len(self.analyzed_items) > 0)

    def analyze_text(self):
        text = self.text_input.toPlainText()
        if not text.strip():
            QMessageBox.warning(self, "Warning", "Please paste text or load files to analyze.")
            return

        self.analyzed_items = self.pipeline.analyze_text(text, source_name="Pasted Input")
        self.render_table()
        self.import_btn.setEnabled(len(self.analyzed_items) > 0)
        self.export_btn.setEnabled(len(self.analyzed_items) > 0)

    def sync_edits_from_table(self):
        for row, item in enumerate(self.analyzed_items):
            word_val = self.table.item(row, 1)
            ipa_val = self.table.item(row, 2)
            pos_val = self.table.item(row, 3)
            m_en_val = self.table.item(row, 4)
            m_fa_val = self.table.item(row, 5)
            ex_en_val = self.table.item(row, 6)
            ex_fa_val = self.table.item(row, 7)

            if word_val:
                item.word = word_val.text().strip()
            if ipa_val:
                item.ipa = ipa_val.text().strip()
                item.pronunciation = item.ipa
            if pos_val:
                item.part_of_speech = pos_val.text().strip()
            if m_en_val:
                item.meaning_en = m_en_val.text().strip()
                item.meaning = item.meaning_en
            if m_fa_val:
                item.meaning_fa = m_fa_val.text().strip()
            if ex_en_val:
                item.example_en = ex_en_val.text().strip()
                item.example = item.example_en
            if ex_fa_val:
                item.example_fa = ex_fa_val.text().strip()

    def render_table(self):
        self.table.setRowCount(len(self.analyzed_items))
        succ_cnt = sum(1 for i in self.analyzed_items if i.status == ItemStatus.SUCCESS)
        dup_cnt = sum(1 for i in self.analyzed_items if i.status == ItemStatus.DUPLICATE)
        failed_cnt = sum(1 for i in self.analyzed_items if i.status == ItemStatus.FAILED)

        selected_cnt = 0
        for row in range(self.table.rowCount()):
            chk = self.table.cellWidget(row, 0)
            if isinstance(chk, QCheckBox) and chk.isChecked():
                selected_cnt += 1

        self.stats_label.setText(
            f"Detected: {len(self.analyzed_items)} | Selected: {selected_cnt} | Success: {succ_cnt} | Duplicates: {dup_cnt} | Failed: {failed_cnt}"
        )

        for row, item in enumerate(self.analyzed_items):
            chk = QCheckBox()
            chk.setChecked(item.status != ItemStatus.DUPLICATE)
            chk.stateChanged.connect(self._on_check_changed)
            self.table.setCellWidget(row, 0, chk)

            self.table.setItem(row, 1, QTableWidgetItem(item.word or ""))
            self.table.setItem(row, 2, QTableWidgetItem(item.ipa or item.pronunciation or ""))
            self.table.setItem(row, 3, QTableWidgetItem(item.part_of_speech or ""))
            self.table.setItem(row, 4, QTableWidgetItem(item.meaning_en or item.meaning or ""))
            self.table.setItem(row, 5, QTableWidgetItem(item.meaning_fa or ""))
            self.table.setItem(row, 6, QTableWidgetItem(item.example_en or item.example or ""))
            self.table.setItem(row, 7, QTableWidgetItem(item.example_fa or ""))
            self.table.setItem(row, 8, QTableWidgetItem(item.source or ""))

            status_item = QTableWidgetItem(item.status.value)
            if item.status == ItemStatus.SUCCESS:
                status_item.setForeground(Qt.GlobalColor.darkGreen)
            elif item.status == ItemStatus.FAILED:
                status_item.setForeground(Qt.GlobalColor.red)
            elif item.status == ItemStatus.DUPLICATE:
                status_item.setForeground(Qt.GlobalColor.darkYellow)

            self.table.setItem(row, 9, status_item)

        self.retry_btn.setEnabled(failed_cnt > 0)

    def _on_check_changed(self):
        selected_cnt = 0
        for row in range(self.table.rowCount()):
            chk = self.table.cellWidget(row, 0)
            if isinstance(chk, QCheckBox) and chk.isChecked():
                selected_cnt += 1

        succ_cnt = sum(1 for i in self.analyzed_items if i.status == ItemStatus.SUCCESS)
        dup_cnt = sum(1 for i in self.analyzed_items if i.status == ItemStatus.DUPLICATE)
        failed_cnt = sum(1 for i in self.analyzed_items if i.status == ItemStatus.FAILED)

        self.stats_label.setText(
            f"Detected: {len(self.analyzed_items)} | Selected: {selected_cnt} | Success: {succ_cnt} | Duplicates: {dup_cnt} | Failed: {failed_cnt}"
        )

    def start_import(self):
        self.sync_edits_from_table()
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

    def retry_failed(self):
        failed_items = [item for item in self.analyzed_items if item.status == ItemStatus.FAILED]
        if not failed_items:
            return

        for item in failed_items:
            item.status = ItemStatus.PENDING

        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(failed_items))
        self.progress_bar.setValue(0)
        self.analyze_btn.setEnabled(False)
        self.import_btn.setEnabled(False)

        self.worker = WorkerThread(self.pipeline, failed_items)
        self.worker.progress_signal.connect(self.on_item_progress)
        self.worker.finished_signal.connect(self.on_import_finished)
        self.worker.start()

    def export_json(self):
        self.sync_edits_from_table()
        if not self.analyzed_items:
            QMessageBox.warning(self, "Warning", "No items to export.")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Export Canonical JSON", "vocabulary.json", "JSON Files (*.json)")
        if not file_path:
            return

        entries = [item.to_canonical_schema().model_dump(exclude_none=True) for item in self.analyzed_items]
        batch = {
            "schema_version": "1.0",
            "entries": entries
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(batch, f, ensure_ascii=False, indent=2)

        QMessageBox.information(self, "Export Successful", f"Exported {len(entries)} entries to {file_path}")

    def on_item_progress(self, item: WordItem, idx: int, total: int, stats: PipelineStats):
        self.progress_bar.setValue(idx)
        self.render_table()

    def on_import_finished(self, processed_items: List[WordItem]):
        self.progress_bar.setVisible(False)
        self.analyze_btn.setEnabled(True)
        self.import_btn.setEnabled(True)
        self.render_table()
        QMessageBox.information(self, "Batch Import Completed", f"Processed {len(processed_items)} items!")


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

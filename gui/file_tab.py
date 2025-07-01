from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QListWidget,
    QTextEdit,
    QFileDialog,
)
from workers.file_worker import FileTranslationWorker


class FileTranslationTab:
    def __init__(self, main_window):
        self.main_window = main_window
        self.widget = QWidget()
        self.layout = QVBoxLayout(self.widget)
        self.setup_ui()

    def setup_ui(self):
        self.select_button = QPushButton("Select Files")
        self.translate_button = QPushButton("Translate Files")
        self.file_list = QListWidget()
        self.output = QTextEdit()
        self.output.setReadOnly(True)

        self.layout.addWidget(self.select_button)
        self.layout.addWidget(self.translate_button)
        self.layout.addWidget(self.file_list)
        self.layout.addWidget(self.output)

    def setup_signals(self):
        self.select_button.clicked.connect(self.select_files)
        self.translate_button.clicked.connect(self.start_translation)

    def enable(self, status):
        self.translate_button.setEnabled(status)

    def select_files(self):
        files, _ = QFileDialog.getOpenFileNames(self.widget, "Select Files")
        if files:
            self.file_list.addItems(files)
            self.selected_files = files

    def start_translation(self):
        config = self.main_window.config
        self.worker = FileTranslationWorker(
            self.main_window.api_client,
            self.selected_files,
            config["project_id"],
            None,
            config["files_max_retries"],
            config["files_retry_delay"],
        )
        self.worker.progress_updated.connect(self.update_status)
        self.worker.file_completed.connect(self.file_status)
        self.worker.all_completed.connect(self.finished)
        self.worker.error_occurred.connect(self.error)
        self.worker.start()

    def update_status(self, msg):
        self.main_window.statusBar().showMessage(msg)

    def file_status(self, filename, status):
        self.output.append(f"{filename}: {status}")

    def finished(self, summary):
        self.output.append(f"\n{summary}")
        self.update_status("✅ All files processed")

    def error(self, msg):
        self.output.append(f"❌ {msg}")
        self.update_status("❌ Error")

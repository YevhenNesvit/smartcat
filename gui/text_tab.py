from PyQt5.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QTextEdit, QPushButton
from workers.text_worker import TranslationWorker


class TextTranslationTab:
    def __init__(self, main_window):
        self.main_window = main_window
        self.widget = QWidget()
        self.layout = QVBoxLayout(self.widget)
        self.setup_ui()

    def setup_ui(self):
        self.text_input = QTextEdit()
        self.translate_button = QPushButton("Translate Text")
        self.result_output = QTextEdit()
        self.result_output.setReadOnly(True)

        group = QGroupBox("Text Translation")
        group_layout = QVBoxLayout()
        group_layout.addWidget(self.text_input)
        group_layout.addWidget(self.translate_button)
        group_layout.addWidget(self.result_output)
        group.setLayout(group_layout)

        self.layout.addWidget(group)

    def setup_signals(self):
        self.translate_button.clicked.connect(self.start_translation)

    def enable(self, status):
        self.translate_button.setEnabled(status)

    def start_translation(self):
        text = self.text_input.toPlainText().strip()
        if not text:
            return

        config = self.main_window.config
        self.worker = TranslationWorker(
            self.main_window.api_client,
            text,
            config["project_id"],
            config["source_lang"],
            config["target_lang"],
            config["max_retries"],
            config["retry_delay"],
        )

        self.worker.progress_updated.connect(self.update_status)
        self.worker.translation_completed.connect(self.translation_done)
        self.worker.error_occurred.connect(self.translation_error)
        self.worker.start()

    def update_status(self, msg):
        self.main_window.statusBar().showMessage(msg)

    def translation_done(self, result):
        self.result_output.setPlainText(result)
        self.update_status("✅ Translation complete")

    def translation_error(self, error):
        self.result_output.setPlainText(f"❌ {error}")
        self.update_status("❌ Error")

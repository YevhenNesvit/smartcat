from PyQt5.QtWidgets import QVBoxLayout, QGroupBox, QTextEdit, QPushButton
from workers.text_worker import TranslationWorker
from gui.base_tab import BaseTranslationTab


class TextTranslationTab(BaseTranslationTab):
    """
    Вкладка для перекладу тексту.
    """

    def __init__(self, api_client, config, status_handler, parent=None):
        super().__init__(api_client, config, status_handler, parent)
        self.text_input = None
        self.translate_button = None
        self.result_output = None

        # Викликаємо setup_ui та setup_signals тут, після ініціалізації атрибутів
        self.setup_ui()
        self.setup_signals()

    def setup_ui(self):
        """Налаштовує елементи інтерфейсу користувача для вкладки перекладу тексту."""
        input_group = QGroupBox(
            f"Text for translation ({self.config['source_lang'].upper()} → {self.config['target_lang'].upper()})"
        )
        input_layout = QVBoxLayout()
        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("Enter text for translation...")
        self.text_input.setMaximumHeight(120)
        input_layout.addWidget(self.text_input)

        self.translate_button = QPushButton("🔄 Translate Text")
        self.translate_button.setEnabled(False)  # Спочатку вимкнено
        input_layout.addWidget(self.translate_button)
        input_group.setLayout(input_layout)
        self._main_layout.addWidget(input_group)

        result_group = QGroupBox("Translation result")
        result_layout = QVBoxLayout()
        self.result_output = QTextEdit()
        self.result_output.setReadOnly(True)
        result_layout.addWidget(self.result_output)
        result_group.setLayout(result_layout)
        self._main_layout.addWidget(result_group)

    def setup_signals(self):
        """Підключає сигнали та слоти для вкладки перекладу тексту."""
        self.translate_button.clicked.connect(self.start_translation)  # type: ignore

    def enable_translation_button(self, enable: bool):
        """Вмикає або вимикає кнопку перекладу тексту."""
        self.translate_button.setEnabled(enable)  # type: ignore

    def start_translation(self):
        """Запускає процес перекладу тексту."""
        source_text = self.text_input.toPlainText().strip()  # type: ignore
        if not source_text:
            self.status_handler.show_warning("Error", "Please enter text for translation")
            return
        if not self.api_client:
            self.status_handler.show_warning("Error", "First connect to API")
            return

        self.enable_translation_button(False)
        self.status_handler.show_progress()
        self.result_output.clear()  # type: ignore

        self.worker = TranslationWorker(
            self.api_client,
            source_text,
            self.config["project_id"],
            self.config["source_lang"],
            self.config["target_lang"],
            self.config["max_retries"],
            self.config["retry_delay"],
        )
        self.worker.progress_updated.connect(self._handle_worker_progress)
        self.worker.translation_completed.connect(self._text_translation_finished)
        self.worker.error_occurred.connect(self._handle_worker_error)
        self.worker.start()

    def _text_translation_finished(self, result: str):
        """Обробник завершення перекладу тексту."""
        self.result_output.setPlainText(result)  # type: ignore
        self.status_handler.update_status("✅ Text translation completed successfully!")
        self.status_handler.hide_progress()
        self.enable_translation_button(True)
        self.translation_completed.emit(result)  # type: ignore # Передаємо результат далі

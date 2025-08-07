import os
from PyQt5.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QListWidget,
    QTextEdit,
    QFileDialog,
    QGroupBox,
    QFormLayout,
    QLineEdit,
)
from workers.file_worker import FileTranslationWorker
from gui.base_tab import BaseTranslationTab


class FileTranslationTab(BaseTranslationTab):
    """
    Tab for file translation.
    """

    def __init__(self, api_client, config, status_handler, parent=None):
        super().__init__(api_client, config, status_handler, parent)
        self.selected_files = []
        self.files_list = None
        self.output_folder_input = None
        self.translate_button = None
        self.file_results_output = None

        self.setup_ui()
        self.setup_signals()

    def setup_ui(self):
        """Configures the user interface elements for the file translation tab."""
        file_selection_group = QGroupBox("File Selection")
        file_selection_layout = QVBoxLayout()
        file_buttons_layout = QHBoxLayout()

        browse_files_btn = QPushButton("📂 Browse Files")
        browse_files_btn.clicked.connect(self.browse_files)
        file_buttons_layout.addWidget(browse_files_btn)

        clear_files_btn = QPushButton("🗑️ Clear Files")
        clear_files_btn.clicked.connect(self.clear_files)
        file_buttons_layout.addWidget(clear_files_btn)
        file_selection_layout.addLayout(file_buttons_layout)

        self.files_list = QListWidget()
        self.files_list.setMaximumHeight(100)
        file_selection_layout.addWidget(self.files_list)
        file_selection_group.setLayout(file_selection_layout)
        self._main_layout.addWidget(file_selection_group)

        output_group = QGroupBox("Output Settings")
        output_layout = QFormLayout()
        folder_layout = QHBoxLayout()
        self.output_folder_input = QLineEdit()
        folder_layout.addWidget(self.output_folder_input)
        browse_folder_btn = QPushButton("📁 Browse Folder")
        browse_folder_btn.clicked.connect(self.browse_output_folder)
        folder_layout.addWidget(browse_folder_btn)
        output_layout.addRow("Translated Files Folder:", folder_layout)
        output_group.setLayout(output_layout)
        self._main_layout.addWidget(output_group)

        self.translate_button = QPushButton("🔄 Translate Files")
        self.translate_button.setEnabled(False)  # Спочатку вимкнено
        self._main_layout.addWidget(self.translate_button)

        file_results_group = QGroupBox("Translation Results")
        file_results_layout = QVBoxLayout()
        self.file_results_output = QTextEdit()
        self.file_results_output.setReadOnly(True)
        file_results_layout.addWidget(self.file_results_output)
        file_results_group.setLayout(file_results_layout)
        self._main_layout.addWidget(file_results_group)

    def setup_signals(self):
        """Connects signals and slots for the file translation tab."""
        self.translate_button.clicked.connect(self.start_translation)  # type: ignore
        self.status_handler.file_translation_button_enabled.connect(self.translate_button.setEnabled)  # type: ignore

    def enable_translation_button(self, enable: bool):
        """Enables or disables the file translation button."""
        self.translate_button.setEnabled(enable)  # type: ignore

    def browse_files(self):
        """Opens the file selection dialog and updates the list."""
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select files", "", "All Files (*.*)"
        )
        if files:
            self.selected_files.extend(files)
            self._update_files_list()
            self.status_handler.enable_file_translation_button(
                len(self.selected_files) > 0 and self.api_client is not None
            )

    def browse_output_folder(self):
        """Opens the folder selection dialog to save the translated files."""
        folder = QFileDialog.getExistingDirectory(self, "Select output folder")
        if folder:
            self.output_folder_input.setText(folder)  # type: ignore

    def clear_files(self):
        """Clears the list of selected files."""
        self.selected_files.clear()
        self._update_files_list()
        self.status_handler.enable_file_translation_button(False)

    def _update_files_list(self):
        """Updates the display of the file list in the QListWidget widget."""
        self.files_list.clear()  # type: ignore
        for file_path in self.selected_files:
            self.files_list.addItem(os.path.basename(file_path))  # type: ignore

    def start_translation(self):
        """Starts the file translation process."""
        if not self.selected_files:
            self.status_handler.show_warning("Error", "Please select files")
            return
        if not self.api_client:
            self.status_handler.show_warning("Error", "First connect to API")
            return

        output_folder = self.output_folder_input.text().strip() or None  # type: ignore
        if output_folder and not os.path.exists(output_folder):
            try:
                os.makedirs(output_folder)
            except Exception as e:
                self.status_handler.show_warning(
                    "Error", f"Cannot create output folder: {str(e)}"
                )
                return

        self.enable_translation_button(False)
        self.status_handler.show_progress()
        self.file_results_output.clear()  # type: ignore

        self.worker = FileTranslationWorker(
            self.api_client,
            self.selected_files.copy(),
            self.config["project_id"],
            output_folder,
            self.config["files_max_retries"],
            self.config["files_retry_delay"],
        )
        self.worker.progress_updated.connect(self._handle_worker_progress)
        self.worker.file_completed.connect(self._file_translation_update)
        self.worker.all_completed.connect(self._file_translation_finished)
        self.worker.error_occurred.connect(self._handle_worker_error)
        self.worker.start()

    def _file_translation_update(self, filename: str, status: str):
        """Updates the translation status of an individual file."""
        current_text = self.file_results_output.toPlainText()  # type: ignore
        new_text = (
            f"{current_text}\n{filename}: {status}"
            if current_text
            else f"{filename}: {status}"
        )
        self.file_results_output.setPlainText(new_text)  # type: ignore
        cursor = self.file_results_output.textCursor()  # type: ignore
        cursor.movePosition(cursor.End)
        self.file_results_output.setTextCursor(cursor)  # type: ignore
        self.file_status_updated.emit(filename, status)  # type: ignore

    def _file_translation_finished(self, summary: str):
        """Handler for the completion of translation of all files."""
        self.file_results_output.append(f"\n{summary}")  # type: ignore
        self.status_handler.update_status("✅ Files translation completed!")
        self.status_handler.hide_progress()
        self.enable_translation_button(True)
        self.status_handler.show_info(
            "Translation Complete",
            "File translation has been completed! Check the results below.",
        )
        self.all_files_completed.emit(summary)  # type: ignore

import os
from PyQt5.QtWidgets import (
    QMainWindow,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QTextEdit,
    QPushButton,
    QLabel,
    QProgressBar,
    QMessageBox,
    QGroupBox,
    QFormLayout,
    QFileDialog,
    QLineEdit,
    QListWidget,
    QTabWidget,
)
from config import load_env_config
from workers.text_worker import TranslationWorker
from workers.file_worker import FileTranslationWorker
from api import SmartCAT


class SmartCATGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.api_client = None
        self.worker = None
        self.file_worker = None
        self.selected_files = []

        self.config = load_env_config()
        self.init_ui()
        self.auto_connect()

    def init_ui(self):
        self.setWindowTitle(self.config["app_title"])
        self.setGeometry(100, 100, 800, 700)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        config_group = QGroupBox("Configuration (from .env file)")
        config_layout = QFormLayout()
        self.config_info = QLabel()
        self.update_config_display()
        config_layout.addRow(self.config_info)

        self.connect_btn = QPushButton("Connect to SmartCAT")
        self.connect_btn.clicked.connect(self.connect_to_api)
        config_layout.addRow(self.connect_btn)

        self.connection_status = QLabel("Status: Not connected")
        config_layout.addRow(self.connection_status)
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        self.create_text_translation_tab()
        self.create_file_translation_tab()

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Ready to work")
        self.status_label.setStyleSheet("QLabel { color: #666; font-style: italic; }")
        layout.addWidget(self.status_label)

        button_layout = QHBoxLayout()
        self.clear_btn = QPushButton("🗑️ Clear All")
        self.clear_btn.clicked.connect(self.clear_all)
        button_layout.addWidget(self.clear_btn)

        self.refresh_btn = QPushButton("🔄 Refresh Configuration")
        self.refresh_btn.clicked.connect(self.refresh_config)
        button_layout.addWidget(self.refresh_btn)
        layout.addLayout(button_layout)

    def create_text_translation_tab(self):
        text_tab = QWidget()
        self.tabs.addTab(text_tab, "📝 Text Translation")
        layout = QVBoxLayout(text_tab)

        input_group = QGroupBox(
            f"Text for translation ({self.config['source_lang'].upper()} → {self.config['target_lang'].upper()})"
        )
        input_layout = QVBoxLayout()
        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("Enter text for translation...")
        self.text_input.setMaximumHeight(120)
        input_layout.addWidget(self.text_input)

        self.translate_text_btn = QPushButton("🔄 Translate Text")
        self.translate_text_btn.clicked.connect(self.start_text_translation)
        self.translate_text_btn.setEnabled(False)
        input_layout.addWidget(self.translate_text_btn)
        input_group.setLayout(input_layout)
        layout.addWidget(input_group)

        result_group = QGroupBox("Translation result")
        result_layout = QVBoxLayout()
        self.text_result_output = QTextEdit()
        self.text_result_output.setReadOnly(True)
        result_layout.addWidget(self.text_result_output)
        result_group.setLayout(result_layout)
        layout.addWidget(result_group)

    def create_file_translation_tab(self):
        file_tab = QWidget()
        self.tabs.addTab(file_tab, "📁 File Translation")
        layout = QVBoxLayout(file_tab)

        file_selection_group = QGroupBox("File Selection")
        file_selection_layout = QVBoxLayout()
        file_buttons_layout = QHBoxLayout()

        self.browse_files_btn = QPushButton("📂 Browse Files")
        self.browse_files_btn.clicked.connect(self.browse_files)
        file_buttons_layout.addWidget(self.browse_files_btn)

        self.clear_files_btn = QPushButton("🗑️ Clear Files")
        self.clear_files_btn.clicked.connect(self.clear_files)
        file_buttons_layout.addWidget(self.clear_files_btn)
        file_selection_layout.addLayout(file_buttons_layout)

        self.files_list = QListWidget()
        self.files_list.setMaximumHeight(100)
        file_selection_layout.addWidget(self.files_list)
        file_selection_group.setLayout(file_selection_layout)
        layout.addWidget(file_selection_group)

        output_group = QGroupBox("Output Settings")
        output_layout = QFormLayout()
        folder_layout = QHBoxLayout()
        self.output_folder_input = QLineEdit()
        folder_layout.addWidget(self.output_folder_input)
        self.browse_folder_btn = QPushButton("📁 Browse Folder")
        self.browse_folder_btn.clicked.connect(self.browse_output_folder)
        folder_layout.addWidget(self.browse_folder_btn)
        output_layout.addRow("Translated Files Folder:", folder_layout)
        output_group.setLayout(output_layout)
        layout.addWidget(output_group)

        self.translate_files_btn = QPushButton("🔄 Translate Files")
        self.translate_files_btn.clicked.connect(self.start_file_translation)
        self.translate_files_btn.setEnabled(False)
        layout.addWidget(self.translate_files_btn)

        file_results_group = QGroupBox("Translation Results")
        file_results_layout = QVBoxLayout()
        self.file_results_output = QTextEdit()
        self.file_results_output.setReadOnly(True)
        file_results_layout.addWidget(self.file_results_output)
        file_results_group.setLayout(file_results_layout)
        layout.addWidget(file_results_group)

    def update_config_display(self):
        self.config_info.setText(
            f"""
📡 Server: {self.config['server_url']}
👤 User: {self.config['username'][:3]}***
🆔 Project ID: {self.config['project_id']}
🔤 Language pair: {self.config['source_lang'].upper()} → {self.config['target_lang'].upper()}
            """.strip()
        )

    def refresh_config(self):
        from dotenv import load_dotenv

        load_dotenv(override=True)
        self.config = load_env_config()
        self.update_config_display()
        self.connection_status.setText(
            "Status: Configuration updated. Reconnection required."
        )
        self.connection_status.setStyleSheet("color: orange")
        self.translate_text_btn.setEnabled(False)
        self.translate_files_btn.setEnabled(False)
        QMessageBox.information(
            self, "Configuration", "Configuration reloaded from .env file!"
        )

    def auto_connect(self):
        if (
            self.config["username"]
            and self.config["password"]
            and self.config["project_id"]
        ):
            self.connect_to_api()

    def connect_to_api(self):
        try:
            self.connection_status.setText("Status: Connecting...")
            self.connection_status.setStyleSheet("color: orange")
            self.api_client = SmartCAT(
                self.config["username"],
                self.config["password"],
                self.config["server_url"],
            )
            test_response = self.api_client.project.get(self.config["project_id"])
            if test_response.status_code == 200:
                project_name = test_response.json().get("name", "Unknown")
                self.connection_status.setText(
                    f"Status: ✅ Connected to project '{project_name}'"
                )
                self.connection_status.setStyleSheet("color: green")
                self.translate_text_btn.setEnabled(True)
                self.translate_files_btn.setEnabled(len(self.selected_files) > 0)
            else:
                raise Exception("Project not found or access denied")
        except Exception as e:
            self.connection_status.setText("Status: ❌ Connection error")
            self.connection_status.setStyleSheet("color: red")
            QMessageBox.critical(
                self, "Connection error", f"Failed to connect to API:\n{str(e)}"
            )

    def browse_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select files", "", "All Files (*.*)"
        )
        if files:
            self.selected_files.extend(files)
            self.update_files_list()
            self.translate_files_btn.setEnabled(
                len(self.selected_files) > 0 and self.api_client is not None
            )

    def browse_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select output folder")
        if folder:
            self.output_folder_input.setText(folder)

    def clear_files(self):
        self.selected_files.clear()
        self.update_files_list()
        self.translate_files_btn.setEnabled(False)

    def update_files_list(self):
        self.files_list.clear()
        for file_path in self.selected_files:
            self.files_list.addItem(os.path.basename(file_path))

    def start_text_translation(self):
        source_text = self.text_input.toPlainText().strip()
        if not source_text:
            QMessageBox.warning(self, "Error", "Please enter text for translation")
            return
        if not self.api_client:
            QMessageBox.warning(self, "Error", "First connect to API")
            return
        self.translate_text_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.text_result_output.clear()
        self.worker = TranslationWorker(
            self.api_client,
            source_text,
            self.config["project_id"],
            self.config["source_lang"],
            self.config["target_lang"],
            self.config["max_retries"],
            self.config["retry_delay"],
        )
        self.worker.progress_updated.connect(self.update_progress)
        self.worker.translation_completed.connect(self.text_translation_finished)
        self.worker.error_occurred.connect(self.text_translation_error)
        self.worker.start()

    def start_file_translation(self):
        if not self.selected_files:
            QMessageBox.warning(self, "Error", "Please select files")
            return
        if not self.api_client:
            QMessageBox.warning(self, "Error", "First connect to API")
            return
        output_folder = self.output_folder_input.text().strip() or None
        if output_folder and not os.path.exists(output_folder):
            try:
                os.makedirs(output_folder)
            except Exception as e:
                QMessageBox.warning(
                    self, "Error", f"Cannot create output folder: {str(e)}"
                )
                return
        self.translate_files_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.file_results_output.clear()
        self.file_worker = FileTranslationWorker(
            self.api_client,
            self.selected_files.copy(),
            self.config["project_id"],
            output_folder,
            self.config["files_max_retries"],
            self.config["files_retry_delay"],
        )
        self.file_worker.progress_updated.connect(self.update_progress)
        self.file_worker.file_completed.connect(self.file_translation_update)
        self.file_worker.all_completed.connect(self.file_translation_finished)
        self.file_worker.error_occurred.connect(self.file_translation_error)
        self.file_worker.start()

    def update_progress(self, message):
        self.status_label.setText(message)

    def text_translation_finished(self, result):
        self.text_result_output.setPlainText(result)
        self.status_label.setText("✅ Text translation completed successfully!")
        self.progress_bar.setVisible(False)
        self.translate_text_btn.setEnabled(True)

    def text_translation_error(self, error_message):
        self.text_result_output.setPlainText(f"❌ Error: {error_message}")
        self.status_label.setText("❌ Error during text translation")
        self.progress_bar.setVisible(False)
        self.translate_text_btn.setEnabled(True)
        QMessageBox.critical(self, "Error", error_message)

    def file_translation_update(self, filename, status):
        current_text = self.file_results_output.toPlainText()
        new_text = (
            f"{current_text}\n{filename}: {status}"
            if current_text
            else f"{filename}: {status}"
        )
        self.file_results_output.setPlainText(new_text)
        cursor = self.file_results_output.textCursor()
        cursor.movePosition(cursor.End)
        self.file_results_output.setTextCursor(cursor)

    def file_translation_finished(self, summary):
        self.file_results_output.append(f"\n{summary}")
        self.status_label.setText("✅ File translation completed!")
        self.progress_bar.setVisible(False)
        self.translate_files_btn.setEnabled(True)
        QMessageBox.information(
            self,
            "Translation Complete",
            "File translation has been completed! Check the results below.",
        )

    def file_translation_error(self, error_message):
        self.file_results_output.append(f"\n❌ Critical Error: {error_message}")
        self.status_label.setText("❌ Critical error during file translation")
        self.progress_bar.setVisible(False)
        self.translate_files_btn.setEnabled(True)
        QMessageBox.critical(self, "Error", error_message)

    def clear_all(self):
        self.text_input.clear()
        self.text_result_output.clear()
        self.file_results_output.clear()
        self.selected_files.clear()
        self.update_files_list()
        self.output_folder_input.clear()
        self.status_label.setText("Ready to work")
        self.translate_files_btn.setEnabled(False)

import sys
import os
import time
import json
import tempfile
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from PyQt5.QtWidgets import (
    QApplication,
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
from PyQt5.QtCore import QThread, pyqtSignal

# Імпортуємо класи SmartCAT API
from api import SmartCAT

# Завантажуємо змінні з .env файлу
load_dotenv()


class TranslationWorker(QThread):
    """Робочий потік для виконання перекладу тексту в фоновому режимі"""

    progress_updated = pyqtSignal(str)
    translation_completed = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, api_client, source_text, project_id):
        super().__init__()
        self.api_client = api_client
        self.source_text = source_text
        self.project_id = project_id
        self.source_lang = os.getenv("SOURCE_LANGUAGE", "ru")
        self.target_lang = os.getenv("TARGET_LANGUAGE", "en")
        self.max_retries = int(os.getenv("MAX_RETRIES", "60"))
        self.retry_delay = int(os.getenv("RETRY_DELAY", "5"))

    def run(self):
        try:
            # Крок 1: Створення JSON документа
            self.progress_updated.emit("Creating JSON document...")
            json_data = {
                "data": self.source_text,
            }

            # Створюємо тимчасовий JSON файл
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False, encoding="utf-8"
            ) as temp_file:
                json.dump(json_data, temp_file, ensure_ascii=False, indent=2)
                temp_file_path = temp_file.name

            # Крок 2: Завантаження документа до існуючого проекту
            self.progress_updated.emit(
                f"Uploading document to project {self.project_id}..."
            )

            with open(temp_file_path, "rb") as file:
                files = {
                    "file": (
                        f'source_text_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json',
                        file,
                        "multipart/form-data",
                    )
                }
                doc_response = self.api_client.project.attach_document(
                    self.project_id, files
                )

            if doc_response.status_code != 200:
                raise Exception(
                    f"Document upload error: {doc_response.status_code} - {doc_response.text}"
                )

            doc_data = doc_response.json()
            if not doc_data or len(doc_data) == 0:
                raise Exception("Failed to retrieve uploaded document info")

            document_id = (
                doc_data[0].get("id")
                if isinstance(doc_data, list)
                else doc_data.get("id")
            )

            if not document_id:
                raise Exception("Failed to get document ID")

            self.progress_updated.emit(f"Document uploaded with ID: {document_id}")

            # Крок 3: Очікування перекладу
            self.progress_updated.emit("Waiting for translation to complete...")
            attempt = 0

            while attempt < self.max_retries:
                time.sleep(self.retry_delay)
                attempt += 1

                try:
                    self.progress_updated.emit(
                            f"Checking status... Attempt {attempt}/{self.max_retries}"
                    )
                except Exception as e:
                    self.progress_updated.emit(
                        f"Status check error: {str(e)} (attempt {attempt}/{self.max_retries})"
                    )

            # Крок 4: Експорт перекладу
            self.progress_updated.emit("Requesting translation export...")
            export_response = self.api_client.document.request_export(
                [document_id], target_type="target"
            )

            if export_response.status_code != 200:
                raise Exception(
                    f"Export request error: {export_response.status_code} - {export_response.text}"
                )

            export_data = export_response.json()
            task_id = export_data.get("id")

            if not task_id:
                raise Exception("Failed to get export task ID")

            # Крок 5: Очікуємо завершення експорту та завантажуємо результат
            export_attempts = 0
            max_export_attempts = 30

            while export_attempts < max_export_attempts:
                time.sleep(self.retry_delay)
                export_attempts += 1

                self.progress_updated.emit(
                    f"Downloading result... Attempt {export_attempts}/{max_export_attempts}"
                )

                try:
                    download_response = self.api_client.document.download_export_result(
                        task_id
                    )
                    if download_response.status_code == 200:
                        # Зберігаємо результат
                        result_content = download_response.text

                        try:
                            # Якщо результат є JSON, витягуємо переклад
                            result_json = json.loads(result_content)
                            if isinstance(result_json, dict) and "data" in result_json:
                                translated_text = result_json.get(
                                    "data", result_content
                                )
                            else:
                                translated_text = result_content
                        except json.JSONDecodeError:
                            # Якщо не JSON, використовуємо як є
                            translated_text = result_content

                        # Виводимо лише сам переклад
                        self.translation_completed.emit(translated_text)

                        try:
                            self.progress_updated.emit(
                                "Deleting document from project..."
                            )
                            delete_response = self.api_client.document.delete(
                                document_id
                            )
                            if delete_response.status_code == 204:
                                self.progress_updated.emit(
                                    "Document successfully deleted from project"
                                )
                            else:
                                self.progress_updated.emit(
                                    f"Warning: failed to delete document (code: {delete_response.status_code})"
                                )
                        except Exception as delete_error:
                            self.progress_updated.emit(
                                f"Warning: error deleting document: {str(delete_error)}"
                            )

                        break

                    elif download_response.status_code == 202:
                        # Експорт ще обробляється
                        continue
                    else:
                        raise Exception(
                            f"Download error: {download_response.status_code}"
                        )

                except Exception as e:
                    if export_attempts >= max_export_attempts:
                        raise Exception(
                            f"Failed to download result after {max_export_attempts} attempts: {str(e)}"
                        )
                    continue

            # Очищення тимчасових файлів
            try:
                os.unlink(temp_file_path)
            except:
                pass

        except Exception as e:
            self.error_occurred.emit(f"Error: {str(e)}")


class FileTranslationWorker(QThread):
    """Робочий потік для виконання перекладу файлів в фоновому режимі"""

    progress_updated = pyqtSignal(str)
    file_completed = pyqtSignal(str, str)  # filename, status
    all_completed = pyqtSignal(str)  # summary
    error_occurred = pyqtSignal(str)

    def __init__(self, api_client, file_paths, project_id, output_folder=None):
        super().__init__()
        self.api_client = api_client
        self.file_paths = file_paths
        self.project_id = project_id
        self.output_folder = output_folder
        self.max_retries = int(os.getenv("FILES_MAX_RETRIES", "5"))
        self.retry_delay = int(os.getenv("FILES_RETRY_DELAY", "60"))

    def run(self):
        try:
            successful_files = []
            failed_files = []
            
            total_files = len(self.file_paths)
            
            for i, file_path in enumerate(self.file_paths, 1):
                try:
                    filename = os.path.basename(file_path)
                    self.progress_updated.emit(f"Processing file {i}/{total_files}: {filename}")
                    
                    # Крок 1: Завантаження файлу до проекту
                    self.progress_updated.emit(f"Uploading {filename}...")
                    
                    with open(file_path, "rb") as file:
                        files = {
                            "file": (filename, file, "multipart/form-data")
                        }
                        doc_response = self.api_client.project.attach_document(
                            self.project_id, files
                        )

                    if doc_response.status_code != 200:
                        raise Exception(
                            f"Upload error: {doc_response.status_code} - {doc_response.text}"
                        )

                    doc_data = doc_response.json()
                    document_id = (
                        doc_data[0].get("id")
                        if isinstance(doc_data, list)
                        else doc_data.get("id")
                    )

                    if not document_id:
                        raise Exception("Failed to get document ID")

                    self.progress_updated.emit(f"File {filename} uploaded with ID: {document_id}")

                    # Крок 2: Очікування перекладу
                    self.progress_updated.emit(f"Waiting for translation of {filename}...")
                    for attempt in range(1, self.max_retries + 1):
                        try:
                            doc_response = self.api_client.project.get(self.project_id)
                            if doc_response.status_code != 200:
                                self.error_occurred.emit(f"❌ Failed to get project data (attempt {attempt})")
                                time.sleep(self.retry_delay)
                                continue
                            
                            doc_data = doc_response.json()
                            documents = doc_data.get("documents", [])
                            total_docs = len(documents)

                            if total_docs == 0:
                                self.error_occurred.emit("❗ No documents found in the project.")
                                return
                            
                            completed = 0
                            for doc in documents:
                                filename = doc.get("filename", "Unnamed file")
                                status = doc.get("status", "Unknown")
                                if status == "completed":
                                    completed += 1
                                else:
                                    self.progress_updated.emit(f"⏳ {filename}: status = {status}")
                            
                            if completed == total_docs:
                                self.file_completed.emit(filename, "✅ All documents are completed!")
                                break
                            else:
                                self.progress_updated.emit(f"⏳ {completed}/{total_docs} documents completed. Retrying... (attempt {attempt})")
                                time.sleep(self.retry_delay)
                            
                        except Exception as e:
                            self.error_occurred.emit(f"❌ Error during document status check: {str(e)}")
                            time.sleep(self.retry_delay)
                        
                    # Крок 3: Експорт перекладу
                    self.progress_updated.emit(f"Requesting export for {filename}...")
                    export_response = self.api_client.document.request_export(
                        [document_id], target_type="target"
                    )

                    if export_response.status_code != 200:
                        raise Exception(
                            f"Export request error: {export_response.status_code}"
                        )

                    export_data = export_response.json()
                    task_id = export_data.get("id")

                    if not task_id:
                        raise Exception("Failed to get export task ID")

                    # Крок 4: Завантаження результату
                    export_attempts = 0
                    max_export_attempts = 30

                    while export_attempts < max_export_attempts:
                        time.sleep(self.retry_delay)
                        export_attempts += 1

                        self.progress_updated.emit(
                            f"Downloading {filename}... Attempt {export_attempts}/{max_export_attempts}"
                        )

                        try:
                            download_response = self.api_client.document.download_export_result(
                                task_id
                            )
                            if download_response.status_code == 200:
                                # Визначаємо шлях збереження
                                if self.output_folder:
                                    output_dir = self.output_folder
                                else:
                                    output_dir = os.path.dirname(file_path)

                                # Створюємо ім'я файлу з суфіксом
                                file_stem = Path(filename).stem
                                file_ext = Path(filename).suffix
                                translated_filename = f"{file_stem}_translated{file_ext}"
                                output_path = os.path.join(output_dir, translated_filename)

                                # Зберігаємо файл
                                with open(output_path, "wb") as f:
                                    f.write(download_response.content)

                                successful_files.append((filename, output_path))
                                self.file_completed.emit(filename, f"✅ Saved to: {output_path}")

                                # Видаляємо документ з проекту
                                try:
                                    delete_response = self.api_client.document.delete(document_id)
                                    if delete_response.status_code == 204:
                                        self.progress_updated.emit(f"Document {filename} cleaned up")
                                except Exception:
                                    pass  # Не критично якщо не вдалося видалити

                                break

                            elif download_response.status_code == 202:
                                # Експорт ще обробляється
                                continue
                            else:
                                raise Exception(
                                    f"Download error: {download_response.status_code}"
                                )

                        except Exception as e:
                            if export_attempts >= max_export_attempts:
                                raise Exception(
                                    f"Failed to download after {max_export_attempts} attempts: {str(e)}"
                                )
                            continue

                except Exception as e:
                    failed_files.append((filename, str(e))) # type: ignore
                    self.file_completed.emit(filename, f"❌ Error: {str(e)}") # type: ignore

            # Підсумок
            summary = f"""
📊 Translation Summary:
✅ Successfully translated: {len(successful_files)} files
❌ Failed: {len(failed_files)} files

Successful files:
""" + "\n".join([f"• {name} → {path}" for name, path in successful_files])

            if failed_files:
                summary += "\n\nFailed files:\n" + "\n".join([f"• {name}: {error}" for name, error in failed_files])

            self.all_completed.emit(summary)

        except Exception as e:
            self.error_occurred.emit(f"Critical error: {str(e)}")


class SmartCATGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.api_client = None
        self.worker = None
        self.file_worker = None
        self.selected_files = []

        # Завантажуємо конфігурацію з .env
        self.load_env_config()
        self.init_ui()
        self.auto_connect()

    def load_env_config(self):
        """Завантажує конфігурацію з .env файлу"""
        self.username = os.getenv("SMARTCAT_USERNAME", "")
        self.password = os.getenv("SMARTCAT_PASSWORD", "")
        self.server_url = os.getenv("SMARTCAT_SERVER", "https://smartcat.ai")
        self.project_id = os.getenv("SMARTCAT_PROJECT_ID", "")
        self.source_lang = os.getenv("SOURCE_LANGUAGE", "ru")
        self.target_lang = os.getenv("TARGET_LANGUAGE", "en")
        self.app_title = os.getenv("APP_TITLE", "SmartCAT Russian-English Translator")

    def init_ui(self):
        self.setWindowTitle(self.app_title)
        self.setGeometry(100, 100, 800, 700)

        # Центральний віджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Інформація про конфігурацію
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

        # Створюємо вкладки
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Вкладка для перекладу тексту
        self.create_text_translation_tab()

        # Вкладка для перекладу файлів
        self.create_file_translation_tab()

        # Прогрес-бар (загальний)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Статус (загальний)
        self.status_label = QLabel("Ready to work")
        self.status_label.setStyleSheet("QLabel { color: #666; font-style: italic; }")
        layout.addWidget(self.status_label)

        # Кнопки управління
        button_layout = QHBoxLayout()

        self.clear_btn = QPushButton("🗑️ Clear All")
        self.clear_btn.clicked.connect(self.clear_all)
        button_layout.addWidget(self.clear_btn)

        self.refresh_btn = QPushButton("🔄 Refresh Configuration")
        self.refresh_btn.clicked.connect(self.refresh_config)
        button_layout.addWidget(self.refresh_btn)

        layout.addLayout(button_layout)

    def create_text_translation_tab(self):
        """Створює вкладку для перекладу тексту"""
        text_tab = QWidget()
        self.tabs.addTab(text_tab, "📝 Text Translation")
        
        layout = QVBoxLayout(text_tab)

        # Поле для введення тексту
        input_group = QGroupBox(
            f"Text for translation ({self.source_lang.upper()} → {self.target_lang.upper()})"
        )
        input_layout = QVBoxLayout()

        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText(
            "Enter text for translation..."
        )
        self.text_input.setMaximumHeight(120)
        input_layout.addWidget(self.text_input)

        # Кнопка перекладу тексту
        self.translate_text_btn = QPushButton("🔄 Translate Text")
        self.translate_text_btn.clicked.connect(self.start_text_translation)
        self.translate_text_btn.setEnabled(False)
        self.translate_text_btn.setStyleSheet(
            "QPushButton { font-size: 14px; padding: 8px; }"
        )
        input_layout.addWidget(self.translate_text_btn)

        input_group.setLayout(input_layout)
        layout.addWidget(input_group)

        # Поле для виведення результату тексту
        result_group = QGroupBox("Translation result")
        result_layout = QVBoxLayout()

        self.text_result_output = QTextEdit()
        self.text_result_output.setReadOnly(True)
        self.text_result_output.setPlaceholderText("Translation result will appear here...")
        result_layout.addWidget(self.text_result_output)

        result_group.setLayout(result_layout)
        layout.addWidget(result_group)

    def create_file_translation_tab(self):
        """Створює вкладку для перекладу файлів"""
        file_tab = QWidget()
        self.tabs.addTab(file_tab, "📁 File Translation")
        
        layout = QVBoxLayout(file_tab)

        # Секція вибору файлів
        file_selection_group = QGroupBox("File Selection")
        file_selection_layout = QVBoxLayout()

        # Кнопки для вибору файлів
        file_buttons_layout = QHBoxLayout()
        
        self.browse_files_btn = QPushButton("📂 Browse Files")
        self.browse_files_btn.clicked.connect(self.browse_files)
        file_buttons_layout.addWidget(self.browse_files_btn)

        self.clear_files_btn = QPushButton("🗑️ Clear Files")
        self.clear_files_btn.clicked.connect(self.clear_files)
        file_buttons_layout.addWidget(self.clear_files_btn)

        file_selection_layout.addLayout(file_buttons_layout)

        # Список вибраних файлів
        self.files_list = QListWidget()
        self.files_list.setMaximumHeight(100)
        file_selection_layout.addWidget(self.files_list)

        file_selection_group.setLayout(file_selection_layout)
        layout.addWidget(file_selection_group)

        # Секція налаштувань збереження
        output_group = QGroupBox("Output Settings")
        output_layout = QFormLayout()

        # Поле для папки збереження
        folder_layout = QHBoxLayout()
        self.output_folder_input = QLineEdit()
        self.output_folder_input.setPlaceholderText("Optional: Select folder for translated files (leave empty to save next to originals)")
        folder_layout.addWidget(self.output_folder_input)

        self.browse_folder_btn = QPushButton("📁 Browse Folder")
        self.browse_folder_btn.clicked.connect(self.browse_output_folder)
        folder_layout.addWidget(self.browse_folder_btn)

        output_layout.addRow("Translated Files Folder:", folder_layout)
        output_group.setLayout(output_layout)
        layout.addWidget(output_group)

        # Кнопка перекладу файлів
        self.translate_files_btn = QPushButton("🔄 Translate Files")
        self.translate_files_btn.clicked.connect(self.start_file_translation)
        self.translate_files_btn.setEnabled(False)
        self.translate_files_btn.setStyleSheet(
            "QPushButton { font-size: 14px; padding: 8px; background-color: #4CAF50; color: white; }"
        )
        layout.addWidget(self.translate_files_btn)

        # Результати перекладу файлів
        file_results_group = QGroupBox("Translation Results")
        file_results_layout = QVBoxLayout()

        self.file_results_output = QTextEdit()
        self.file_results_output.setReadOnly(True)
        self.file_results_output.setPlaceholderText("File translation results will appear here...")
        file_results_layout.addWidget(self.file_results_output)

        file_results_group.setLayout(file_results_layout)
        layout.addWidget(file_results_group)

    def update_config_display(self):
        """Оновлює відображення конфігурації"""
        config_text = f"""
📡 Server: {self.server_url}
👤 User: {self.username[:3]}***
🆔 Project ID: {self.project_id}
🔤 Language pair: {self.source_lang.upper()} → {self.target_lang.upper()}
        """.strip()
        self.config_info.setText(config_text)

    def refresh_config(self):
        """Перезавантажує конфігурацію з .env файлу"""
        load_dotenv(override=True)
        self.load_env_config()
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
        """Автоматично підключається при запуску, якщо є всі дані"""
        if self.username and self.password and self.project_id:
            self.connect_to_api()

    def connect_to_api(self):
        """Підключається до SmartCAT API"""
        if not self.username or not self.password:
            QMessageBox.warning(
                self,
                "Error",
                "Please set SMARTCAT_USERNAME and SMARTCAT_PASSWORD in .env file",
            )
            return

        if not self.project_id:
            QMessageBox.warning(
                self,
                "Error",
                "Please set SMARTCAT_PROJECT_ID in .env file",
            )
            return

        try:
            self.connection_status.setText("Status: Connecting...")
            self.connection_status.setStyleSheet("color: orange")

            self.api_client = SmartCAT(self.username, self.password, self.server_url)

            # Тестуємо підключення, перевіряючи існування проекту
            test_response = self.api_client.project.get(self.project_id)
            if test_response.status_code == 200:
                project_data = test_response.json()
                project_name = project_data.get("name", "Unknown")

                self.connection_status.setText(
                    f"Status: ✅ Connected to project '{project_name}'"
                )
                self.connection_status.setStyleSheet("color: green")
                self.translate_text_btn.setEnabled(True)
                self.translate_files_btn.setEnabled(len(self.selected_files) > 0)
                QMessageBox.information(
                    self,
                    "Success",
                    f"Successfully connected to project:\n{project_name}",
                )
            else:
                raise Exception(
                    f"Project with ID {self.project_id} not found or access denied: {test_response.status_code}"
                )

        except Exception as e:
            self.connection_status.setText("Status: ❌ Connection error")
            self.connection_status.setStyleSheet("color: red")
            QMessageBox.critical(
                self,
                "Connection error",
                f"Failed to connect to API:\n{str(e)}",
            )

    def browse_files(self):
        """Відкриває діалог для вибору файлів"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select files for translation",
            "",
            "All Files (*.*)"
        )
        
        if files:
            self.selected_files.extend(files)
            self.update_files_list()
            self.translate_files_btn.setEnabled(
                len(self.selected_files) > 0 and self.api_client is not None
            )

    def browse_output_folder(self):
        """Відкриває діалог для вибору папки збереження"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select folder for translated files"
        )
        
        if folder:
            self.output_folder_input.setText(folder)

    def clear_files(self):
        """Очищає список вибраних файлів"""
        self.selected_files.clear()
        self.update_files_list()
        self.translate_files_btn.setEnabled(False)

    def update_files_list(self):
        """Оновлює відображення списку файлів"""
        self.files_list.clear()
        for file_path in self.selected_files:
            self.files_list.addItem(os.path.basename(file_path))

    def start_text_translation(self):
        """Запускає процес перекладу тексту"""
        source_text = self.text_input.toPlainText().strip()

        if not source_text:
            QMessageBox.warning(self, "Error", "Please enter text for translation")
            return

        if not self.api_client:
            QMessageBox.warning(self, "Error", "First connect to API")
            return

        # Блокуємо інтерфейс під час перекладу
        self.translate_text_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Індетермінований прогрес
        self.text_result_output.clear()

        # Запускаємо робочий потік
        self.worker = TranslationWorker(self.api_client, source_text, self.project_id)

        self.worker.progress_updated.connect(self.update_progress)
        self.worker.translation_completed.connect(self.text_translation_finished)
        self.worker.error_occurred.connect(self.text_translation_error)

        self.worker.start()

    def start_file_translation(self):
        """Запускає процес перекладу файлів"""
        if not self.selected_files:
            QMessageBox.warning(self, "Error", "Please select files for translation")
            return

        if not self.api_client:
            QMessageBox.warning(self, "Error", "First connect to API")
            return

        # Отримуємо папку для збереження
        output_folder = self.output_folder_input.text().strip() or None
        
        if output_folder and not os.path.exists(output_folder):
            try:
                os.makedirs(output_folder)
            except Exception as e:
                QMessageBox.warning(
                    self, 
                    "Error", 
                    f"Cannot create output folder: {str(e)}"
                )
                return

        # Блокуємо інтерфейс під час перекладу
        self.translate_files_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.file_results_output.clear()

        # Запускаємо робочий потік для файлів
        self.file_worker = FileTranslationWorker(
            self.api_client, 
            self.selected_files.copy(), 
            self.project_id,
            output_folder
        )

        self.file_worker.progress_updated.connect(self.update_progress)
        self.file_worker.file_completed.connect(self.file_translation_update)
        self.file_worker.all_completed.connect(self.file_translation_finished)
        self.file_worker.error_occurred.connect(self.file_translation_error)

        self.file_worker.start()

    def update_progress(self, message):
        """Оновлює статус прогресу"""
        self.status_label.setText(message)

    def text_translation_finished(self, result):
        """Обробляє завершення перекладу тексту"""
        self.text_result_output.setPlainText(result)
        self.status_label.setText("✅ Text translation completed successfully!")
        self.progress_bar.setVisible(False)
        self.translate_text_btn.setEnabled(True)

    def text_translation_error(self, error_message):
        """Обробляє помилки перекладу тексту"""
        self.text_result_output.setPlainText(f"❌ Error: {error_message}")
        self.status_label.setText("❌ Error during text translation")
        self.progress_bar.setVisible(False)
        self.translate_text_btn.setEnabled(True)
        QMessageBox.critical(self, "Error", error_message)

    def file_translation_update(self, filename, status):
        """Оновлює статус перекладу окремого файлу"""
        current_text = self.file_results_output.toPlainText()
        new_text = f"{current_text}\n{filename}: {status}" if current_text else f"{filename}: {status}"
        self.file_results_output.setPlainText(new_text)
        
        # Прокручуємо до кінця
        cursor = self.file_results_output.textCursor()
        cursor.movePosition(cursor.End)
        self.file_results_output.setTextCursor(cursor)

    def file_translation_finished(self, summary):
        """Обробляє завершення перекладу всіх файлів"""
        self.file_results_output.append(f"\n{summary}")
        self.status_label.setText("✅ File translation completed!")
        self.progress_bar.setVisible(False)
        self.translate_files_btn.setEnabled(True)
        
        # Показуємо повідомлення про завершення
        QMessageBox.information(
            self, 
            "Translation Complete", 
            "File translation has been completed! Check the results below."
        )

    def file_translation_error(self, error_message):
        """Обробляє критичні помилки перекладу файлів"""
        self.file_results_output.append(f"\n❌ Critical Error: {error_message}")
        self.status_label.setText("❌ Critical error during file translation")
        self.progress_bar.setVisible(False)
        self.translate_files_btn.setEnabled(True)
        QMessageBox.critical(self, "Error", error_message)

    def clear_all(self):
        """Очищає всі поля"""
        self.text_input.clear()
        self.text_result_output.clear()
        self.file_results_output.clear()
        self.selected_files.clear()
        self.update_files_list()
        self.output_folder_input.clear()
        self.status_label.setText("Ready to work")
        self.translate_files_btn.setEnabled(False)


def main():
    # Перевіряємо наявність .env файлу
    if not os.path.exists(".env"):
        print("❌ .env file not found!")
        print("Create .env file with the required variables:")
        print("SMARTCAT_USERNAME=your_username")
        print("SMARTCAT_PASSWORD=your_password")
        print("SMARTCAT_PROJECT_ID=your_project_id")
        return

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Створюємо та показуємо головне вікно
    window = SmartCATGUI()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
    
import sys
import os
import time
import json
import tempfile
from datetime import datetime
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
)
from PyQt5.QtCore import QThread, pyqtSignal

# Імпортуємо класи SmartCAT API
from api import SmartCAT

# Завантажуємо змінні з .env файлу
load_dotenv()


class TranslationWorker(QThread):
    """Робочий потік для виконання перекладу в фоновому режимі"""

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
                    # Перевіряємо статус проекту
                    project_status = self.api_client.project.get(self.project_id)
                    if project_status.status_code == 200:
                        status_data = project_status.json()
                        progress = status_data.get("progress", 0)
                        self.progress_updated.emit(
                            f"Translation progress: {progress}% (спроба {attempt}/{self.max_retries})"
                        )

                        if progress >= 100:
                            break
                    else:
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

                        # Створюємо результат для відображення
                        translation_result = f"""✅ TRANSLATION COMPLETED SUCCESSFULLY!

🔤 Source text ({self.source_lang.upper()}):
{self.source_text}
"""

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


class SmartCATGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.api_client = None
        self.worker = None

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
        self.setGeometry(100, 100, 700, 500)

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

        # Поле для введення тексту
        input_group = QGroupBox(
            f"Text for translation ({self.source_lang.upper()} → {self.target_lang.upper()})"
        )
        input_layout = QVBoxLayout()

        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText(
            "Enter Russian text for translation into English..."
        )
        self.text_input.setMaximumHeight(120)
        input_layout.addWidget(self.text_input)

        # Кнопка перекладу
        self.translate_btn = QPushButton("🔄 Translate")
        self.translate_btn.clicked.connect(self.start_translation)
        self.translate_btn.setEnabled(False)
        self.translate_btn.setStyleSheet(
            "QPushButton { font-size: 14px; padding: 8px; }"
        )
        input_layout.addWidget(self.translate_btn)

        input_group.setLayout(input_layout)
        layout.addWidget(input_group)

        # Прогрес-бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Статус
        self.status_label = QLabel("Ready to work")
        self.status_label.setStyleSheet("QLabel { color: #666; font-style: italic; }")
        layout.addWidget(self.status_label)

        # Поле для виведення результату
        result_group = QGroupBox("Translation result")
        result_layout = QVBoxLayout()

        self.result_output = QTextEdit()
        self.result_output.setReadOnly(True)
        self.result_output.setPlaceholderText("Translation result will appear here...")
        result_layout.addWidget(self.result_output)

        result_group.setLayout(result_layout)
        layout.addWidget(result_group)

        # Кнопки управління
        button_layout = QHBoxLayout()

        self.clear_btn = QPushButton("🗑️ Clear")
        self.clear_btn.clicked.connect(self.clear_all)
        button_layout.addWidget(self.clear_btn)

        self.refresh_btn = QPushButton("🔄 Refresh configuration")
        self.refresh_btn.clicked.connect(self.refresh_config)
        button_layout.addWidget(self.refresh_btn)

        layout.addLayout(button_layout)

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
        self.translate_btn.setEnabled(False)
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
                self.translate_btn.setEnabled(True)
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

    def start_translation(self):
        """Запускає процес перекладу"""
        source_text = self.text_input.toPlainText().strip()

        if not source_text:
            QMessageBox.warning(self, "Error", "Please enter text for translation")
            return

        if not self.api_client:
            QMessageBox.warning(self, "Error", "Спочатку підключіться до API")
            return

        # Блокуємо інтерфейс під час перекладу
        self.translate_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Індетермінований прогрес
        self.result_output.clear()

        # Запускаємо робочий потік
        self.worker = TranslationWorker(self.api_client, source_text, self.project_id)

        self.worker.progress_updated.connect(self.update_progress)
        self.worker.translation_completed.connect(self.translation_finished)
        self.worker.error_occurred.connect(self.translation_error)

        self.worker.start()

    def update_progress(self, message):
        """Оновлює статус прогресу"""
        self.status_label.setText(message)

    def translation_finished(self, result):
        """Обробляє завершення перекладу"""
        self.result_output.setPlainText(result)
        self.status_label.setText("✅ Translation completed successfully!")
        self.progress_bar.setVisible(False)
        self.translate_btn.setEnabled(True)

    def translation_error(self, error_message):
        """Обробляє помилки перекладу"""
        self.result_output.setPlainText(f"❌ Error: {error_message}")
        self.status_label.setText("❌ Error during translation")
        self.progress_bar.setVisible(False)
        self.translate_btn.setEnabled(True)

        QMessageBox.critical(self, "Error", error_message)

    def clear_all(self):
        """Очищає всі поля"""
        self.text_input.clear()
        self.result_output.clear()
        self.status_label.setText("Ready to work")


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

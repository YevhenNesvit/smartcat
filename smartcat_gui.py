import sys
import zipfile
import os
import time
import io
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
    QLineEdit,
    QProgressBar,
    QMessageBox,
    QGroupBox,
    QFormLayout,
)
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QFont

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
            self.progress_updated.emit("Створення JSON документа...")
            # json_data = {
            #     "source_text": self.source_text,
            #     "source_language": self.source_lang,
            #     "target_language": self.target_lang,
            #     "project_id": self.project_id,
            #     "timestamp": datetime.now().isoformat(),
            #     "status": "processing"
            # }

            # Створюємо тимчасовий JSON файл
            # with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as temp_file:
            #     json.dump(json_data, temp_file, ensure_ascii=False, indent=2)
            #     temp_file_path = temp_file.name

            # Створюємо тимчасовий TXT файл
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False, encoding="utf-8"
            ) as temp_file:
                temp_file.write(self.source_text)
                temp_file_path = temp_file.name

            # Крок 2: Завантаження документа до існуючого проекту
            self.progress_updated.emit(
                f"Завантаження документа до проекту {self.project_id}..."
            )

            with open(temp_file_path, "rb") as file:
                files = {
                    "file": (
                        f'source_text_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt',
                        file,
                        "text/plain",
                    )
                }
                doc_response = self.api_client.project.attach_document(
                    self.project_id, files
                )

            if doc_response.status_code != 200:
                raise Exception(
                    f"Помилка завантаження документа: {doc_response.status_code} - {doc_response.text}"
                )

            doc_data = doc_response.json()
            if not doc_data or len(doc_data) == 0:
                raise Exception(
                    "Не вдалося отримати інформацію про завантажений документ"
                )

            document_id = (
                doc_data[0].get("id")
                if isinstance(doc_data, list)
                else doc_data.get("id")
            )

            if not document_id:
                raise Exception("Не вдалося отримати ID документа")

            self.progress_updated.emit(f"Документ завантажено з ID: {document_id}")

            # Крок 3: Очікування перекладу
            self.progress_updated.emit("Очікування завершення перекладу...")
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
                            f"Прогрес перекладу: {progress}% (спроба {attempt}/{self.max_retries})"
                        )

                        if progress >= 100:
                            break
                    else:
                        self.progress_updated.emit(
                            f"Перевірка статусу... Спроба {attempt}/{self.max_retries}"
                        )
                except Exception as e:
                    self.progress_updated.emit(
                        f"Помилка перевірки статусу: {str(e)} (спроба {attempt}/{self.max_retries})"
                    )

            # Крок 4: Експорт перекладу
            self.progress_updated.emit("Запит експорту перекладу...")
            export_response = self.api_client.document.request_export(
                [document_id], target_type="target"
            )

            if export_response.status_code != 200:
                raise Exception(
                    f"Помилка запиту експорту: {export_response.status_code} - {export_response.text}"
                )

            export_data = export_response.json()
            task_id = export_data.get("id")

            if not task_id:
                raise Exception("Не вдалося отримати ID задачі експорту")

            # Крок 5: Очікуємо завершення експорту та завантажуємо результат
            export_attempts = 0
            max_export_attempts = 30

            while export_attempts < max_export_attempts:
                time.sleep(self.retry_delay)
                export_attempts += 1

                self.progress_updated.emit(
                    f"Завантаження результату... Спроба {export_attempts}/{max_export_attempts}"
                )

                try:
                    download_response = self.api_client.document.download_export_result(
                        task_id
                    )
                    if download_response.status_code == 200:
                        # Зберігаємо результат
                        translated_text = download_response.text

                        # Створюємо результат для відображення
                        translation_result = f"""✅ ПЕРЕКЛАД ЗАВЕРШЕНО УСПІШНО!

🔤 Оригінальний текст ({self.source_lang.upper()}):
{self.source_text}
"""

                        # Виводимо лише сам переклад
                        self.translation_completed.emit(translated_text)

                        try:
                            self.progress_updated.emit("Видалення документа з проекту...")
                            delete_response = self.api_client.document.delete(document_id)
                            if delete_response.status_code == 200:
                                self.progress_updated.emit("Документ успішно видалено з проекту")
                            else:
                                self.progress_updated.emit(f"Попередження: не вдалося видалити документ (код: {delete_response.status_code})")
                        except Exception as delete_error:
                            self.progress_updated.emit(f"Попередження: помилка видалення документа: {str(delete_error)}")
                        
                        break

                    elif download_response.status_code == 202:
                        # Експорт ще обробляється
                        continue
                    else:
                        raise Exception(
                            f"Помилка завантаження: {download_response.status_code}"
                        )

                except Exception as e:
                    if export_attempts >= max_export_attempts:
                        raise Exception(
                            f"Не вдалося завантажити результат після {max_export_attempts} спроб: {str(e)}"
                        )
                    continue

            # Очищення тимчасових файлів
            try:
                os.unlink(temp_file_path)
            except:
                pass

        except Exception as e:
            self.error_occurred.emit(f"Помилка: {str(e)}")


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
        config_group = QGroupBox("Конфігурація (з .env файлу)")
        config_layout = QFormLayout()

        self.config_info = QLabel()
        self.update_config_display()
        config_layout.addRow(self.config_info)

        self.connect_btn = QPushButton("Підключитися до SmartCAT")
        self.connect_btn.clicked.connect(self.connect_to_api)
        config_layout.addRow(self.connect_btn)

        self.connection_status = QLabel("Статус: Не підключено")
        config_layout.addRow(self.connection_status)

        config_group.setLayout(config_layout)
        layout.addWidget(config_group)

        # Поле для введення тексту
        input_group = QGroupBox(
            f"Текст для перекладу ({self.source_lang.upper()} → {self.target_lang.upper()})"
        )
        input_layout = QVBoxLayout()

        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText(
            "Введіть російський текст для перекладу на англійську..."
        )
        self.text_input.setMaximumHeight(120)
        input_layout.addWidget(self.text_input)

        # Кнопка перекладу
        self.translate_btn = QPushButton("🔄 Перекласти")
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
        self.status_label = QLabel("Готовий до роботи")
        self.status_label.setStyleSheet("QLabel { color: #666; font-style: italic; }")
        layout.addWidget(self.status_label)

        # Поле для виведення результату
        result_group = QGroupBox("Результат перекладу")
        result_layout = QVBoxLayout()

        self.result_output = QTextEdit()
        self.result_output.setReadOnly(True)
        self.result_output.setPlaceholderText("Тут з'явиться результат перекладу...")
        result_layout.addWidget(self.result_output)

        result_group.setLayout(result_layout)
        layout.addWidget(result_group)

        # Кнопки управління
        button_layout = QHBoxLayout()

        self.clear_btn = QPushButton("🗑️ Очистити")
        self.clear_btn.clicked.connect(self.clear_all)
        button_layout.addWidget(self.clear_btn)

        self.refresh_btn = QPushButton("🔄 Оновити конфігурацію")
        self.refresh_btn.clicked.connect(self.refresh_config)
        button_layout.addWidget(self.refresh_btn)

        layout.addLayout(button_layout)

    def update_config_display(self):
        """Оновлює відображення конфігурації"""
        config_text = f"""
📡 Сервер: {self.server_url}
👤 Користувач: {self.username[:3]}***
🆔 ID проекту: {self.project_id}
🔤 Мовна пара: {self.source_lang.upper()} → {self.target_lang.upper()}
        """.strip()
        self.config_info.setText(config_text)

    def refresh_config(self):
        """Перезавантажує конфігурацію з .env файлу"""
        load_dotenv(override=True)
        self.load_env_config()
        self.update_config_display()
        self.connection_status.setText(
            "Статус: Конфігурацію оновлено. Необхідно перепідключитися."
        )
        self.connection_status.setStyleSheet("color: orange")
        self.translate_btn.setEnabled(False)
        QMessageBox.information(
            self, "Конфігурація", "Конфігурацію оновлено з .env файлу!"
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
                "Помилка",
                "Будь ласка, встановіть SMARTCAT_USERNAME та SMARTCAT_PASSWORD у .env файлі",
            )
            return

        if not self.project_id:
            QMessageBox.warning(
                self,
                "Помилка",
                "Будь ласка, встановіть SMARTCAT_PROJECT_ID у .env файлі",
            )
            return

        try:
            self.connection_status.setText("Статус: Підключення...")
            self.connection_status.setStyleSheet("color: orange")

            self.api_client = SmartCAT(self.username, self.password, self.server_url)

            # Тестуємо підключення, перевіряючи існування проекту
            test_response = self.api_client.project.get(self.project_id)
            if test_response.status_code == 200:
                project_data = test_response.json()
                project_name = project_data.get("name", "Unknown")

                self.connection_status.setText(
                    f"Статус: ✅ Підключено до проекту '{project_name}'"
                )
                self.connection_status.setStyleSheet("color: green")
                self.translate_btn.setEnabled(True)
                QMessageBox.information(
                    self, "Успіх", f"Успішно підключено до проекту:\n{project_name}"
                )
            else:
                raise Exception(
                    f"Проект з ID {self.project_id} не знайдено або немає доступу: {test_response.status_code}"
                )

        except Exception as e:
            self.connection_status.setText("Статус: ❌ Помилка підключення")
            self.connection_status.setStyleSheet("color: red")
            QMessageBox.critical(
                self,
                "Помилка підключення",
                f"Не вдалося підключитися до API:\n{str(e)}",
            )

    def start_translation(self):
        """Запускає процес перекладу"""
        source_text = self.text_input.toPlainText().strip()

        if not source_text:
            QMessageBox.warning(
                self, "Помилка", "Будь ласка, введіть текст для перекладу"
            )
            return

        if not self.api_client:
            QMessageBox.warning(self, "Помилка", "Спочатку підключіться до API")
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
        self.status_label.setText("✅ Переклад завершено успішно!")
        self.progress_bar.setVisible(False)
        self.translate_btn.setEnabled(True)

    def translation_error(self, error_message):
        """Обробляє помилки перекладу"""
        self.result_output.setPlainText(f"❌ Помилка: {error_message}")
        self.status_label.setText("❌ Помилка при перекладі")
        self.progress_bar.setVisible(False)
        self.translate_btn.setEnabled(True)

        QMessageBox.critical(self, "Помилка", error_message)

    def clear_all(self):
        """Очищає всі поля"""
        self.text_input.clear()
        self.result_output.clear()
        self.status_label.setText("Готовий до роботи")


def main():
    # Перевіряємо наявність .env файлу
    if not os.path.exists(".env"):
        print("❌ Файл .env не знайдено!")
        print("Створіть файл .env з необхідними змінними:")
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

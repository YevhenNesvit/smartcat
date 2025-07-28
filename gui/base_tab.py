from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import pyqtSignal


class BaseTranslationTab(QWidget):
    """
    Базовий клас для вкладок перекладу, що надає спільну структуру та функціональність.
    """

    # Сигналы, которые вкладка может выпроминять для главного окна
    translation_started: pyqtSignal = pyqtSignal()
    translation_completed: pyqtSignal = pyqtSignal(str)
    translation_error: pyqtSignal = pyqtSignal(str)
    file_status_updated: pyqtSignal = pyqtSignal(str, str)  # Для файлового перекладу: filename, status
    all_files_completed: pyqtSignal = pyqtSignal(str)  # Для файлового перекладу: summary

    def __init__(self, api_client, config, status_handler, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.config = config
        self.status_handler = status_handler
        self.worker = None  # Посилання на поточний worker

        # Виправлення для "Cannot assign to attribute 'layout'"
        _layout = QVBoxLayout(self)
        self.setLayout(_layout)
        self._main_layout = _layout  # Зберігаємо посилання на об'єкт макета для прямого маніпулювання в підкласах

        # setup_ui() та setup_signals() тепер викликаються в дочірніх класах
        # після ініціалізації їхніх власних атрибутів UI.

    def setup_ui(self):
        """
        Абстрактний метод для налаштування інтерфейсу користувача вкладки.
        Повинен бути реалізований у дочірніх класах.
        """
        raise NotImplementedError("setup_ui must be implemented by subclasses")

    def setup_signals(self):
        """
        Абстрактний метод для підключення сигналів та слотів вкладки.
        Повинен бути реалізований у дочірніх класах.
        """
        raise NotImplementedError("setup_signals must be implemented by subclasses")

    def enable_translation_button(self, enable: bool):
        """
        Вмикає або вимикає кнопку перекладу на вкладці.
        Повинен бути реалізований у дочірніх класах.
        """
        raise NotImplementedError("enable_translation_button must be implemented by subclasses")

    def _handle_worker_progress(self, message: str):
        """Обробник сигналу оновлення прогресу від worker."""
        self.status_handler.update_status(message)

    def _handle_worker_error(self, error_message: str):
        """Обробник сигналу помилки від worker."""
        self.status_handler.show_critical("Error", error_message)
        self.status_handler.hide_progress()
        # Метод 'emit' є стандартним для сигналів PyQt. Якщо ваш лінтер скаржиться,
        # це може бути обмеження статичного аналізу. Код повинен працювати коректно.
        self.translation_error.emit(error_message)  # type: ignore # Передаємо помилку далі
        self.enable_translation_button(True)

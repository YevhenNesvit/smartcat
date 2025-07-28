from PyQt5.QtWidgets import QProgressBar, QLabel, QMessageBox, QWidget
from PyQt5.QtCore import pyqtSignal, QObject


class StatusHandler(QObject):
    """
    Клас для централізованого керування станом інтерфейсу користувача,
    прогрес-баром та відображенням повідомлень.
    """

    # Сигнали для оновлення UI
    status_message_updated: pyqtSignal = pyqtSignal(str)
    progress_bar_visibility_changed: pyqtSignal = pyqtSignal(bool)
    progress_bar_range_changed: pyqtSignal = pyqtSignal(int, int)
    translation_buttons_enabled: pyqtSignal = pyqtSignal(bool)
    file_translation_button_enabled: pyqtSignal = pyqtSignal(bool)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._progress_bar = None
        self._status_label = None
        self._main_window = parent  # Для відображення QMessageBox

    def set_ui_elements(self, progress_bar: QProgressBar, status_label: QLabel):
        """Встановлює віджети UI, якими керуватиме StatusHandler."""
        self._progress_bar = progress_bar
        self._status_label = status_label

        # Підключаємо внутрішні сигнали до віджетів
        self.status_message_updated.connect(self._status_label.setText)
        self.progress_bar_visibility_changed.connect(self._progress_bar.setVisible)
        self.progress_bar_range_changed.connect(self._progress_bar.setRange)

    def update_status(self, message: str):
        """Оновлює текстовий статус у статус-барі."""
        self.status_message_updated.emit(message)

    def show_progress(self):
        """Показує прогрес-бар у невизначеному стані."""
        self.progress_bar_range_changed.emit(0, 0)
        self.progress_bar_visibility_changed.emit(True)

    def hide_progress(self):
        """Приховує прогрес-бар."""
        self.progress_bar_visibility_changed.emit(False)

    def enable_translation_buttons(self, enable: bool):
        """Вмикає або вимикає кнопки перекладу."""
        self.translation_buttons_enabled.emit(enable)

    def enable_file_translation_button(self, enable: bool):
        """Вмикає або вимикає кнопку перекладу файлів."""
        self.file_translation_button_enabled.emit(enable)

    def show_info(self, title: str, message: str):
        """Відображає інформаційне повідомлення."""
        if self._main_window:
            QMessageBox.information(self._main_window, title, message)

    def show_warning(self, title: str, message: str):
        """Відображає попереджувальне повідомлення."""
        if self._main_window:
            QMessageBox.warning(self._main_window, title, message)

    def show_critical(self, title: str, message: str):
        """Відображає критичне повідомлення про помилку."""
        if self._main_window:
            QMessageBox.critical(self._main_window, title, message)

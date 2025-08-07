from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import pyqtSignal


class BaseTranslationTab(QWidget):
    """
    Base class for translation tabs that provides shared structure and functionality.
    """

    # Signals that the tab can emit to the main window.
    translation_started: pyqtSignal = pyqtSignal()
    translation_completed: pyqtSignal = pyqtSignal(str)
    translation_error: pyqtSignal = pyqtSignal(str)
    file_status_updated: pyqtSignal = pyqtSignal(str, str)
    all_files_completed: pyqtSignal = pyqtSignal(str)

    def __init__(self, api_client, config, status_handler, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.config = config
        self.status_handler = status_handler
        self.worker = None

        _layout = QVBoxLayout(self)
        self.setLayout(_layout)
        self._main_layout = _layout  # Store a reference to the layout object for direct manipulation in subclasses.

    def setup_ui(self):
        """
        Abstract method for setting up the tab's user interface.
        Must be implemented in child classes.
        """
        raise NotImplementedError("setup_ui must be implemented by subclasses")

    def setup_signals(self):
        """
        Abstract method for connecting the tab's signals and slots.
        Must be implemented in child classes.
        """
        raise NotImplementedError("setup_signals must be implemented by subclasses")

    def enable_translation_button(self, enable: bool):
        """
        Enables or disables the translate button on the tab.
        Must be implemented in child classes.
        """
        raise NotImplementedError("enable_translation_button must be implemented by subclasses")

    def _handle_worker_progress(self, message: str):
        """Handler for the progress update signal from the worker."""
        self.status_handler.update_status(message)

    def _handle_worker_error(self, error_message: str):
        """Handler for the error signal from the worker."""
        self.status_handler.show_critical("Error", error_message)
        self.status_handler.hide_progress()
        self.translation_error.emit(error_message)  # type: ignore
        self.enable_translation_button(True)

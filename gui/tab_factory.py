from gui.text_tab import TextTranslationTab
from gui.file_tab import FileTranslationTab


class TabFactory:
    """
    Фабрика для створення об'єктів вкладок.
    """

    def __init__(self, api_client, config, status_handler):
        self.api_client = api_client
        self.config = config
        self.status_handler = status_handler

    def create_text_tab(self, parent=None):
        """Створює та повертає екземпляр TextTranslationTab."""
        return TextTranslationTab(self.api_client, self.config, self.status_handler, parent)

    def create_file_tab(self, parent=None):
        """Створює та повертає екземпляр FileTranslationTab."""
        return FileTranslationTab(self.api_client, self.config, self.status_handler, parent)

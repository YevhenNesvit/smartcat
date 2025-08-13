from gui.text_tab import TextTranslationTab
from gui.file_tab import FileTranslationTab


class TabFactory:
    """
    Factory for creating tab objects.
    """

    def __init__(self, api_client, config, status_handler):
        self.api_client = api_client
        self.config = config
        self.status_handler = status_handler

    def create_text_tab(self, parent=None):
        """Creates and returns an instance of TextTranslationTab."""
        return TextTranslationTab(self.api_client, self.config, self.status_handler, parent)

    def create_file_tab(self, parent=None):
        """Creates and returns an instance of FileTranslationTab."""
        return FileTranslationTab(self.api_client, self.config, self.status_handler, parent)

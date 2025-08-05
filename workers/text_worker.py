from PyQt5.QtCore import QThread, pyqtSignal
from services.document_service import DocumentService


class TranslationWorker(QThread):
    progress_updated = pyqtSignal(str)
    translation_completed = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, api_client, source_text, project_id, source_lang, target_lang, max_retries, retry_delay):
        super().__init__()
        self.service = DocumentService(api_client, project_id, max_retries, retry_delay)
        self.source_text = source_text

    def run(self):
        try:
            self.progress_updated.emit("Creating and uploading text document...")
            document_id, temp_path = self.service.upload_text_document(self.source_text)

            self.progress_updated.emit("Checking translation status...")
            self.service.wait_for_translation(document_id, self.progress_updated.emit)

            self.progress_updated.emit("Requesting export...")
            task_id = self.service.request_export(document_id)

            self.progress_updated.emit("Downloading translation result...")
            translated_text = self.service.download_translation(task_id)

            self.translation_completed.emit(translated_text)

            self.service.delete_document(document_id)
            self.progress_updated.emit("Document deleted.")
        except Exception as e:
            self.error_occurred.emit(f"Error: {str(e)}")

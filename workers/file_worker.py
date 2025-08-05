from PyQt5.QtCore import QThread, pyqtSignal
from services.document_service import DocumentService
import os


class FileTranslationWorker(QThread):
    progress_updated = pyqtSignal(str)
    file_completed = pyqtSignal(str, str)
    all_completed = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, api_client, file_paths, project_id, output_folder=None, max_retries=5, retry_delay=60):
        super().__init__()
        self.service = DocumentService(api_client, project_id, max_retries, retry_delay)
        self.file_paths = file_paths
        self.output_folder = output_folder

    def run(self):
        successful, failed = [], []

        try:
            for path in self.file_paths:
                try:
                    self.progress_updated.emit(f"Uploading {os.path.basename(path)}...")
                    document_id = self.service.upload_file_document(path)
                    self.progress_updated.emit(f"Uploaded with ID {document_id}")
                    successful.append((path, document_id))
                except Exception as e:
                    self.file_completed.emit(path, f"❌ {str(e)}")
                    failed.append((path, str(e)))

            self.service.wait_for_all([doc_id for _, doc_id in successful], self.progress_updated.emit)

            for path, doc_id in successful:
                try:
                    task_id = self.service.request_export(doc_id)
                    filename, result_path, stats = self.service.download_and_save_file(task_id, path, doc_id, self.output_folder)
                    self.service.delete_document(doc_id)
                    self.file_completed.emit(filename, f"✅ Saved to {result_path}{stats}")
                except Exception as e:
                    self.file_completed.emit(path, f"❌ {str(e)}")
                    failed.append((path, str(e)))

            summary = f"✅ {len(successful)} translated, ❌ {len(failed)} failed."
            self.all_completed.emit(summary)
        except Exception as e:
            self.error_occurred.emit(str(e))

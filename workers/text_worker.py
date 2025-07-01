import os
import time
import json
import tempfile
from datetime import datetime
from PyQt5.QtCore import QThread, pyqtSignal


class TranslationWorker(QThread):
    progress_updated = pyqtSignal(str)
    translation_completed = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(
        self,
        api_client,
        source_text,
        project_id,
        source_lang,
        target_lang,
        max_retries,
        retry_delay,
    ):
        super().__init__()
        self.api_client = api_client
        self.source_text = source_text
        self.project_id = project_id
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def run(self):
        try:
            self.progress_updated.emit("Creating JSON document...")
            json_data = {"data": self.source_text}

            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False, encoding="utf-8"
            ) as temp_file:
                json.dump(json_data, temp_file, ensure_ascii=False, indent=2)
                temp_file_path = temp_file.name

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
            document_id = (
                doc_data[0].get("id")
                if isinstance(doc_data, list)
                else doc_data.get("id")
            )
            if not document_id:
                raise Exception("Failed to get document ID")

            self.progress_updated.emit(f"Document uploaded with ID: {document_id}")
            self.progress_updated.emit("Waiting for translation to complete...")
            attempt = 0

            while attempt < self.max_retries:
                time.sleep(self.retry_delay)
                attempt += 1

                try:
                    self.progress_updated.emit(
                        f"Checking translation status... Attempt {attempt}/{self.max_retries}"
                    )

                    # Перевіряємо статус документа
                    doc_status_response = self.api_client.document.get(document_id)

                    if doc_status_response.status_code == 200:
                        doc_status_data = doc_status_response.json()
                        pretranslated = doc_status_data.get(
                            "pretranslateCompleted", False
                        )

                        self.progress_updated.emit(
                            f"Translation in progress (Pre-translated = {pretranslated})"
                        )

                        if pretranslated:
                            self.progress_updated.emit("✅ Translation completed!")
                            break
                    else:
                        self.progress_updated.emit(
                            f"⚠️ Status check error: {doc_status_response.status_code}"
                        )

                except Exception as e:
                    self.progress_updated.emit(
                        f"Status check error: {str(e)} (attempt {attempt}/{self.max_retries})"
                    )

            # Перевіряємо чи переклад завершився
            if attempt >= self.max_retries:
                # Остання перевірка перед помилкою
                try:
                    doc_status_response = self.api_client.document.get(document_id)
                    if doc_status_response.status_code == 200:
                        doc_status_data = doc_status_response.json()
                        pretranslated = doc_status_data.get(
                            "pretranslateCompleted", False
                        )
                        if not pretranslated:
                            raise Exception(
                                f"Translation timeout: document not completed after {self.max_retries} attempts"
                            )
                except Exception as e:
                    raise Exception(
                        f"Translation timeout and status check failed: {str(e)}"
                    )

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

            for attempt in range(30):
                time.sleep(self.retry_delay)
                self.progress_updated.emit(
                    f"Downloading result... Attempt {attempt + 1}/30"
                )

                download_response = self.api_client.document.download_export_result(
                    task_id
                )
                if download_response.status_code == 200:
                    try:
                        result_json = json.loads(download_response.text)
                        translated_text = result_json.get(
                            "data", download_response.text
                        )
                    except json.JSONDecodeError:
                        translated_text = download_response.text

                    self.translation_completed.emit(translated_text)

                    try:
                        delete_response = self.api_client.document.delete(document_id)
                        if delete_response.status_code == 204:
                            self.progress_updated.emit(
                                "Document successfully deleted from project"
                            )
                    except Exception as delete_error:
                        self.progress_updated.emit(
                            f"Warning: error deleting document: {str(delete_error)}"
                        )

                    break
                elif download_response.status_code == 202:
                    continue
                else:
                    raise Exception(f"Download error: {download_response.status_code}")

            os.unlink(temp_file_path)

        except Exception as e:
            self.error_occurred.emit(f"Error: {str(e)}")

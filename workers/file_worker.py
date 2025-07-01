import os
import time
from pathlib import Path
from PyQt5.QtCore import QThread, pyqtSignal


class FileTranslationWorker(QThread):
    progress_updated = pyqtSignal(str)
    file_completed = pyqtSignal(str, str)
    all_completed = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(
        self,
        api_client,
        file_paths,
        project_id,
        output_folder=None,
        max_retries=5,
        retry_delay=60,
    ):
        super().__init__()
        self.api_client = api_client
        self.file_paths = file_paths
        self.project_id = project_id
        self.output_folder = output_folder
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def run(self):
        try:
            successful_files = []
            failed_files = []
            document_info = []
            self.progress_updated.emit("📤 Uploading files...")

            for file_path in self.file_paths:
                try:
                    filename = os.path.basename(file_path)
                    with open(file_path, "rb") as file:
                        files = {"file": (filename, file, "multipart/form-data")}
                        response = self.api_client.project.attach_document(
                            self.project_id, files
                        )

                    if response.status_code != 200:
                        raise Exception(response.text)

                    doc_data = response.json()
                    document_id = (
                        doc_data[0].get("id")
                        if isinstance(doc_data, list)
                        else doc_data.get("id")
                    )

                    document_info.append(
                        {
                            "filename": filename,
                            "file_path": file_path,
                            "document_id": document_id,
                        }
                    )
                    self.progress_updated.emit(
                        f"✅ Uploaded {filename} with ID {document_id}"
                    )

                except Exception as e:
                    failed_files.append((file_path, str(e)))
                    self.file_completed.emit(file_path, f"❌ {e}")

            for attempt in range(self.max_retries):
                done = 0
                for doc in document_info:
                    r = self.api_client.document.get(doc["document_id"])
                    if r.status_code == 200 and r.json().get("pretranslateCompleted"):
                        done += 1
                self.progress_updated.emit(
                    f"🕒 Waiting... {done}/{len(document_info)} ready"
                )
                if done == len(document_info):
                    break
                time.sleep(self.retry_delay)

            for doc in document_info:
                try:
                    export = self.api_client.document.request_export(
                        [doc["document_id"]], target_type="target"
                    )
                    task_id = export.json().get("id")

                    for _ in range(30):
                        time.sleep(self.retry_delay)
                        download = self.api_client.document.download_export_result(
                            task_id
                        )
                        if download.status_code == 200:
                            output_dir = self.output_folder or os.path.dirname(
                                doc["file_path"]
                            )
                            output_name = f"{Path(doc["filename"]).stem}_translated{Path(doc["filename"]).suffix}"
                            output_path = os.path.join(output_dir, output_name)
                            with open(output_path, "wb") as f:
                                f.write(download.content)
                            successful_files.append((doc["filename"], output_path))
                            self.file_completed.emit(
                                doc["filename"], f"✅ {output_path}"
                            )
                            self.api_client.document.delete(doc["document_id"])
                            break
                except Exception as e:
                    failed_files.append((doc["filename"], str(e)))
                    self.file_completed.emit(doc["filename"], f"❌ {e}")

            summary = f"✅ {len(successful_files)} translated, ❌ {len(failed_files)} failed.\n"
            summary += "\n".join([f"+ {f} → {p}" for f, p in successful_files])
            if failed_files:
                summary += "\n" + "\n".join([f"- {f}: {e}" for f, e in failed_files])

            self.all_completed.emit(summary)

        except Exception as e:
            self.error_occurred.emit(str(e))

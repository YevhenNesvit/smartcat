import os
import json
import time
import tempfile
from datetime import datetime
from pathlib import Path


class DocumentService:
    def __init__(self, api_client, project_id, max_retries, retry_delay):
        self.api_client = api_client
        self.project_id = project_id
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def upload_text_document(self, text):
        data = {"data": text}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as tmp:
            json.dump(data, tmp, ensure_ascii=False, indent=2)
            temp_path = tmp.name
        with open(temp_path, "rb") as f:
            files = {"file": (f"source_text_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", f, "multipart/form-data")}
            response = self.api_client.project.attach_document(self.project_id, files)
        if response.status_code != 200:
            raise Exception(f"Upload failed: {response.status_code} - {response.text}")
        doc_data = response.json()
        doc_id = doc_data[0]["id"] if isinstance(doc_data, list) else doc_data["id"]
        return doc_id, temp_path

    def upload_file_document(self, file_path):
        with open(file_path, "rb") as f:
            filename = os.path.basename(file_path)
            files = {"file": (filename, f, "multipart/form-data")}
            response = self.api_client.project.attach_document(self.project_id, files)
        if response.status_code != 200:
            raise Exception(f"Upload failed: {response.status_code} - {response.text}")
        doc_data = response.json()
        return doc_data[0]["id"] if isinstance(doc_data, list) else doc_data["id"]

    def wait_for_translation(self, doc_id, log_fn):
        for attempt in range(self.max_retries):
            time.sleep(self.retry_delay)
            status = self.api_client.document.get(doc_id)
            if status.status_code == 200:
                if status.json().get("pretranslateCompleted"):
                    return
            log_fn(f"Translation in progress (Pre-translated = {status.json().get("pretranslateCompleted")})")
        raise Exception("Translation did not complete in time")

    def wait_for_all(self, doc_ids, log_fn):
        for attempt in range(self.max_retries):
            done = sum(
                1 for doc_id in doc_ids
                if self.api_client.document.get(doc_id).json().get("pretranslateCompleted", False)
            )
            log_fn(f"🕒 Waiting... {done}/{len(doc_ids)} ready")
            if done == len(doc_ids):
                return
            time.sleep(self.retry_delay)

    def request_export(self, doc_id):
        response = self.api_client.document.request_export([doc_id], target_type="target")
        if response.status_code != 200:
            raise Exception(f"Export request failed: {response.status_code}")
        return response.json().get("id")

    def download_translation(self, task_id):
        for _ in range(30):
            time.sleep(self.retry_delay)
            r = self.api_client.document.download_export_result(task_id)
            if r.status_code == 200:
                try:
                    return json.loads(r.text).get("data", r.text)
                except json.JSONDecodeError:
                    return r.text
            elif r.status_code != 202:
                raise Exception(f"Download failed: {r.status_code}")
        raise Exception("Download timeout")

    def download_and_save_file(self, task_id, file_path, doc_id, output_folder=None):
        for _ in range(30):
            time.sleep(self.retry_delay)
            r = self.api_client.document.download_export_result(task_id)
            if r.status_code == 200:
                output_dir = output_folder or os.path.dirname(file_path)
                filename = os.path.basename(file_path)
                translated_name = f"{Path(filename).stem}_translated{Path(filename).suffix}"
                full_path = os.path.join(output_dir, translated_name)
                with open(full_path, "wb") as f:
                    f.write(r.content)
                stats = self.fetch_statistics(doc_id)
                return filename, full_path, stats
        raise Exception("Download failed")

    def fetch_statistics(self, doc_id):
        try:
            response = self.api_client.project.segment_confirmation_statistics(self.project_id, doc_id.split("_")[0])
            stats = response.json() if response.status_code == 200 else []
            mt = sum(e.get("wordcounts", {}).get("mt", 0) for e in stats if e.get("stageType") == "translation")
            tm = sum(sum(e.get("wordcounts", {}).get("tmMatches", {}).values()) for e in stats if e.get("stageType") == "translation")
            total = mt + tm
            if total == 0:
                return "\n📊 Statistics unavailable"
            return f"\n\n📊 Statistics:\n🔢 {total} words\n🧠 MT: {mt} ({mt/total:.2%})\n📚 TM: {tm} ({tm/total:.2%})\n"
        except Exception as e:
            return f"\n📊 Stats error: {str(e)}"

    def delete_document(self, doc_id):
        try:
            self.api_client.document.delete(doc_id)
        except Exception:
            pass

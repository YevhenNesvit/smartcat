import os
from dotenv import load_dotenv


def load_env_config():
    load_dotenv()
    return {
        "username": os.getenv("SMARTCAT_USERNAME", ""),
        "password": os.getenv("SMARTCAT_PASSWORD", ""),
        "server_url": os.getenv("SMARTCAT_SERVER", "https://smartcat.ai"),
        "project_id": os.getenv("SMARTCAT_PROJECT_ID", ""),
        "source_lang": os.getenv("SOURCE_LANGUAGE", "ru"),
        "target_lang": os.getenv("TARGET_LANGUAGE", "en"),
        "app_title": os.getenv("APP_TITLE", "SmartCAT Russian-English Translator"),
        "max_retries": int(os.getenv("MAX_RETRIES", "60")),
        "retry_delay": int(os.getenv("RETRY_DELAY", "5")),
        "files_max_retries": int(os.getenv("FILES_MAX_RETRIES", "5")),
        "files_retry_delay": int(os.getenv("FILES_RETRY_DELAY", "60")),
    }

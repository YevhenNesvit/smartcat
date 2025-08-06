# SmartCAT GUI Translator

🧠 A modern PyQt5 GUI app for text and file translation using the SmartCAT API based on the existing library: https://pypi.org/project/smartcat/ by v.zhyliaiev.

## 📁 Project Structure

```
smartcat_api_test/
├── api.py
├── main.py
├── main.spec
├── config.py
├── requirements.txt
├── gui/
│   ├── __init__.py
|   ├── base_tab.py
|   ├── file_tab.py
|   ├── main_window.py
|   ├── status_handler.py
|   ├── tab_factory.py
    └── text_tab.py
├── old_versions/
|   ├── smartcat_cli.py
    └── smatcat_gui.py
├── services/
|   ├── __init__.py
    └── document_service.py
├── workers/
│   ├── __init__.py
│   ├── text_worker.py
    └── file_worker.py
└── .env
```

## ⚙️ Requirements

- Python starting from 3.11
- SmartCAT API credentials
- `requirements.txt`

## 🔑 .env Configuration

Create a `.env` file based on `.env.example`:

## 🚀 Run Locally

```bash
pip install -r requirements.txt
python main.py
```

## 📸 Features
- Translate text directly in-app
- Translate multiple files asynchronously
- Status updates and progress bar
- Output management with optional folders
- Project configuration loaded from `.env`

---
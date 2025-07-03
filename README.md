# SmartCAT GUI Translator

🧠 A modern PyQt5 GUI app for text and file translation using the SmartCAT API based on the existing library: https://pypi.org/project/smartcat/ by v.zhyliaiev.

## 📁 Project Structure

```
smartcat_api_test/
├── main.py                  # Entry point
├── config.py               # Loads environment config from .env
├── requirements.txt        # Python dependencies
├── gui/
│   ├── __init__.py
│   └── main_window.py      # Full GUI logic and layout
    ├── file_tab.py
    └── text_tab.py
├── workers/
│   ├── __init__.py
│   ├── text_worker.py      # Async translation for plain text
│   └── file_worker.py      # Async translation for files
├── .env                    # Configuration (not tracked in Git)
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
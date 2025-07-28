from PyQt5.QtWidgets import (
    QMainWindow,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QPushButton,
    QLabel,
    QProgressBar,
    QGroupBox,
    QFormLayout,
    QTabWidget,
)
from config import load_env_config
from api import SmartCAT

# Імпортуємо рефакторингові вкладки та нові допоміжні класи
from gui.status_handler import StatusHandler
from gui.tab_factory import TabFactory


class SmartCATGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.api_client = None
        self.config = load_env_config()
        self.status_handler = StatusHandler(self)  # Створюємо StatusHandler
        self.tab_factory = TabFactory(self.api_client, self.config, self.status_handler)

        self.init_ui()
        self.auto_connect()

    def init_ui(self):
        self.setWindowTitle(self.config["app_title"])
        self.setGeometry(100, 100, 800, 700)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Панель конфігурації
        config_group = QGroupBox("Configuration (from.env file)")
        config_layout = QFormLayout()
        self.config_info = QLabel()
        self.update_config_display()
        config_layout.addRow(self.config_info)

        self.connect_btn = QPushButton("Connect to SmartCAT")
        self.connect_btn.clicked.connect(self.connect_to_api)
        config_layout.addRow(self.connect_btn)

        self.connection_status = QLabel("Status: Not connected")
        config_layout.addRow(self.connection_status)
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)

        # Вкладки перекладу
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Створюємо вкладки за допомогою фабрики
        self.text_translation_tab = self.tab_factory.create_text_tab(self)
        self.file_translation_tab = self.tab_factory.create_file_tab(self)

        self.tabs.addTab(self.text_translation_tab, "📝 Text Translation")
        self.tabs.addTab(self.file_translation_tab, "📁 File Translation")

        # Підключаємо сигнали від вкладок до StatusHandler
        # Ці сигнали можуть бути підключені до методів StatusHandler, які керують UI
        self.text_translation_tab.translation_started.connect(self.status_handler.show_progress)  # type: ignore
        self.text_translation_tab.translation_completed.connect(lambda: self.status_handler.hide_progress())  # type: ignore
        self.text_translation_tab.translation_error.connect(self.status_handler.show_critical)  # type: ignore

        self.file_translation_tab.translation_started.connect(self.status_handler.show_progress)  # type: ignore
        self.file_translation_tab.all_files_completed.connect(lambda: self.status_handler.hide_progress())  # type: ignore
        self.file_translation_tab.translation_error.connect(self.status_handler.show_critical)  # type: ignore

        # Прогрес-бар та статус-лейбл, якими керує StatusHandler
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Ready to work")
        self.status_label.setStyleSheet("QLabel { color: #666; font-style: italic; }")
        layout.addWidget(self.status_label)

        # Встановлюємо елементи UI для StatusHandler
        self.status_handler.set_ui_elements(self.progress_bar, self.status_label)

        # Підключаємо сигнали StatusHandler до кнопок перекладу на вкладках
        self.status_handler.translation_buttons_enabled.connect(self.text_translation_tab.enable_translation_button)
        self.status_handler.file_translation_button_enabled.connect(self.file_translation_tab.enable_translation_button)

        button_layout = QHBoxLayout()
        self.clear_btn = QPushButton("🗑️ Clear All")
        self.clear_btn.clicked.connect(self.clear_all)
        button_layout.addWidget(self.clear_btn)

        self.refresh_btn = QPushButton("🔄 Refresh Configuration")
        self.refresh_btn.clicked.connect(self.refresh_config)
        button_layout.addWidget(self.refresh_btn)
        layout.addLayout(button_layout)

    def update_config_display(self):
        self.config_info.setText(
            f"""
📡 Server: {self.config['server_url']}
🆔 Project ID: {self.config['project_id']}
🔤 Language pair: {self.config['source_lang'].upper()} → {self.config['target_lang'].upper()}
            """.strip()
        )

    def refresh_config(self):
        from dotenv import load_dotenv

        load_dotenv(override=True)
        self.config = load_env_config()
        self.update_config_display()
        self.connection_status.setText(
            "Status: Configuration updated. Reconnection required."
        )
        self.connection_status.setStyleSheet("color: orange")
        self.status_handler.enable_translation_buttons(False)
        self.status_handler.enable_file_translation_button(False)
        self.status_handler.show_info("Configuration", "Configuration reloaded from.env file!")

    def auto_connect(self):
        if (self.config["username"] and self.config["password"] and self.config["project_id"]):
            self.connect_to_api()

    def connect_to_api(self):
        try:
            self.connection_status.setText("Status: Connecting...")
            self.connection_status.setStyleSheet("color: orange")
            self.api_client = SmartCAT(
                self.config["username"],
                self.config["password"],
                self.config["server_url"],
            )
            # Оновлюємо api_client у фабриці та вкладках
            self.tab_factory.api_client = self.api_client  # type: ignore
            self.text_translation_tab.api_client = self.api_client
            self.file_translation_tab.api_client = self.api_client

            test_response = self.api_client.project.get(self.config["project_id"])
            if test_response.status_code == 200:
                project_name = test_response.json().get("name", "Unknown")
                self.connection_status.setText(
                    f"Status: ✅ Connected to project '{project_name}'"
                )
                self.connection_status.setStyleSheet("color: green")
                self.status_handler.enable_translation_buttons(True)
                self.status_handler.enable_file_translation_button(len(self.file_translation_tab.selected_files) > 0)
            else:
                raise Exception("Project not found or access denied")
        except Exception as e:
            self.connection_status.setText("Status: ❌ Connection error")
            self.connection_status.setStyleSheet("color: red")
            self.status_handler.show_critical(
                "Connection error", f"Failed to connect to API:\n{str(e)}"
            )

    def clear_all(self):
        self.text_translation_tab.text_input.clear()  # type: ignore
        self.text_translation_tab.result_output.clear()  # type: ignore
        self.file_translation_tab.file_results_output.clear()  # type: ignore
        self.file_translation_tab.selected_files.clear()
        self.file_translation_tab._update_files_list()  # Змінено на виклик внутрішнього методу
        self.file_translation_tab.output_folder_input.clear()  # type: ignore
        self.status_handler.update_status("Ready to work")
        self.status_handler.enable_file_translation_button(False)

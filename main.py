from PyQt5.QtWidgets import QApplication
import sys
from gui.main_window import SmartCATGUI


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = SmartCATGUI()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

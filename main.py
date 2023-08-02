import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from controller_new import Controller
import traceback


if __name__ == '__main__':
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)  # enable high DPI scaling
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)  # use high DPI icons
    app = QApplication([])

    try:
        window = Controller()
        window.gui.show()
        sys.exit(app.exec())
    except Exception as e:
        traceback.print_exc()
        print("Exception occurred:", str(e))

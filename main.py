import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from controller_new import Controller
import traceback
import faulthandler

faulthandler.enable()


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)  # enable high DPI scaling
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)  # use high DPI icons
    app = QApplication([])

    try:
        window = Controller()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        traceback.print_exc()
        print("Exception occurred:", str(e))


if __name__ == '__main__':
    main()

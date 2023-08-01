import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from controller import Controller

def excepthook(exc_type, exc_value, traceback):
    print("Uncaught exception occurred:", exc_value)

if __name__ == '__main__':
    sys.excepthook = excepthook

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)  # enable high DPI scaling
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)  # use high DPI icons
    app = QApplication([])

    try:
        window = Controller()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        print("Exception occurred:", str(e))

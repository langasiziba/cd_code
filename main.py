import pyvisa
from PySide6.QtWidgets import (QApplication, QMainWindow)
from debug import LogObject
from pem import PEM
from app import Ui_MainWindow
import queue
from mono import (Monoi, Monoii)

# from mono import Monoii

# from mfli import MFLI
# from mono import (monoi, monoii)

"""This following class controls the gui and all aspects of this code"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.initializeClicked.connect(self.do_on_initialize_click)
        self.ui.closeClicked.connect(self.do_on_close_click)
        self.ui.setpmtClicked.connect(self.do_on_initialize_click)


        self.pem_logger = LogObject(log_name='PEM')
        self.monoi_logger = LogObject(log_name='MONI')
        self.monoii_logger = LogObject(log_name='MONII')

        self.pem_logger.log_signal.connect(self.update_debug_log)
        self.monoi_logger.log_signal.connect(self.update_debug_log)
        self.monoii_logger.log_signal.connect(self.update_debug_log)

        self.pem = PEM()
        self.monoi = Monoi()
        self.monoii = Monoii()

        self.pem.log_signal.connect(self.pem_logger.log)
        self.monoi.log_signal.connect(self.monoi_logger.log)
        self.monoii.log_signal.connect(self.monoii_logger.log)

    def update_debug_log(self, log_message):
        self.ui.debug_input.insertPlainText(log_message + '\n')

    def do_on_initialize_click(self):
        # Create an instance of VisaDevice and call its initialize() method
        rm = pyvisa.ResourceManager()
        log_queue = queue.Queue()

        # Create instances of PEM and Mono and call their initialize() methods
        self.ui.pem_process.setText("Initializing")
        self.ui.monoi_process.setText("Initializing")
        self.ui.monoii_process.setText("Initializing")
        self.ui.mfli_process.setText("Initializing")

        self.pem.initialize(rm, log_queue)
        self.monoi.initialize(rm, log_queue)
        self.monoii.initialize(rm, log_queue)

        print("initializing tried")

    def do_on_close_click(self):
        pass


if __name__ == '__main__':
    import sys

    app = QApplication([])
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

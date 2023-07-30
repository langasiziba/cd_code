import queue

import pyvisa
from PyQt5.QtCore import Qt, QTimer, QThread
from PyQt5.QtWidgets import QApplication, QMainWindow, QDialog, QVBoxLayout, QLabel, QPushButton
import time

from debug import LogObject
from gui import Ui_MainWindow
from mfli import MFLI

from pem import PEM

import sys
import time
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QDialog, QLabel, QPushButton
from PyQt5.QtCore import QTimer, Qt


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

        mfli = MFLI(ID="dev7024", logname="mfli_log", log_queue=log_queue)

        # Connect to the MFLI device
        connected = mfli.connect()
        pmt_data = mfli.get_pmt_data()

        if connected:
            # Perform further operations with the MFLI device
            pmt_spectra_data = mfli.get_pmt_data()


        # Print the log messages from the MFLI instance
        while not log_queue.empty():
            print(log_queue.get())

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
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)  # enable high DPI scaling
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)  # use high DPI icons
    app = QApplication([])
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

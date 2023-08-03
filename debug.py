from queue import Queue  # Import the Queue class from the queue module
from datetime import datetime  # Import the datetime class from the datetime module
import time
import pyvisa
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QMessageBox


class ECommError(Exception):
    pass


"""This part of the code controls is the error log. Through the following program we are able to display an error
log using a central box and in the debug log that displays the error in the format [Error type][Date, Time][Error] This class 
will also be used to control error handling for the devices in the system"""


class LogObject(QObject):
    log_signal = pyqtSignal(str)

    def __init__(self, log_name=''):
        super().__init__()
        self.log_name = log_name
        self.initialized = False
        self.log_queue = Queue()
        self.error_emitted = False

    def log(self, s: str, error: bool = False, no_id: bool = False):
        timestamp = datetime.now().strftime("%H:%M:%S")
        ss = '[{}] {}'.format(timestamp, s)
        if not no_id:
            ss = '[{}] {}'.format(self.log_name, ss)

        if error or 'error' in ss.lower():
            self.log_queue.put(ss)
            if not no_id:
                self.show_error_box(ss)
                self.log_signal.emit(ss)
        elif not self.log_queue.full():
            self.log_queue.put(ss)
            self.error_emitted = False
        # Always emit the signal regardless of whether an error occurred or not
        self.log_signal.emit(ss)

    def log_ask(self, q: str):
        self.log('<< {}'.format(q))

    def log_answer(self, s: str):
        self.log('>> {}'.format(s))

    def show_error_box(self, s: str):
        error_box = QMessageBox()  # Create a QMessageBox instance
        error_box.setWindowTitle('Error')
        error_box.setText(s)
        error_box.setIcon(QMessageBox.Icon.Critical)
        error_box.addButton(QMessageBox.StandardButton.Ok)
        error_box.exec()

    def close(self):
        self.log('Closing logger...')
        self.initialized = False
        self.log('Logger closed.')


class VisaDevice(LogObject):
    def log_query(self, q: str) -> str:
        self.log_ask(q)
        s = self.inst.query(q)
        self.log_answer(s)
        return s

    def debug_query(self, q: str) -> None:
        self.inst.write(q)
        self.log_ask(q)
        start_time = time.time()
        while time.time() - start_time < self.inst.timeout / 1000:
            try:
                self.log_answer(self.inst.read_bytes(1))
            except pyvisa.VisaIOError:
                self.log("Debug query timeout.")
                break

    def close(self) -> None:
        self.log('Closing connection...')
        self.inst.close()
        self.log('Connection closed.')
        self.initialized = False

import pyvisa
from PySide6.QtWidgets import (QApplication, QMainWindow)
from PyQt6 import QtWidgets
from debug import LogObject
from pem import PEM
from app import Ui_MainWindow, ButtonHandler
import sys

# from mfli import MFLI
# from mono import (monoi, monoii)

"""This following class controls the gui and all aspects of this code"""


class Control(LogObject):
    pass


"""# Main Thread
if __name__ == '__main__':
    import sys

    app = QtWidgets.QApplication(sys.argv)

    def handle_offset_click(offset_value):
        print(f"Offset button clicked in the GUI thread with value: {offset_value}")

    # Create the GUI instance
    gui = MyGUI()

    # Connect the offsetClicked signal to the handle_offset_click function in the main thread
    gui.offsetClicked.connect(handle_offset_click)

    # Show the GUI
    gui.show()

    # Start the event loop
    sys.exit(app.exec())
    
            # Connect signals from the button handler to the respective slots
        app.initializeClicked.connect(do_on_initialize_click)
        self.buttonHandler.closeClicked.connect(self.do_on_close_click)
        self.buttonHandler.gainClicked.connect(self.do_on_gain_click)
        self.buttonHandler.offsetClicked.connect(self.do_on_offset_click)
        self.buttonHandler.rangeClicked.connect(self.do_on_range_click)
        self.buttonHandler.stepsizeClicked.connect(self.do_on_stepsize_click)
        self.buttonHandler.wlmaxClicked.connect(self.do_on_wl_max_click)
        self.buttonHandler.dwelltimeClicked.connect(self.do_on_dwelltime_click)
        self.buttonHandler.wlminClicked.connect(self.do_on_wl_min_click)
        self.buttonHandler.filenameClicked.connect(self.do_on_filename_click)
        self.buttonHandler.detcorrectionsClicked.connect(self.do_on_detcorrections_click)
        self.buttonHandler.acClicked.connect(self.do_on_ac_click)
        self.buttonHandler.repetitionsClicked.connect(self.do_on_repetitions_click)
        self.buttonHandler.samplecClicked.connect(self.do_on_samplec_click)
        self.buttonHandler.dcClicked.connect(self.do__on_dc_click)
        self.buttonHandler.startbuttonClicked.connect(self.do_on_start_button_click)
        self.buttonHandler.stopbuttonClicked.connect(self.do_on_stop_button_click)
        self.buttonHandler.savecommentsClicked.connect(self.do_on_save_comments_click)
        self.buttonHandler.pathClicked.connect(self.do_on_path_click)

    def do_on_initialize_click(self):
        pass

    def do_on_close_click(self):
        pass

    def do_on_gain_click(self):
        pass

    def do_on_offset_click(self):
        pass

    def do_on_range_click(self):
        pass

    def do_on_stepsize_click(self):
        pass

    def do_on_dwelltime_click(self):
        pass

    def do_on_wl_min_click(self):
        pass

    def do_on_wl_max_click(self):
        pass

    def do_on_filename_click(self):
        pass

    def do_on_detcorrections_click(self):
        pass

    def do_on_ac_click(self):
        pass

    def do_on_initialize_click(self):
        pass

    def do_on_initialize_click(self):
        pass

    def do_on_initialize_click(self):
        pass

    def do_on_initialize_click(self):
        pass
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()

        self.ui.setupUi(self)


if __name__ == '__main__':
    app = QApplication([])

    def do_on_initialize_click():
        print("initialize clicked")

    bh = ButtonHandler()

    bh.initializeClicked.connect(do_on_initialize_click)

    window = MainWindow()

    window.show()
    app.exec()

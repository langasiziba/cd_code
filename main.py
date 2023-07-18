import pyvisa
from PySide6.QtWidgets import QApplication, QMainWindow, QGraphicsView, QGraphicsScene, QVBoxLayout, QLabel, QWidget
from PySide6.QtCore import Qt
from app import Ui_MainWindow
from debug import LogObject
from pem import PEM
from mono import Monoi, Monoii
from mfli import MFLI
import queue
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PySide6.QtWidgets import QGraphicsProxyWidget

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

        # Create a Figure and an Axes for plotting the PMT spectra
        self.pmt_spectra_figure = plt.figure()
        self.pmt_spectra_axes = self.pmt_spectra_figure.add_subplot(111)
        self.pmt_spectra_canvas = FigureCanvas(self.pmt_spectra_figure)

        # Create a QWidget to hold the FigureCanvas
        self.pmt_spectra_widget = QWidget()
        self.pmt_spectra_layout = QVBoxLayout()
        self.pmt_spectra_widget.setLayout(self.pmt_spectra_layout)

        # Create a QGraphicsProxyWidget to hold the QWidget
        self.pmt_spectra_proxy = QGraphicsProxyWidget()
        self.pmt_spectra_proxy.setWidget(self.pmt_spectra_widget)

        # Create a QGraphicsScene and set it as the scene for pmt_spectra_view
        self.pmt_spectra_scene = QGraphicsScene()
        self.ui.pmt_spectra_view.setScene(self.pmt_spectra_scene)

        # Add the QGraphicsProxyWidget to the scene
        self.pmt_spectra_scene.addItem(self.pmt_spectra_proxy)

    def update_pmt_spectra(self, data):
        # Clear the previous data
        self.pmt_spectra_axes.clear()

        # Update the PMT spectra data
        x_values = [x for x, _ in data]
        y_values = [y for _, y in data]
        self.pmt_spectra_axes.plot(x_values, y_values)

        # Set labels and titles if needed
        self.pmt_spectra_axes.set_xlabel('X-axis label')
        self.pmt_spectra_axes.set_ylabel('Y-axis label')
        self.pmt_spectra_axes.set_title('PMT Spectra')

        # Redraw the plot
        self.pmt_spectra_canvas.draw()

    def update_debug_log(self, log_message):
        self.ui.debug_input.insertPlainText(log_message + '\n')

    def do_on_initialize_click(self):
        # Create an instance of VisaDevice and call its initialize() method
        rm = pyvisa.ResourceManager()
        log_queue = queue.Queue()

        mfli = MFLI(ID="dev7024", logname="mfli_log", log_queue=log_queue)

        # Connect to the MFLI device
        connected = mfli.connect()

        if connected:
            # Perform further operations with the MFLI device
            pmt_spectra_data = mfli.get_pmt_spectra()

            # Update the PMT spectra in the GUI
            self.update_pmt_spectra(pmt_spectra_data)

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

    app = QApplication([])
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

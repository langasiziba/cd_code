import queue

from PyQt5.QtCore import (QCoreApplication, QMetaObject, QRect,
                          Qt, pyqtSignal, pyqtSlot, QObject, QTimer)
from PyQt5.QtGui import (QCursor, QFont, QDoubleValidator)
from PyQt5.QtWidgets import (QGroupBox, QLabel,
                             QLineEdit, QPlainTextEdit, QProgressBar,
                             QSizePolicy, QStatusBar, QWidget, QVBoxLayout, QComboBox, QMessageBox)
from PyQt5.QtWidgets import QPushButton
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

import controller
from mfli import MFLI
from debug import LogObject




class MyProgressBar(QProgressBar):
    def __init__(self, parent=None):
        super(MyProgressBar, self).__init__(parent)
        self.time_left = 0
        self.unit = 's'

    def text(self):
        return f'ca. {self.time_left:.1f} {self.unit}'

class Ui_MainWindow(QObject):
    setpmtClicked = pyqtSignal()
    initializeClicked = pyqtSignal()
    closeClicked = pyqtSignal()
    gainClicked = pyqtSignal()
    offsetClicked = pyqtSignal()
    rangeClicked = pyqtSignal()
    startbuttonClicked = pyqtSignal()
    stopbuttonClicked = pyqtSignal()
    savecommentsClicked = pyqtSignal()
    setwavelengthClicked = pyqtSignal()
    rangeChosen = pyqtSignal()
    calibrateClicked = pyqtSignal()
    values_changed = pyqtSignal(int, float, float, float, float, str, str, str, str, int)
    update_max_voltage_signal = pyqtSignal(float)
    update_avg_voltage_signal = pyqtSignal(float)
    handle_range_limit_reached_signal = pyqtSignal()
    handle_pmt_limit_reached_signal = pyqtSignal()
    closing = pyqtSignal()


    def __init__(self):
        super().__init__()
        self.oscilloscope_thread = None
        log_queue = queue.Queue()
        self.mfli = MFLI(ID="dev7024", logname="mfli_log", log_queue=log_queue)
        self.controller = controller.Controller()
        self.PhaseOffsetCalibrationDialog = controller.PhaseOffsetCalibrationDialog(self.controller)
        self.edits_map = {
            "edt_det_corr": self.edt_det_corr,
            "edt_debug_log": self.debug_input
        }

        self.input_mapping = {
            "edt_pmt": self.pmt_input,
            "edt_gain": self.gain_input,
        }
        # To call on_closing when the window is closing
        self.closeEvent = self.on_closing
        self.close_button.clicked.connect(self.close)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plots)
        self.timer.start(1000)  # update every 1000 ms (1 second)
        self.myLogger = LogObject('MyLogger')


    def set_text(self, edt, text):
        # Find the QLineEdit instance by name
        edit = self.edits_map.get(edt)
        if edit is not None:
            edit.setText(text)
        else:
            print(f"No QLineEdit named {edt} found.")

    def closeEvent(self, event):
        self.controller.on_closing()
        event.accept()

    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1480, 886)
        font = QFont()
        font.setFamily(u"Segoe UI Historic")
        MainWindow.setFont(font)
        MainWindow.setAutoFillBackground(True)
        MainWindow.setStyleSheet(u"background color: rgb(230, 230, 230)")
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.devicesetup_group = QGroupBox(self.centralwidget)
        self.devicesetup_group.setObjectName(u"devicesetup_group")
        self.devicesetup_group.setGeometry(QRect(10, 10, 371, 241))
        font1 = QFont()
        font1.setFamily(u"Segoe UI Semibold")
        font1.setPointSize(14)
        self.devicesetup_group.setFont(font1)
        self.devicesetup_group.setAutoFillBackground(False)
        self.devicesetup_group.setStyleSheet(u"background-color: rgb(225, 195, 255)")
        self.initialize_button = QPushButton(self.devicesetup_group)
        self.initialize_button.setObjectName(u"initialize_button")
        self.initialize_button.setGeometry(QRect(10, 40, 75, 24))
        font2 = QFont()
        font2.setFamily(u"Segoe UI Historic")
        font2.setPointSize(9)
        self.initialize_button.setFont(font2)
        self.initialize_button.setAutoFillBackground(False)
        self.initialize_button.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.close_button = QPushButton(self.devicesetup_group)
        self.close_button.setObjectName(u"close_button")
        self.close_button.setGeometry(QRect(10, 70, 75, 24))
        self.close_button.setFont(font2)
        self.close_button.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.close_button.setEnabled(False)
        self.label = QLabel(self.devicesetup_group)
        self.label.setObjectName(u"label")
        self.label.setGeometry(QRect(10, 100, 49, 16))
        self.label.setFont(font2)
        self.label_2 = QLabel(self.devicesetup_group)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setGeometry(QRect(10, 130, 49, 16))
        self.label_2.setFont(font2)
        self.label_3 = QLabel(self.devicesetup_group)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setGeometry(QRect(10, 160, 49, 16))
        self.label_3.setFont(font2)
        self.label_4 = QLabel(self.devicesetup_group)
        self.label_4.setObjectName(u"label_4")
        self.label_4.setGeometry(QRect(10, 190, 49, 16))
        self.label_4.setFont(font2)
        self.pem_process = QLabel(self.devicesetup_group)
        self.pem_process.setObjectName(u"pem_process")
        self.pem_process.setGeometry(QRect(70, 100, 91, 16))
        self.pem_process.setFont(font2)
        self.monoi_process = QLabel(self.devicesetup_group)
        self.monoi_process.setObjectName(u"monoi_process")
        self.monoi_process.setGeometry(QRect(70, 130, 101, 20))
        self.monoi_process.setFont(font2)
        self.monoii_process = QLabel(self.devicesetup_group)
        self.monoii_process.setObjectName(u"monoii_process")
        self.monoii_process.setGeometry(QRect(70, 160, 111, 16))
        self.monoii_process.setFont(font2)
        self.mfli_process = QLabel(self.devicesetup_group)
        self.mfli_process.setObjectName(u"mfli_process")
        self.mfli_process.setGeometry(QRect(70, 190, 91, 16))
        self.mfli_process.setFont(font2)
        self.signaltuning_group = QGroupBox(self.centralwidget)
        self.signaltuning_group.setObjectName(u"signaltuning_group")
        self.signaltuning_group.setGeometry(QRect(10, 260, 371, 601))
        self.signaltuning_group.setFont(font1)
        self.signaltuning_group.setAutoFillBackground(False)
        self.signaltuning_group.setStyleSheet(u"background-color: rgb(195, 195, 255)")
        self.signaltuning_group.setEnabled(False)

        # pmt spectra
        # Create a Figure for your plot
        # Initialize the FigureCanvas
        self.fig = Figure(figsize=(6, 5), dpi=50)
        self.ax = self.fig.add_subplot(111)
        # Create a new FigureCanvas
        self.canvas = FigureCanvas(self.fig)
        self.pmt_spectra_view = QWidget(self.signaltuning_group)
        self.pmt_spectra_view.setObjectName(u"pmt_spectra_view")
        self.pmt_spectra_view.setGeometry(15, 30, 321, 191)
        self.pmt_spectra_view.setStyleSheet(u"background-color: rgb(255,255,255)")
        canvas_layout = QVBoxLayout()
        canvas_layout.addWidget(self.canvas)
        self.pmt_spectra_view.setLayout(canvas_layout)

        self.label_9 = QLabel(self.signaltuning_group)
        self.label_9.setObjectName(u"label_9")
        self.label_9.setGeometry(QRect(10, 220, 101, 16))
        font3 = QFont()
        font3.setFamily(u"Segoe UI")
        font3.setPointSize(9)
        self.label_9.setFont(font3)
        self.label_10 = QLabel(self.signaltuning_group)
        self.label_10.setObjectName(u"label_10")
        self.label_10.setGeometry(QRect(10, 250, 91, 16))
        self.label_10.setFont(font3)
        self.label_11 = QLabel(self.signaltuning_group)
        self.label_11.setObjectName(u"label_11")
        self.label_11.setGeometry(QRect(10, 290, 81, 16))
        self.label_11.setFont(font3)
        self.label_12 = QLabel(self.signaltuning_group)
        self.label_12.setObjectName(u"label_12")
        self.label_12.setGeometry(QRect(10, 330, 91, 16))
        self.label_12.setFont(font3)
        self.label_13 = QLabel(self.signaltuning_group)
        self.label_13.setObjectName(u"label_13")
        self.label_13.setGeometry(QRect(10, 370, 91, 16))
        self.label_13.setFont(font3)
        self.label_15 = QLabel(self.signaltuning_group)
        self.label_15.setObjectName(u"label_15")
        self.label_15.setGeometry(QRect(10, 410, 81, 21))
        self.label_15.setFont(font3)
        self.peak_voltagetext = QLabel(self.signaltuning_group)
        self.peak_voltagetext.setObjectName(u"peak_voltagetext")
        self.peak_voltagetext.setGeometry(QRect(110, 220, 91, 16))
        self.peak_voltagetext.setFont(font3)
        self.avg_voltagetext = QLabel(self.signaltuning_group)
        self.avg_voltagetext.setObjectName(u"avg_voltagetext")
        self.avg_voltagetext.setGeometry(QRect(110, 250, 81, 16))
        self.avg_voltagetext.setFont(font3)
        self.set_pmt = QPushButton(self.signaltuning_group)
        self.set_pmt.setObjectName(u"set_pmt")
        self.set_pmt.setGeometry(QRect(250, 290, 51, 24))
        font4 = QFont()
        font4.setFamily(u"Segoe UI Semibold")
        font4.setPointSize(9)
        self.set_pmt.setFont(font4)
        self.set_pmt.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.label_26 = QLabel(self.signaltuning_group)
        self.label_26.setObjectName(u"label_26")
        self.label_26.setGeometry(QRect(10, 450, 81, 21))
        self.label_26.setFont(font3)
        self.set_gain = QPushButton(self.signaltuning_group)
        self.set_gain.setObjectName(u"set_gain")
        self.set_gain.setGeometry(QRect(250, 330, 51, 24))
        self.set_gain.setFont(font4)
        self.set_gain.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.set_wavelength = QPushButton(self.signaltuning_group)
        self.set_wavelength.setObjectName(u"set_wavelength")
        self.set_wavelength.setGeometry(QRect(250, 370, 51, 24))
        self.set_wavelength.setFont(font4)
        self.set_wavelength.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.pmt_input = QLineEdit(self.signaltuning_group)
        self.pmt_input.setObjectName(u"pmt_input")
        self.pmt_input.setGeometry(QRect(110, 290, 113, 21))
        self.pmt_input.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.cbx_range = QComboBox(self.signaltuning_group)
        self.cbx_range.setObjectName(u"cbx_range")
        self.cbx_range.setGeometry(QRect(110, 410, 113, 21))
        # add items to the combo box
        self.cbx_range.addItem("0.001")
        self.cbx_range.addItem("0.003")
        self.cbx_range.addItem("1.0")
        self.cbx_range.addItem("3.0")

        self.gain_input = QLineEdit(self.signaltuning_group)
        self.gain_input.setObjectName(u"gain_input")
        self.gain_input.setGeometry(QRect(110, 330, 113, 21))
        self.gain_input.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.edt_excWL = QLineEdit(self.signaltuning_group)
        self.edt_excWL.setObjectName(u"edt_excWL")
        self.edt_excWL.setGeometry(QRect(110, 370, 113, 21))
        self.edt_excWL.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.set_range = QPushButton(self.signaltuning_group)
        self.set_range.setObjectName(u"set_range")
        self.set_range.setGeometry(QRect(250, 410, 51, 24))
        self.set_range.setFont(font4)
        self.set_range.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.edt_phaseoffset = QLineEdit(self.signaltuning_group)
        self.edt_phaseoffset.setObjectName(u"edt_phaseoffset")
        self.edt_phaseoffset.setGeometry(QRect(110, 450, 113, 21))
        self.edt_phaseoffset.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.set_offset = QPushButton(self.signaltuning_group)
        self.set_offset.setObjectName(u"set_offset")
        self.set_offset.setGeometry(QRect(250, 450, 51, 24))
        self.set_offset.setFont(font4)
        self.set_offset.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.calibrate = QPushButton(self.signaltuning_group)
        self.calibrate.setObjectName(u"calibrate")
        self.calibrate.setEnabled(True)
        self.calibrate.setGeometry(QRect(110, 490, 191, 24))
        self.calibrate.setFont(font4)
        self.calibrate.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.graphicsView.raise_()
        self.label_9.raise_()
        self.label_10.raise_()
        self.label_11.raise_()
        self.label_12.raise_()
        self.label_13.raise_()
        self.label_15.raise_()
        self.peak_voltagetext.raise_()
        self.avg_voltagetext.raise_()
        self.set_pmt.raise_()
        self.label_26.raise_()
        self.set_gain.raise_()
        self.set_wavelength.raise_()
        self.cbx_range.raise_()
        self.gain_input.raise_()
        self.edt_excWL.raise_()
        self.set_range.raise_()
        self.pmt_input.raise_()
        self.edt_phaseoffset.raise_()
        self.set_offset.raise_()
        self.calibrate.raise_()
        self.spectrasetup_group = QGroupBox(self.centralwidget)
        self.spectrasetup_group.setObjectName(u"spectrasetup_group")
        self.spectrasetup_group.setGeometry(QRect(390, 10, 381, 851))
        self.spectrasetup_group.setFont(font1)
        self.spectrasetup_group.setAutoFillBackground(False)
        self.spectrasetup_group.setStyleSheet(u"background-color: rgb(195, 235, 255)")
        self.spectrasetup_group.setEnabled(False)

        self.var_pem_off = QCheckBox(self.spectrasetup_group)
        self.var_pem_off.setObjectName(u"var_pem_off")
        self.var_pem_off.setGeometry(QRect(140,460,121,16))

        self.edt_start = QLineEdit(self.spectrasetup_group)
        self.edt_start.setObjectName(u"edt_start")
        self.edt_start.setGeometry(QRect(140, 60, 155, 21))
        self.edt_start.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.label_14 = QLabel(self.spectrasetup_group)
        self.label_14.setObjectName(u"label_14")
        self.label_14.setGeometry(QRect(20, 140, 111, 16))
        self.label_14.setFont(font3)
        self.edt_dwell = QLineEdit(self.spectrasetup_group)
        self.edt_dwell.setObjectName(u"edt_dwell")
        self.edt_dwell.setGeometry(QRect(140, 180, 155, 21))
        self.edt_dwell.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.edt_end = QLineEdit(self.spectrasetup_group)
        self.edt_end.setObjectName(u"edt_end")
        self.edt_end.setGeometry(QRect(140, 100, 155, 21))
        self.edt_end.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.edt_step = QLineEdit(self.spectrasetup_group)
        self.edt_step.setObjectName(u"edt_step")
        self.edt_step.setGeometry(QRect(140, 140, 155, 21))
        self.edt_step.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.label_18 = QLabel(self.spectrasetup_group)
        self.label_18.setObjectName(u"label_18")
        self.label_18.setGeometry(QRect(20, 180, 81, 16))
        self.label_18.setFont(font3)
        self.label_19 = QLabel(self.spectrasetup_group)
        self.label_19.setObjectName(u"label_19")
        self.label_19.setGeometry(QRect(20, 60, 101, 16))
        self.label_19.setFont(font3)
        self.label_20 = QLabel(self.spectrasetup_group)
        self.label_20.setObjectName(u"label_20")
        self.label_20.setGeometry(QRect(20, 100, 91, 16))
        self.label_20.setFont(font3)
        self.edt_rep = QLineEdit(self.spectrasetup_group)
        self.edt_rep.setObjectName(u"edt_rep")
        self.edt_rep.setGeometry(QRect(140, 220, 155, 21))
        self.edt_rep.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.label_21 = QLabel(self.spectrasetup_group)
        self.label_21.setObjectName(u"label_21")
        self.label_21.setGeometry(QRect(20, 300, 81, 16))
        self.label_21.setFont(font3)
        self.edt_ac_blank = QLineEdit(self.spectrasetup_group)
        self.edt_ac_blank.setObjectName(u"edt_ac_blank")
        self.edt_ac_blank.setGeometry(QRect(140, 340, 155, 21))
        self.edt_ac_blank.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.edt_det_corr = QLineEdit(self.spectrasetup_group)
        self.edt_det_corr.setObjectName(u"edt_det_corr")
        self.edt_det_corr.setGeometry(QRect(140, 260, 155, 21))
        self.edt_det_corr.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.edt_filename = QLineEdit(self.spectrasetup_group)
        self.edt_filename.setObjectName(u"edt_filename")
        self.edt_filename.setGeometry(QRect(140, 300, 155, 21))
        self.edt_filename.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.label_22 = QLabel(self.spectrasetup_group)
        self.label_22.setObjectName(u"label_22")
        self.label_22.setGeometry(QRect(20, 340, 101, 16))
        self.label_22.setFont(font3)
        self.label_23 = QLabel(self.spectrasetup_group)
        self.label_23.setObjectName(u"label_23")
        self.label_23.setGeometry(QRect(20, 220, 91, 16))
        self.label_23.setFont(font3)
        self.label_24 = QLabel(self.spectrasetup_group)
        self.label_24.setObjectName(u"label_24")
        self.label_24.setGeometry(QRect(20, 260, 111, 16))
        self.label_24.setFont(font3)
        self.edt_dc_blank = QLineEdit(self.spectrasetup_group)
        self.edt_dc_blank.setObjectName(u"edt_dc_blank")
        self.edt_dc_blank.setGeometry(QRect(140, 380, 155, 21))
        self.edt_dc_blank.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.label_25 = QLabel(self.spectrasetup_group)
        self.label_25.setObjectName(u"label_25")
        self.label_25.setGeometry(QRect(20, 500, 81, 16))
        self.label_25.setFont(font3)
        self.samplec_input = QLineEdit(self.spectrasetup_group)
        self.samplec_input.setObjectName(u"samplec_input")
        self.samplec_input.setGeometry(QRect(140, 420, 155, 21))
        self.samplec_input.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.label_27 = QLabel(self.spectrasetup_group)
        self.label_27.setObjectName(u"label_27")
        self.label_27.setGeometry(QRect(20, 380, 101, 16))
        self.label_27.setFont(font3)
        self.label_28 = QLabel(self.spectrasetup_group)
        self.label_28.setObjectName(u"label_28")
        self.label_28.setGeometry(QRect(20, 420, 121, 16))
        self.label_28.setFont(font3)
        self.edt_comment = QPlainTextEdit(self.spectrasetup_group)
        self.edt_comment.setObjectName(u"edt_comment")
        self.edt_comment.setGeometry(QRect(140, 500, 191, 91))
        self.edt_comment.setFont(font2)
        self.edt_comment.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.start_button = QPushButton(self.spectrasetup_group)
        self.start_button.setObjectName(u"start_button")
        self.start_button.setGeometry(QRect(100, 720, 81, 31))
        font5 = QFont()
        font5.setFamily(u"Segoe UI Semibold")
        font5.setPointSize(11)
        self.start_button.setFont(font5)
        self.start_button.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.stop_button = QPushButton(self.spectrasetup_group)
        self.stop_button.setObjectName(u"stop_button")
        self.stop_button.setGeometry(QRect(190, 720, 81, 31))
        self.stop_button.setFont(font5)
        self.stop_button.setStyleSheet(u"background-color: rgb(255, 99, 99)")
        self.save_comments = QPushButton(self.spectrasetup_group)
        self.save_comments.setObjectName(u"save_comments")
        self.save_comments.setGeometry(QRect(140, 600, 51, 21))
        self.save_comments.setFont(font2)
        self.save_comments.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.progressBar = MyProgressBar(self.spectrasetup_group)
        self.progressBar.setObjectName(u"progressBar")
        self.progressBar.setGeometry(QRect(80, 780, 251, 23))
        self.progressBar.setFont(font5)
        self.progressBar.setValue(0)
        self.label_33 = QLabel(self.spectrasetup_group)
        self.label_33.setObjectName(u"label_33")
        self.label_33.setGeometry(QRect(140, 640, 71, 16))
        self.label_33.setFont(font2)
        self.set_path = QPushButton(self.spectrasetup_group)
        self.set_path.setObjectName(u"set_path")
        self.set_path.setGeometry(QRect(280, 460, 51, 24))
        self.set_path.setFont(font4)
        self.set_path.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.path_input = QLineEdit(self.spectrasetup_group)
        self.path_input.setObjectName(u"path_input")
        self.path_input.setGeometry(QRect(140, 460, 155, 21))
        self.path_input.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.label_34 = QLabel(self.spectrasetup_group)
        self.label_34.setObjectName(u"label_34")
        self.label_34.setGeometry(QRect(20, 460, 121, 16))
        self.label_34.setFont(font3)
        self.spectra_group = QGroupBox(self.centralwidget)
        self.spectra_group.setObjectName(u"spectra_group")
        self.spectra_group.setGeometry(QRect(780, 10, 691, 521))
        self.spectra_group.setFont(font1)
        self.spectra_group.setAutoFillBackground(False)
        self.spectra_group.setStyleSheet(u"background-color: rgb(195, 255, 255)")
        self.spectra_group.setEnabled(False)
        self.graphicsView_2 = self.setup_matplotlib_widget(self.spectra_group, QRect(20, 60, 321, 201), 'CDgraph')
        self.graphicsView_3 = self.setup_matplotlib_widget(self.spectra_group, QRect(360, 60, 321, 201), 'g_absgraph')
        self.graphicsView_4 = self.setup_matplotlib_widget(self.spectra_group, QRect(20, 290, 321, 201),
                                                           'molar_ellipsgraph')
        self.graphicsView_5 = self.setup_matplotlib_widget(self.spectra_group, QRect(360, 290, 321, 201), 'LDgraph')
        self.label_29 = QLabel(self.spectra_group)
        self.label_29.setObjectName(u"label_29")
        self.label_29.setGeometry(QRect(20, 270, 49, 16))
        self.label_29.setFont(font4)
        self.label_30 = QLabel(self.spectra_group)
        self.label_30.setObjectName(u"label_30")
        self.label_30.setGeometry(QRect(360, 270, 49, 16))
        self.label_30.setFont(font4)
        self.label_31 = QLabel(self.spectra_group)
        self.label_31.setObjectName(u"label_31")
        self.label_31.setGeometry(QRect(30, 40, 49, 16))
        self.label_31.setFont(font4)
        self.label_32 = QLabel(self.spectra_group)
        self.label_32.setObjectName(u"label_32")
        self.label_32.setGeometry(QRect(360, 40, 49, 16))
        self.label_32.setFont(font4)
        self.debug_group = QGroupBox(self.centralwidget)
        self.debug_group.setObjectName(u"debug_group")
        self.debug_group.setGeometry(QRect(780, 540, 691, 321))
        self.debug_group.setFont(font1)
        self.debug_group.setAutoFillBackground(True)
        self.debug_input = QPlainTextEdit(self.debug_group)
        self.debug_input.setObjectName(u"debug_input")
        self.debug_input.setGeometry(QRect(10, 40, 661, 261))
        sizePolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.debug_input.sizePolicy().hasHeightForWidth())
        self.debug_input.setSizePolicy(sizePolicy)
        self.debug_input.setFont(font2)
        self.debug_input.viewport().setProperty("cursor", QCursor(Qt.IBeamCursor))
        MainWindow.setCentralWidget(self.centralwidget)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)

        # Create a validator to accept only floating-point values
        validator0 = QDoubleValidator()
        validator0.setDecimals(0)

        validator1 = QDoubleValidator()
        validator0.setDecimals(1)

        validator2 = QDoubleValidator()
        validator0.setDecimals(2)

        self.edt_start.setValidator(validator2)
        self.edt_end.setValidator(validator2)
        self.edt_dwell.setValidator(validator1)
        self.edt_step.setValidator(validator0)
        self.gain_input.setValidator(validator2)
        self.edt_phaseoffset.setValidator(validator2)
        self.cbx_range.setValidator(validator2)
        self.edt_rep.setValidator(validator0)
        self.samplec_input.setValidator(validator2)
        self.path_input.setValidator(validator2)
        self.pmt_input.setValidator(validator1)
        self.myLogger.log_signal.connect(self.handleLogSignal)


        for var, edt in self.input_mapping.items():
            edt.textChanged.connect(lambda: self.controller.edt_changed(var))

        self.cbx_range.currentIndexChanged.connect(self.on_cbx_range_changed)
        self.retranslateUi(MainWindow)
        self.oscilloscope_thread = controller.OscilloscopeThread(self.controller)
        self.oscilloscope_thread.update_max_voltage_signal.connect(self.update_max_voltage)
        self.oscilloscope_thread.update_avg_voltage_signal.connect(self.update_avg_voltage)
        self.oscilloscope_thread.handle_range_limit_reached_signal.connect(self.handle_range_limit_reached)
        self.oscilloscope_thread.handle_pmt_limit_reached_signal.connect(self.handle_pmt_limit_reached)
        QMetaObject.connectSlotsByName(MainWindow)


    def handleLogSignal(self, log_message):
        # Update your GUI with log_message
        self.debug_input.append(log_message)  # Assuming debug_input is a QTextEdit widget

    def update_plots(self):
        # Get updated data from the controller.
        cdgraph_data = self.controller.get_data_for_cdgraph()
        g_absgraph_data = self.controller.get_data_for_g_absgraph()
        molar_ellipsgraph_data = self.controller.get_data_for_molar_ellipsgraph()
        ldgraph_data = self.controller.get_data_for_ldgraph()

        # Update the plots.
        self.graphicsView_2.figure.clear()
        self.graphicsView_2.figure.add_subplot(111).plot(cdgraph_data)
        self.graphicsView_2.canvas.draw()

        self.graphicsView_3.figure.clear()
        self.graphicsView_3.figure.add_subplot(111).plot(g_absgraph_data)
        self.graphicsView_3.canvas.draw()

        self.graphicsView_4.figure.clear()
        self.graphicsView_4.figure.add_subplot(111).plot(molar_ellipsgraph_data)
        self.graphicsView_4.canvas.draw()

        self.graphicsView_5.figure.clear()
        self.graphicsView_5.figure.add_subplot(111).plot(ldgraph_data)
        self.graphicsView_5.canvas.draw()


    def reset_edt_color(self, var):
        edt = self.input_mapping[var]
        edt.setStyleSheet("background-color: white")  # reset to white

    def plot_osc(self, data_max, max_len, time_step):
        self.pmt_spectra_view.ax.clear()  # Clear previous plot

        # Ensure data_max is of length max_len
        if len(data_max) > max_len:
            data_max = data_max[-max_len:]  # Trim to max_len if too long
        elif len(data_max) < max_len:
            data_max = [0] * (max_len - len(data_max)) + data_max  # Pad with zeros if too short

        self.pmt_spectra_view.ax.plot(data_max)  # Plot new data
        self.pmt_spectra_view.canvas.draw()  # Update the canvas to show the new plot
        QTimer.singleShot(time_step, self.plot_osc)  # Call the method again after time_step milliseconds.

    @pyqtSlot(float)
    def update_max_voltage(self, voltage):
        self.peak_voltagetext.setText(f"{voltage:.2f} V")

    @pyqtSlot(float)
    def update_avg_voltage(self, voltage):
        self.avg_voltagetext.setText(f"{voltage:.2f} V")

    @pyqtSlot()
    def on_close_button_clicked(self):
        self.closeClicked.emit()

    @pyqtSlot()
    def on_set_gain_clicked(self):
        gain_text = self.gain_input.text()
        gain_value = float(gain_text) if gain_text else 0.0
        self.gainClicked.emit(gain_value)
        self.gain_input.setStyleSheet("background-color: white")  # reset color

    @pyqtSlot()
    def on_set_offset_clicked(self):
        offset_text = self.edt_phaseoffset.text()
        offset_value = float(offset_text) if offset_text else 0.0
        self.offsetClicked.emit(offset_value)
        self.edt_phaseoffset.setStyleSheet("background-color: white")  # reset color

    @pyqtSlot()
    def on_cbx_range_changed(self):
        range_text = self.cbx_range.currentText()
        range_value = float(range_text) if range_text else 0.0
        self.rangeChosen.emit(range_value)

    def on_set_range_clicked(self):
        self.rangeClicked.emit()

    @pyqtSlot()
    def on_start_button_clicked(self):
        reps = int(self.edits_map["edt_rep"].text())
        start_nm = float(self.edits_map["edt_start"].text())
        end_nm = float(self.edits_map["edt_end"].text())
        step = float(self.edits_map["edt_step"].text())
        dwell_time = float(self.edits_map["edt_dwell"].text())
        filename = self.edt_filename.text()
        ac_blank = self.edits_map["edt_ac_blank"].text()
        dc_blank = self.edits_map["edt_dc_blank"].text()
        det_corr = self.edits_map["edt_det_corr"].text()
        pem_off = int(self.input_mapping["edt_excWL"].text())

        self.values_changed.emit(reps, start_nm, end_nm, step, dwell_time, filename, ac_blank, dc_blank, det_corr,
                                 pem_off)

    @pyqtSlot()
    def on_stop_button_clicked(self):
        self.stopbuttonClicked.emit()

    @pyqtSlot()
    def on_save_comments_clicked(self):
        comments_text = self.edt_comment.text()
        comments_value = str(comments_text) if comments_text else "no comments"
        self.savecommentsClicked.emit(comments_value)
        self.edt_comment.setStyleSheet("background-color: white")  # reset color

    @pyqtSlot()
    def on_calibrate_clicked(self):
        self.calibrateClicked.emit()

    @pyqtSlot()
    def on_set_wavelength_clicked(self):
        wavelength_text = self.edt_excWL.text()
        wavelength_value = float(wavelength_text) if wavelength_text else 0.0
        self.setwavelengthClicked.emit(wavelength_value)
        self.edt_excWL.setStyleSheet("background-color: white")  # reset color

    @pyqtSlot()
    def on_set_pmt_clicked(self):
        pmt_text = self.pmt_input.text()
        pmt_value = float(pmt_text) if pmt_text else 0.0
        self.setpmtClicked.emit(pmt_value)
        self.pmt_input.setStyleSheet("background-color: white")  # reset color

    @pyqtSlot()
    def open_cal_dialog(self):
        self.cal_dialog = self.PhaseOffsetCalibrationDialog(self.controller)
        self.cal_dialog.show()


    def setup_matplotlib_widget(self, parent, geometry, name):
        widget = QWidget(parent)
        widget.setObjectName(u"graphicsView_" + name)
        widget.setGeometry(geometry)
        widget.setStyleSheet(u"background-color: rgb(255,255,255)")
        fig = Figure(figsize=(6, 5), dpi=50)
        ax = fig.add_subplot(111)
        canvas = FigureCanvas(fig)
        canvas_layout = QVBoxLayout()
        canvas_layout.addWidget(canvas)
        widget.setLayout(canvas_layout)
        return widget

    # setupUii

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
        self.devicesetup_group.setTitle(QCoreApplication.translate("MainWindow", u"Device Setup", None))
        self.initialize_button.setText(QCoreApplication.translate("MainWindow", u"Initialize", None))
        self.close_button.setText(QCoreApplication.translate("MainWindow", u"Close", None))
        self.label.setText(QCoreApplication.translate("MainWindow", u"PEM      :", None))
        self.label_2.setText(QCoreApplication.translate("MainWindow", u"MON1  :", None))
        self.label_3.setText(QCoreApplication.translate("MainWindow", u"MON2  :", None))
        self.label_4.setText(QCoreApplication.translate("MainWindow", u"MFLI     :", None))
        self.pem_process.setText(QCoreApplication.translate("MainWindow", u"pem_process", None))
        self.monoi_process.setText(QCoreApplication.translate("MainWindow", u"monoi_process", None))
        self.monoii_process.setText(QCoreApplication.translate("MainWindow", u"monoii_process", None))
        self.mfli_process.setText(QCoreApplication.translate("MainWindow", u"mfli_process", None))
        self.signaltuning_group.setTitle(QCoreApplication.translate("MainWindow", u"Signal tuning", None))
        self.label_9.setText(QCoreApplication.translate("MainWindow", u"Peak Voltage :", None))
        self.label_10.setText(QCoreApplication.translate("MainWindow", u"Avg Voltage :", None))
        self.label_11.setText(QCoreApplication.translate("MainWindow", u"PMT Input :", None))
        self.label_12.setText(QCoreApplication.translate("MainWindow", u"Approx gain :", None))
        self.label_13.setText(QCoreApplication.translate("MainWindow", u"Wavelength:", None))
        self.label_15.setText(QCoreApplication.translate("MainWindow", u"Range :", None))
        self.peak_voltagetext.setText(QCoreApplication.translate("MainWindow", u"peak_voltage", None))
        self.avg_voltagetext.setText(QCoreApplication.translate("MainWindow", u"avg_voltage", None))
        self.set_pmt.setText(QCoreApplication.translate("MainWindow", u"Set", None))
        self.var_pem_off.setText(QCoreApplication.translate("MainWindow",u"PEM off", None))
        self.label_26.setText(QCoreApplication.translate("MainWindow", u"Phase Offset:", None))
        self.set_gain.setText(QCoreApplication.translate("MainWindow", u"Set", None))
        self.set_wavelength.setText(QCoreApplication.translate("MainWindow", u"Set", None))
        self.set_range.setText(QCoreApplication.translate("MainWindow", u"Set", None))
        self.set_offset.setText(QCoreApplication.translate("MainWindow", u"Set", None))
        self.calibrate.setText(QCoreApplication.translate("MainWindow", u"Calibrate Phase Offset", None))
        self.spectrasetup_group.setTitle(QCoreApplication.translate("MainWindow", u"Spectra Setup", None))
        self.label_14.setText(QCoreApplication.translate("MainWindow", u"Step size (nm):*", None))
        self.label_18.setText(QCoreApplication.translate("MainWindow", u"Dwell time:*", None))
        self.label_19.setText(QCoreApplication.translate("MainWindow", u"WL min (nm): *", None))
        self.label_20.setText(QCoreApplication.translate("MainWindow", u"WL max (nm):*", None))
        self.label_21.setText(QCoreApplication.translate("MainWindow", u"File name:", None))
        self.label_22.setText(QCoreApplication.translate("MainWindow", u"AC Blank file:", None))
        self.label_23.setText(QCoreApplication.translate("MainWindow", u"Repetitions:*", None))
        self.label_24.setText(QCoreApplication.translate("MainWindow", u"Det. correction:", None))
        self.label_25.setText(QCoreApplication.translate("MainWindow", u"Comments:", None))
        self.label_27.setText(QCoreApplication.translate("MainWindow", u"DC Blank file:", None))
        self.label_28.setText(QCoreApplication.translate("MainWindow", u"Sample C(mol/L):", None))
        self.start_button.setText(QCoreApplication.translate("MainWindow", u"Start", None))
        self.stop_button.setText(QCoreApplication.translate("MainWindow", u"Stop", None))
        self.save_comments.setText(QCoreApplication.translate("MainWindow", u"Save", None))
        self.label_33.setText(QCoreApplication.translate("MainWindow", u"*required", None))
        self.set_path.setText(QCoreApplication.translate("MainWindow", u"Set", None))
        self.label_34.setText(QCoreApplication.translate("MainWindow", u"Path length(mm):", None))
        self.spectra_group.setTitle(QCoreApplication.translate("MainWindow", u"Spectra", None))
        self.label_29.setText(QCoreApplication.translate("MainWindow", u"CD/c*l", None))
        self.label_30.setText(QCoreApplication.translate("MainWindow", u"LD", None))
        self.label_31.setText(QCoreApplication.translate("MainWindow", u"g_abs", None))
        self.label_32.setText(QCoreApplication.translate("MainWindow", u"CD", None))
        self.debug_group.setTitle(QCoreApplication.translate("MainWindow", u"Debug log", None))
        self.debug_input.setPlainText(QCoreApplication.translate("MainWindow", u"Debug goes here", None))
# retranslateUi
    # retranslateUi

    def closeEvent(self, event):
        reply = QMessageBox.question(
            self, 'Quit', 'Do you want to quit?',
            QMessageBox.StandardButtons(QMessageBox.Ok |QMessageBox.Cancel),
            QMessageBox.Cancel)

        if reply == QMessageBox.Ok:
            event.accept()
        else:
            event.ignore()
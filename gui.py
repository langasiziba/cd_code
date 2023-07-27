import queue

from PyQt5.QtCore import (QCoreApplication, QMetaObject, QRect,
                          Qt, pyqtSignal, pyqtSlot, QObject)
from PyQt5.QtGui import (QCursor, QFont, QDoubleValidator)
from PyQt5.QtWidgets import (QGraphicsView, QGroupBox, QLabel,
                             QLineEdit, QPlainTextEdit, QProgressBar,
                             QPushButton, QSizePolicy, QStatusBar, QWidget, QVBoxLayout)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from mfli import MFLI


class Ui_MainWindow(QObject):
    setpmtClicked = pyqtSignal()
    initializeClicked = pyqtSignal()
    closeClicked = pyqtSignal()
    gainClicked = pyqtSignal()
    offsetClicked = pyqtSignal()
    rangeClicked = pyqtSignal()
    stepsizeClicked = pyqtSignal()
    wlmaxClicked = pyqtSignal()
    dwelltimeClicked = pyqtSignal()
    wlminClicked = pyqtSignal()
    filenameClicked = pyqtSignal()
    detcorrectionsClicked = pyqtSignal()
    acClicked = pyqtSignal()
    repetitionsClicked = pyqtSignal()
    samplecClicked = pyqtSignal()
    dcClicked = pyqtSignal()
    startbuttonClicked = pyqtSignal()
    stopbuttonClicked = pyqtSignal()
    savecommentsClicked = pyqtSignal()
    pathClicked = pyqtSignal()
    savenotesClicked = pyqtSignal()

    def __init__(self):
        super().__init__()
        log_queue = queue.Queue()
        self.mfli = MFLI(ID="dev7024", logname="mfli_log", log_queue=log_queue)

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
        self.label_15.setGeometry(QRect(10, 410, 81, 16))
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
        self.save_notes = QPushButton(self.signaltuning_group)
        self.save_notes.setObjectName(u"save_notes")
        self.save_notes.setGeometry(QRect(100, 560, 51, 21))
        self.save_notes.setFont(font2)
        self.save_notes.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.label_26 = QLabel(self.signaltuning_group)
        self.label_26.setObjectName(u"label_26")
        self.label_26.setGeometry(QRect(10, 450, 81, 16))
        self.label_26.setFont(font3)
        self.set_gain = QPushButton(self.signaltuning_group)
        self.set_gain.setObjectName(u"set_gain")
        self.set_gain.setGeometry(QRect(250, 330, 51, 24))
        self.set_gain.setFont(font4)
        self.set_gain.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.set_offset = QPushButton(self.signaltuning_group)
        self.set_offset.setObjectName(u"set_offset")
        self.set_offset.setGeometry(QRect(250, 370, 51, 24))
        self.set_offset.setFont(font4)
        self.set_offset.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.pmt_input = QLineEdit(self.signaltuning_group)
        self.pmt_input.setObjectName(u"pmt_input")
        self.pmt_input.setGeometry(QRect(110, 290, 113, 21))
        self.pmt_input.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.range_input = QLineEdit(self.signaltuning_group)
        self.range_input.setObjectName(u"range_input")
        self.range_input.setGeometry(QRect(110, 410, 113, 21))
        self.range_input.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.gain_input = QLineEdit(self.signaltuning_group)
        self.gain_input.setObjectName(u"gain_input")
        self.gain_input.setGeometry(QRect(110, 330, 113, 21))
        self.gain_input.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.offset_input = QLineEdit(self.signaltuning_group)
        self.offset_input.setObjectName(u"offset_input")
        self.offset_input.setGeometry(QRect(110, 370, 113, 21))
        self.offset_input.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.set_range = QPushButton(self.signaltuning_group)
        self.set_range.setObjectName(u"set_range")
        self.set_range.setGeometry(QRect(250, 410, 51, 24))
        self.set_range.setFont(font4)
        self.set_range.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.notes_input = QPlainTextEdit(self.signaltuning_group)
        self.notes_input.setObjectName(u"notes_input")
        self.notes_input.setGeometry(QRect(110, 450, 191, 81))
        self.notes_input.setFont(font2)
        self.notes_input.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.pmt_spectra_view.raise_()
        self.label_9.raise_()
        self.label_10.raise_()
        self.label_11.raise_()
        self.label_12.raise_()
        self.label_13.raise_()
        self.label_15.raise_()
        self.peak_voltagetext.raise_()
        self.avg_voltagetext.raise_()
        self.set_pmt.raise_()
        self.save_notes.raise_()
        self.label_26.raise_()
        self.set_gain.raise_()
        self.set_offset.raise_()
        self.range_input.raise_()
        self.gain_input.raise_()
        self.offset_input.raise_()
        self.set_range.raise_()
        self.notes_input.raise_()
        self.pmt_input.raise_()
        self.spectrasetup_group = QGroupBox(self.centralwidget)
        self.spectrasetup_group.setObjectName(u"spectrasetup_group")
        self.spectrasetup_group.setGeometry(QRect(390, 10, 381, 851))
        self.spectrasetup_group.setFont(font1)
        self.spectrasetup_group.setAutoFillBackground(False)
        self.spectrasetup_group.setStyleSheet(u"background-color: rgb(195, 235, 255)")
        self.set_stepsize = QPushButton(self.spectrasetup_group)
        self.set_stepsize.setObjectName(u"set_stepsize")
        self.set_stepsize.setGeometry(QRect(280, 140, 51, 24))
        self.set_stepsize.setFont(font4)
        self.set_stepsize.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.wl_min = QLineEdit(self.spectrasetup_group)
        self.wl_min.setObjectName(u"wl_min")
        self.wl_min.setGeometry(QRect(140, 60, 113, 21))
        self.wl_min.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.label_14 = QLabel(self.spectrasetup_group)
        self.label_14.setObjectName(u"label_14")
        self.label_14.setGeometry(QRect(20, 140, 111, 16))
        self.label_14.setFont(font3)
        self.dwelltime_input = QLineEdit(self.spectrasetup_group)
        self.dwelltime_input.setObjectName(u"dwelltime_input")
        self.dwelltime_input.setGeometry(QRect(140, 180, 113, 21))
        self.dwelltime_input.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.wl_max = QLineEdit(self.spectrasetup_group)
        self.wl_max.setObjectName(u"wl_max")
        self.wl_max.setGeometry(QRect(140, 100, 113, 21))
        self.wl_max.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.stepsize_input = QLineEdit(self.spectrasetup_group)
        self.stepsize_input.setObjectName(u"stepsize_input")
        self.stepsize_input.setGeometry(QRect(140, 140, 113, 21))
        self.stepsize_input.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.label_18 = QLabel(self.spectrasetup_group)
        self.label_18.setObjectName(u"label_18")
        self.label_18.setGeometry(QRect(20, 180, 81, 16))
        self.label_18.setFont(font3)
        self.label_19 = QLabel(self.spectrasetup_group)
        self.label_19.setObjectName(u"label_19")
        self.label_19.setGeometry(QRect(20, 60, 101, 16))
        self.label_19.setFont(font3)
        self.set_wl_max = QPushButton(self.spectrasetup_group)
        self.set_wl_max.setObjectName(u"set_wl_max")
        self.set_wl_max.setGeometry(QRect(280, 100, 51, 24))
        self.set_wl_max.setFont(font4)
        self.set_wl_max.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.set_dwelltime = QPushButton(self.spectrasetup_group)
        self.set_dwelltime.setObjectName(u"set_dwelltime")
        self.set_dwelltime.setGeometry(QRect(280, 180, 51, 24))
        self.set_dwelltime.setFont(font4)
        self.set_dwelltime.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.label_20 = QLabel(self.spectrasetup_group)
        self.label_20.setObjectName(u"label_20")
        self.label_20.setGeometry(QRect(20, 100, 91, 16))
        self.label_20.setFont(font3)
        self.set_wlmin = QPushButton(self.spectrasetup_group)
        self.set_wlmin.setObjectName(u"set_wlmin")
        self.set_wlmin.setGeometry(QRect(280, 60, 51, 24))
        self.set_wlmin.setFont(font4)
        self.set_wlmin.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.set_filename = QPushButton(self.spectrasetup_group)
        self.set_filename.setObjectName(u"set_filename")
        self.set_filename.setGeometry(QRect(280, 300, 51, 24))
        self.set_filename.setFont(font4)
        self.set_filename.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.repetitions_input = QLineEdit(self.spectrasetup_group)
        self.repetitions_input.setObjectName(u"repetitions_input")
        self.repetitions_input.setGeometry(QRect(140, 220, 113, 21))
        self.repetitions_input.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.label_21 = QLabel(self.spectrasetup_group)
        self.label_21.setObjectName(u"label_21")
        self.label_21.setGeometry(QRect(20, 300, 81, 16))
        self.label_21.setFont(font3)
        self.ac_input = QLineEdit(self.spectrasetup_group)
        self.ac_input.setObjectName(u"ac_input")
        self.ac_input.setGeometry(QRect(140, 340, 113, 21))
        self.ac_input.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.detcorrection_input = QLineEdit(self.spectrasetup_group)
        self.detcorrection_input.setObjectName(u"detcorrection_input")
        self.detcorrection_input.setGeometry(QRect(140, 260, 113, 21))
        self.detcorrection_input.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.filename_input = QLineEdit(self.spectrasetup_group)
        self.filename_input.setObjectName(u"filename_input")
        self.filename_input.setGeometry(QRect(140, 300, 113, 21))
        self.filename_input.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.label_22 = QLabel(self.spectrasetup_group)
        self.label_22.setObjectName(u"label_22")
        self.label_22.setGeometry(QRect(20, 340, 101, 16))
        self.label_22.setFont(font3)
        self.label_23 = QLabel(self.spectrasetup_group)
        self.label_23.setObjectName(u"label_23")
        self.label_23.setGeometry(QRect(20, 220, 91, 16))
        self.label_23.setFont(font3)
        self.set_detcorrections = QPushButton(self.spectrasetup_group)
        self.set_detcorrections.setObjectName(u"set_detcorrections")
        self.set_detcorrections.setGeometry(QRect(280, 260, 51, 24))
        self.set_detcorrections.setFont(font4)
        self.set_detcorrections.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.set_ac = QPushButton(self.spectrasetup_group)
        self.set_ac.setObjectName(u"set_ac")
        self.set_ac.setGeometry(QRect(280, 340, 51, 24))
        self.set_ac.setFont(font4)
        self.set_ac.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.label_24 = QLabel(self.spectrasetup_group)
        self.label_24.setObjectName(u"label_24")
        self.label_24.setGeometry(QRect(20, 260, 111, 16))
        self.label_24.setFont(font3)
        self.set_repetitions = QPushButton(self.spectrasetup_group)
        self.set_repetitions.setObjectName(u"set_repetitions")
        self.set_repetitions.setGeometry(QRect(280, 220, 51, 24))
        self.set_repetitions.setFont(font4)
        self.set_repetitions.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.dc_input = QLineEdit(self.spectrasetup_group)
        self.dc_input.setObjectName(u"dc_input")
        self.dc_input.setGeometry(QRect(140, 380, 113, 21))
        self.dc_input.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.label_25 = QLabel(self.spectrasetup_group)
        self.label_25.setObjectName(u"label_25")
        self.label_25.setGeometry(QRect(20, 500, 81, 16))
        self.label_25.setFont(font3)
        self.samplec_input = QLineEdit(self.spectrasetup_group)
        self.samplec_input.setObjectName(u"samplec_input")
        self.samplec_input.setGeometry(QRect(140, 420, 113, 21))
        self.samplec_input.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.label_27 = QLabel(self.spectrasetup_group)
        self.label_27.setObjectName(u"label_27")
        self.label_27.setGeometry(QRect(20, 380, 101, 16))
        self.label_27.setFont(font3)
        self.set_samplec = QPushButton(self.spectrasetup_group)
        self.set_samplec.setObjectName(u"set_samplec")
        self.set_samplec.setGeometry(QRect(280, 420, 51, 24))
        self.set_samplec.setFont(font4)
        self.set_samplec.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.label_28 = QLabel(self.spectrasetup_group)
        self.label_28.setObjectName(u"label_28")
        self.label_28.setGeometry(QRect(20, 420, 121, 16))
        self.label_28.setFont(font3)
        self.set_dc = QPushButton(self.spectrasetup_group)
        self.set_dc.setObjectName(u"set_dc")
        self.set_dc.setGeometry(QRect(280, 380, 51, 24))
        self.set_dc.setFont(font4)
        self.set_dc.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.comments_input = QPlainTextEdit(self.spectrasetup_group)
        self.comments_input.setObjectName(u"comments_input")
        self.comments_input.setGeometry(QRect(140, 500, 191, 91))
        self.comments_input.setFont(font2)
        self.comments_input.setStyleSheet(u"background-color: rgb(255, 255, 255)")
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
        self.progressBar = QProgressBar(self.spectrasetup_group)
        self.progressBar.setObjectName(u"progressBar")
        self.progressBar.setGeometry(QRect(80, 780, 251, 23))
        self.progressBar.setFont(font5)
        self.progressBar.setValue(24)
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
        self.path_input.setGeometry(QRect(140, 460, 113, 21))
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
        self.graphicsView_2 = QGraphicsView(self.spectra_group)
        self.graphicsView_2.setObjectName(u"graphicsView_2")
        self.graphicsView_2.setGeometry(QRect(20, 60, 321, 201))
        self.graphicsView_2.setStyleSheet(u"background-color: rgb(255,255,255)")
        self.graphicsView_3 = QGraphicsView(self.spectra_group)
        self.graphicsView_3.setObjectName(u"graphicsView_3")
        self.graphicsView_3.setGeometry(QRect(360, 60, 321, 201))
        self.graphicsView_3.setStyleSheet(u"background-color: rgb(255,255,255)")
        self.graphicsView_4 = QGraphicsView(self.spectra_group)
        self.graphicsView_4.setObjectName(u"graphicsView_4")
        self.graphicsView_4.setGeometry(QRect(20, 290, 321, 201))
        self.graphicsView_4.setStyleSheet(u"background-color: rgb(255,255,255)")
        self.graphicsView_5 = QGraphicsView(self.spectra_group)
        self.graphicsView_5.setObjectName(u"graphicsView_5")
        self.graphicsView_5.setGeometry(QRect(360, 290, 321, 201))
        self.graphicsView_5.setStyleSheet(u"background-color: rgb(255,255,255)")
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

        self.wl_min.setValidator(validator2)
        self.wl_max.setValidator(validator2)
        self.dwelltime_input.setValidator(validator1)
        self.stepsize_input.setValidator(validator0)
        self.gain_input.setValidator(validator2)
        self.offset_input.setValidator(validator2)
        self.range_input.setValidator(validator2)
        self.repetitions_input.setValidator(validator0)
        self.samplec_input.setValidator(validator2)
        self.path_input.setValidator(validator2)
        self.pmt_input.setValidator(validator1)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)

        # connect the actual button clicking
        self.initialize_button.clicked.connect(lambda checked=False: self.on_initialize_clicked())
        self.close_button.clicked.connect(lambda checked=False: self.on_close_clicked)
        self.set_gain.clicked.connect(lambda checked=False: self.on_gain_clicked)
        self.set_offset.clicked.connect(lambda checked=False: self.on_offset_clicked)
        self.set_range.clicked.connect(lambda checked=False: self.on_range_clicked)
        self.set_stepsize.clicked.connect(lambda checked=False: self.on_step_size_clicked)
        self.set_wl_max.clicked.connect(lambda checked=False: self.on_wl_max_clicked)
        self.set_dwelltime.clicked.connect(lambda checked=False: self.on_dwell_time_clicked)
        self.set_wlmin.clicked.connect(lambda checked=False: self.on_wl_min_clicked)
        self.set_filename.clicked.connect(lambda checked=False: self.on_file_name_clicked)
        self.set_detcorrections.clicked.connect(lambda checked=False: self.on_det_corrections_clicked)
        self.set_ac.clicked.connect(lambda checked=False: self.on_ac_clicked)
        self.set_repetitions.clicked.connect(lambda checked=False: self.on_repetitions_clicked)
        self.set_samplec.clicked.connect(lambda checked=False: self.on_sample_c_clicked)
        self.set_dc.clicked.connect(lambda checked=False: self.on_dc_clicked)
        self.start_button.clicked.connect(lambda checked=False: self.on_start_button_clicked)
        self.stop_button.clicked.connect(lambda checked=False: self.on_stop_button_clicked)
        self.save_comments.clicked.connect(lambda checked=False: self.on_save_comments_clicked)
        self.save_notes.clicked.connect(lambda checked=False: self.on_save_notes_clicked)
        self.set_path.clicked.connect(lambda checked=False: self.on_path_clicked)
        self.set_pmt.clicked.connect(lambda checked=False: self.on_pmt_clicked)

    @pyqtSlot(dict)
    def update_plot(self, data):
        self.ax.clear()  # clear the previous plot
        self.ax.plot(data['CD'], data['dc'])
        self.pmt_spectra_view.draw()  # refresh the FigureCanvas

    @pyqtSlot()
    def on_initialize_clicked(self):
        self.initializeClicked.emit()

    @pyqtSlot()
    def on_close_clicked(self):
        self.closeClicked.emit()

    @pyqtSlot()
    def on_gain_clicked(self):
        gain_text = self.gain_input.text()
        gain_value = float(gain_text) if gain_text else 0.0
        self.gainClicked.emit(gain_value)

    @pyqtSlot()
    def on_offset_clicked(self):
        offset_text = self.offset_input.text()
        offset_value = float(offset_text) if offset_text else 0.0
        self.offsetClicked.emit(offset_value)

    @pyqtSlot()
    def on_range_clicked(self):
        range_text = self.range_input.text()
        range_value = float(range_text) if range_text else 0.0
        self.rangeClicked.emit(range_value)

    @pyqtSlot()
    def on_step_size_clicked(self):
        stepsize_text = self.stepsize_input.text()
        stepsize_value = float(stepsize_text) if stepsize_text else 0.0
        self.stepsizeClicked.emit(stepsize_value)

    @pyqtSlot()
    def on_wl_max_clicked(self):
        wlmax_text = self.wl_max.text()
        wlmax_value = float(wlmax_text) if wlmax_text else 0.0
        self.wlmaxClicked.emit(wlmax_value)

    @pyqtSlot()
    def on_dwell_time_clicked(self):
        dwelltime_text = self.dwelltime_input.text()
        dwelltime_value = float(dwelltime_text) if dwelltime_text else 0.0
        self.dwelltimeClicked(dwelltime_value)

    @pyqtSlot()
    def on_wl_min_clicked(self):
        wlmin_text = self.wl_min.text()
        wlmin_value = float(wlmin_text) if wlmin_text else 0.0
        self.wlminClicked(wlmin_value)

    @pyqtSlot()
    def on_file_name_clicked(self):
        self.filenameClicked.emit()

    @pyqtSlot()
    def on_det_corrections_clicked(self):
        self.detcorrectionsClicked.emit()

    @pyqtSlot()
    def on_ac_clicked(self):
        self.acClicked.emit()

    @pyqtSlot()
    def on_repetitions_clicked(self):
        repet_text = self.repetitions_input.text()
        repet_value = float(repet_text) if repet_text else 0.0
        self.repetitionsClicked.emit(repet_value)

    @pyqtSlot()
    def on_sample_c_clicked(self):
        samplec_text = self.samplec_input.text()
        samplec_value = float(samplec_text) if samplec_text else 0.0
        self.mfli.set_samplec(samplec_value)

    @pyqtSlot()
    def on_dc_clicked(self):
        self.dcClicked.emit()

    @pyqtSlot()
    def on_start_button_clicked(self):
        self.startbuttonClicked.emit()

    @pyqtSlot()
    def on_stop_button_clicked(self):
        self.stopbuttonClicked.emit()

    @pyqtSlot()
    def on_save_comments_clicked(self):
        comments_text = self.comments_input.text()
        comments_value = str(comments_text) if comments_text else "no comments"
        self.savecommentsClicked.emit(comments_value)

    def on_save_notes_clicked(self):
        notes_text = self.notes_input.text()
        notes_value = str(notes_text) if notes_text else ("")
        self.savenotesClicked.emit(notes_value)

    @pyqtSlot()
    def on_path_clicked(self):
        path_text = self.path_input.text()
        path_value = float(path_text) if path_text else 0.0
        self.pathClicked.emit(path_value)

    @pyqtSlot()
    def on_pmt_clicked(self):
        pmt_text = self.pmt_input.text()
        pmt_value = float(pmt_text) if pmt_text else 0.0
        self.pathClicked.emit(pmt_value)

    # setupUi
    # setupUi

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
        self.label_13.setText(QCoreApplication.translate("MainWindow", u"Phase Offset :", None))
        self.label_15.setText(QCoreApplication.translate("MainWindow", u"Range :", None))
        self.peak_voltagetext.setText(QCoreApplication.translate("MainWindow", u"peak_voltage", None))
        self.avg_voltagetext.setText(QCoreApplication.translate("MainWindow", u"avg_voltage", None))
        self.set_pmt.setText(QCoreApplication.translate("MainWindow", u"Set", None))
        self.save_notes.setText(QCoreApplication.translate("MainWindow", u"Save", None))
        self.label_26.setText(QCoreApplication.translate("MainWindow", u"Notes :", None))
        self.set_gain.setText(QCoreApplication.translate("MainWindow", u"Set", None))
        self.set_offset.setText(QCoreApplication.translate("MainWindow", u"Set", None))
        self.set_range.setText(QCoreApplication.translate("MainWindow", u"Set", None))
        self.notes_input.setPlainText("")
        self.spectrasetup_group.setTitle(QCoreApplication.translate("MainWindow", u"Spectra Setup", None))
        self.set_stepsize.setText(QCoreApplication.translate("MainWindow", u"Set", None))
        self.label_14.setText(QCoreApplication.translate("MainWindow", u"Step size (nm):*", None))
        self.label_18.setText(QCoreApplication.translate("MainWindow", u"Dwell time:*", None))
        self.label_19.setText(QCoreApplication.translate("MainWindow", u"WL min (nm): *", None))
        self.set_wl_max.setText(QCoreApplication.translate("MainWindow", u"Set", None))
        self.set_dwelltime.setText(QCoreApplication.translate("MainWindow", u"Set", None))
        self.label_20.setText(QCoreApplication.translate("MainWindow", u"WL max (nm):*", None))
        self.set_wlmin.setText(QCoreApplication.translate("MainWindow", u"Set", None))
        self.set_filename.setText(QCoreApplication.translate("MainWindow", u"Set", None))
        self.label_21.setText(QCoreApplication.translate("MainWindow", u"File name:", None))
        self.label_22.setText(QCoreApplication.translate("MainWindow", u"AC Blank file:", None))
        self.label_23.setText(QCoreApplication.translate("MainWindow", u"Repetitions:*", None))
        self.set_detcorrections.setText(QCoreApplication.translate("MainWindow", u"Set", None))
        self.set_ac.setText(QCoreApplication.translate("MainWindow", u"Set", None))
        self.label_24.setText(QCoreApplication.translate("MainWindow", u"Det. correction:", None))
        self.set_repetitions.setText(QCoreApplication.translate("MainWindow", u"Set", None))
        self.label_25.setText(QCoreApplication.translate("MainWindow", u"Comments:", None))
        self.label_27.setText(QCoreApplication.translate("MainWindow", u"DC Blank file:", None))
        self.set_samplec.setText(QCoreApplication.translate("MainWindow", u"Set", None))
        self.label_28.setText(QCoreApplication.translate("MainWindow", u"Sample C(mol/L):", None))
        self.set_dc.setText(QCoreApplication.translate("MainWindow", u"Set", None))
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
from PyQt5.QtCore import (QCoreApplication, QRect,
                          Qt, pyqtSignal, pyqtSlot, QMetaObject)
from PyQt5.QtGui import (QCursor, QFont, QDoubleValidator)
from PyQt5.QtWidgets import (QGroupBox, QLabel,
                             QLineEdit, QPlainTextEdit, QProgressBar,
                             QSizePolicy, QStatusBar, QWidget, QVBoxLayout, QComboBox, QMessageBox, QMainWindow,
                             QCheckBox)
from PyQt5.QtWidgets import QPushButton
from matplotlib import ticker
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from debug import LogObject


class Ui_MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.controller = None
        self.logObject = LogObject()
        self.logObject.log_signal.connect(self.append_to_log)

    def setController(self, controller):
        # Use the controller passed as a parameter
        self.controller = controller
        self.controller.set_pem()
        self.controller.set_mono()
        self.controller.set_mfli()

    @pyqtSlot(str)
    def update_mfli(self, s):
        self.txt_mfli.setText(f"{s}")

    @pyqtSlot(str)
    def update_pem(self, s):
        self.txt_PEM.setText(f"{s}")

    @pyqtSlot(str)
    def update_mono(self, s):
        self.txt_monoi.setText(f"{s}")
        self.txt_monoii.setText(f"{s}")

    @pyqtSlot(str)
    def append_to_log(self, text):
        self.debug_log.appendPlainText(text)  # Assuming debug_log_textedit is your QTextEdit widget

    def plot(self, fig, canvas, ax, xlabel, ylabel, title, data, avgdata=[]):
        ax.clear()

        formatter = ticker.ScalarFormatter(useMathText=True)
        formatter.set_scientific(True)
        formatter.set_powerlimits((0, 0))

        ax.set_xlabel(xlabel, fontsize=10)
        ax.set_ylabel(ylabel, fontsize=10)
        ax.set_title(title, fontsize=10)
        ax.yaxis.set_major_formatter(formatter)

        ax.plot(data[0], data[1])

        if len(avgdata) > 0:
            if len(avgdata[0]) == len(avgdata[1]) and len(avgdata[0]) > 0:
                ax.plot(avgdata[0], avgdata[1])

        fig.subplots_adjust(
            left=0.05,
            bottom=0.1,
            right=0.985,
            top=0.985,
            wspace=0.0,
            hspace=0.0)

        if fig == self.osc_fig:
            fig.set_facecolor("#C3C3FF")
        elif fig in [self.gabs_fig, self.cd_fig, self.ld_fig, self.ellips_fig]:
            fig.set_facecolor("#C3FFFF")

        canvas.draw()

    def plot_osc(self, data_max, max_len, time_step):
        self.plot(fig=self.osc_fig, canvas=self.osc_canvas, ax=self.osc_ax,
                  data=[[-(min(max_len, data_max.size) - i) / (time_step / 10) for i in range(0, data_max.size)],
                        data_max],
                  xlabel='', ylabel='', title='')

    def plot_spec(self, fig, canvas, ax, tot=[], tot_avg=[], cd=[], cd_avg=[], gabs=[], gabs_avg=[], ellips=[],
                  ellips_avg=[], title=''):
        ax.clear()

        formatter = ticker.ScalarFormatter(useMathText=True)
        formatter.set_scientific(True)
        formatter.set_powerlimits((0, 0))

        ax.set_xlabel('', fontsize=10)
        ax.set_ylabel('', fontsize=10)
        ax.set_title(title, fontsize=10)
        ax.yaxis.set_major_formatter(formatter)

        if tot:
            ax.plot(tot[0], tot[1])

        if tot_avg:
            ax.plot(tot_avg[0], tot_avg[1])

        if cd:
            ax.plot(cd[0], cd[1])

        if cd_avg:
            ax.plot(cd_avg[0], cd_avg[1])

        if gabs:
            ax.plot(gabs[0], gabs[1])

        if gabs_avg:
            ax.plot(gabs_avg[0], gabs_avg[1])

        if ellips:
            ax.plot(ellips[0], ellips[1])

        if ellips_avg:
            ax.plot(ellips_avg[0], ellips_avg[1])

        fig.subplots_adjust(
            left=0.05,
            bottom=0.1,
            right=0.985,
            top=0.985,
            wspace=0.0,
            hspace=0.4)

        fig.set_facecolor("#FFEDCC")
        ax.axhline(y=0.0, color="#0000004E", linestyle='-')
        canvas.draw()

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
        self.btn_init = QPushButton(self.devicesetup_group)
        self.btn_init.setObjectName(u"btn_init")
        self.btn_init.setGeometry(QRect(10, 40, 75, 24))
        font2 = QFont()
        font2.setFamily(u"Segoe UI Historic")
        font2.setPointSize(9)
        self.btn_init.setFont(font2)
        self.btn_init.setAutoFillBackground(False)
        self.btn_init.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.btn_close = QPushButton(self.devicesetup_group)
        self.btn_close.setObjectName(u"btn_close")
        self.btn_close.setGeometry(QRect(10, 70, 75, 24))
        self.btn_close.setFont(font2)
        self.btn_close.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.btn_close.setEnabled(False)
        self.btn_solvent = QPushButton(self.devicesetup_group)
        self.btn_solvent.setObjectName(u"btn_close")
        self.btn_solvent.setGeometry(QRect(10, 100, 75, 24))
        self.btn_solvent.setFont(font2)
        self.btn_solvent.setStyleSheet(u"background-color: rgb(255, 255, 200)")
        self.btn_solvent.setEnabled(True)

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
        self.label = QLabel(self.devicesetup_group)
        self.label.setObjectName(u"label")
        self.label.setGeometry(QRect(10, 220, 49, 16))
        self.label.setFont(font2)

        self.txt_monoi = QLabel(self.devicesetup_group)
        self.txt_monoi.setObjectName(u"txt_monoi")
        self.txt_monoi.setGeometry(QRect(70, 130, 101, 20))
        self.txt_monoi.setFont(font2)
        self.txt_monoii = QLabel(self.devicesetup_group)
        self.txt_monoii.setObjectName(u"txt_monoi")
        self.txt_monoii.setGeometry(QRect(70, 160, 111, 16))
        self.txt_monoii.setFont(font2)
        self.txt_mfli = QLabel(self.devicesetup_group)
        self.txt_mfli.setObjectName(u"txt_mfli")
        self.txt_mfli.setGeometry(QRect(70, 190, 91, 16))
        self.txt_mfli.setFont(font2)
        self.txt_PEM = QLabel(self.devicesetup_group)
        self.txt_PEM.setObjectName(u"txt_PEM")
        self.txt_PEM.setGeometry(QRect(70, 220, 91, 16))
        self.txt_PEM.setFont(font2)
        self.signaltuning_group = QGroupBox(self.centralwidget)
        self.signaltuning_group.setObjectName(u"signaltuning_group")
        self.signaltuning_group.setGeometry(QRect(10, 260, 371, 601))
        self.signaltuning_group.setFont(font1)
        self.signaltuning_group.setAutoFillBackground(False)
        self.signaltuning_group.setStyleSheet(u"background-color: rgb(195, 195, 255)")
        self.signaltuning_group.setEnabled(False)

        # Oscilloscope Figure
        # Create the figure
        self.osc_fig = Figure(figsize=(7, 5.5), dpi=50)
        # Create the subplot
        self.osc_ax = self.osc_fig.add_subplot(111)
        self.osc_ax.set_ylabel('', fontsize=10)
        self.osc_fig.set_facecolor("#C3C3FF")
        # Create the canvas
        self.osc_widget = QWidget(self.signaltuning_group)
        self.osc_canvas = FigureCanvas(self.osc_fig)
        # Add the canvas to the groupbox
        osc_layout = QVBoxLayout(self.osc_widget)
        osc_layout.addWidget(self.osc_canvas)
        # Set up the canvas
        self.osc_fig.subplots_adjust(
            left=0.05,
            bottom=0.1,
            right=0.985,
            top=0.985,
            wspace=0.0,
            hspace=0.0)
        self.osc_widget.setGeometry(20, 20, 321, 191)
        self.osc_canvas.draw()

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
        self.txt_maxVolt = QLabel(self.signaltuning_group)
        self.txt_maxVolt.setObjectName(u"txt_maxVolt")
        self.txt_maxVolt.setGeometry(QRect(110, 220, 91, 16))
        self.txt_maxVolt.setFont(font3)
        self.txt_avgVolt = QLabel(self.signaltuning_group)
        self.txt_avgVolt.setObjectName(u"txt_avgVolt")
        self.txt_avgVolt.setGeometry(QRect(110, 250, 81, 16))
        self.txt_avgVolt.setFont(font3)
        self.btn_set_PMT = QPushButton(self.signaltuning_group)
        self.btn_set_PMT.setObjectName(u"btn_set_PMT")
        self.btn_set_PMT.setGeometry(QRect(250, 290, 51, 24))
        font4 = QFont()
        font4.setFamily(u"Segoe UI Semibold")
        font4.setPointSize(9)
        self.btn_set_PMT.setFont(font4)
        self.btn_set_PMT.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.label_26 = QLabel(self.signaltuning_group)
        self.label_26.setObjectName(u"label_26")
        self.label_26.setGeometry(QRect(10, 450, 81, 21))
        self.label_26.setFont(font3)
        self.btn_set_gain = QPushButton(self.signaltuning_group)
        self.btn_set_gain.setObjectName(u"btn_set_gain")
        self.btn_set_gain.setGeometry(QRect(250, 330, 51, 24))
        self.btn_set_gain.setFont(font4)
        self.btn_set_gain.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.btn_set_WL = QPushButton(self.signaltuning_group)
        self.btn_set_WL.setObjectName(u"btn_set_WL")
        self.btn_set_WL.setGeometry(QRect(250, 370, 51, 24))
        self.btn_set_WL.setFont(font4)
        self.btn_set_WL.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.edt_pmt = QLineEdit(self.signaltuning_group)
        self.edt_pmt.setObjectName(u"edt_pmt")
        self.edt_pmt.setGeometry(QRect(110, 290, 113, 21))
        self.edt_pmt.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.cbx_range = QComboBox(self.signaltuning_group)
        self.cbx_range.setObjectName(u"cbx_range")
        self.cbx_range.setGeometry(QRect(110, 410, 113, 21))
        # add items to the combo box
        self.cbx_range.addItem("0.003")
        self.cbx_range.addItem("0.010")
        self.cbx_range.addItem("0.030")
        self.cbx_range.addItem("0.100")
        self.cbx_range.addItem("0.200")
        self.cbx_range.addItem("1.000")
        self.cbx_range.addItem("3.000")

        self.edt_gain = QLineEdit(self.signaltuning_group)
        self.edt_gain.setObjectName(u"edt_gain")
        self.edt_gain.setGeometry(QRect(110, 330, 113, 21))
        self.edt_gain.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.edt_WL = QLineEdit(self.signaltuning_group)
        self.edt_WL.setObjectName(u"edt_WL")
        self.edt_WL.setGeometry(QRect(110, 370, 113, 21))
        self.edt_WL.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.btn_autorange = QPushButton(self.signaltuning_group)
        self.btn_autorange.setObjectName(u"btn_autorange")
        self.btn_autorange.setGeometry(QRect(250, 410, 51, 24))
        self.btn_autorange.setFont(font4)
        self.btn_autorange.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.edt_phaseoffset = QLineEdit(self.signaltuning_group)
        self.edt_phaseoffset.setObjectName(u"edt_phaseoffset")
        self.edt_phaseoffset.setGeometry(QRect(110, 450, 113, 21))
        self.edt_phaseoffset.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.btn_set_phaseoffset = QPushButton(self.signaltuning_group)
        self.btn_set_phaseoffset.setObjectName(u"btn_set_phaseoffset")
        self.btn_set_phaseoffset.setGeometry(QRect(250, 450, 51, 24))
        self.btn_set_phaseoffset.setFont(font4)
        self.btn_set_phaseoffset.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.btn_cal_phaseoffset = QPushButton(self.signaltuning_group)
        self.btn_cal_phaseoffset.setObjectName(u"btn_cal_phaseoffset")
        self.btn_cal_phaseoffset.setEnabled(True)
        self.btn_cal_phaseoffset.setGeometry(QRect(110, 490, 191, 24))
        self.btn_cal_phaseoffset.setFont(font4)
        self.btn_cal_phaseoffset.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.osc_canvas.raise_()
        self.label_9.raise_()
        self.label_10.raise_()
        self.label_11.raise_()
        self.label_12.raise_()
        self.label_13.raise_()
        self.label_15.raise_()
        self.txt_maxVolt.raise_()
        self.txt_avgVolt.raise_()
        self.btn_set_PMT.raise_()
        self.label_26.raise_()
        self.btn_set_gain.raise_()
        self.btn_set_WL.raise_()
        self.cbx_range.raise_()
        self.edt_gain.raise_()
        self.edt_WL.raise_()
        self.btn_autorange.raise_()
        self.edt_pmt.raise_()
        self.edt_phaseoffset.raise_()
        self.btn_set_phaseoffset.raise_()
        self.btn_cal_phaseoffset.raise_()
        self.spectrasetup_group = QGroupBox(self.centralwidget)
        self.spectrasetup_group.setObjectName(u"spectrasetup_group")
        self.spectrasetup_group.setGeometry(QRect(390, 10, 381, 705))
        self.spectrasetup_group.setFont(font1)
        self.spectrasetup_group.setAutoFillBackground(False)
        self.spectrasetup_group.setStyleSheet(u"background-color: rgb(195, 235, 255)")
        self.spectrasetup_group.setEnabled(False)

        self.edt_base = QLineEdit(self.spectrasetup_group)
        self.edt_base.setObjectName(u"edt_base")
        self.edt_base.setGeometry(QRect(140, 30, 155, 21))
        self.edt_base.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.label_39 = QLabel(self.spectrasetup_group)
        self.label_39.setObjectName(u"label_39")
        self.label_39.setGeometry(QRect(20, 30, 111, 16))
        self.label_39.setFont(font3)
        self.edt_start = QLineEdit(self.spectrasetup_group)
        self.edt_start.setObjectName(u"edt_start")
        self.edt_start.setGeometry(QRect(140, 70, 155, 21))
        self.edt_start.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.label_14 = QLabel(self.spectrasetup_group)
        self.label_14.setObjectName(u"label_14")
        self.label_14.setGeometry(QRect(20, 150, 111, 16))
        self.label_14.setFont(font3)
        self.edt_dwell = QLineEdit(self.spectrasetup_group)
        self.edt_dwell.setObjectName(u"edt_dwell")
        self.edt_dwell.setGeometry(QRect(140, 190, 155, 21))
        self.edt_dwell.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.edt_end = QLineEdit(self.spectrasetup_group)
        self.edt_end.setObjectName(u"edt_end")
        self.edt_end.setGeometry(QRect(140, 110, 155, 21))
        self.edt_end.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.edt_step = QLineEdit(self.spectrasetup_group)
        self.edt_step.setObjectName(u"edt_step")
        self.edt_step.setGeometry(QRect(140, 150, 155, 21))
        self.edt_step.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.label_18 = QLabel(self.spectrasetup_group)
        self.label_18.setObjectName(u"label_18")
        self.label_18.setGeometry(QRect(20, 190, 81, 16))
        self.label_18.setFont(font3)
        self.label_19 = QLabel(self.spectrasetup_group)
        self.label_19.setObjectName(u"label_19")
        self.label_19.setGeometry(QRect(20, 70, 101, 16))
        self.label_19.setFont(font3)
        self.label_20 = QLabel(self.spectrasetup_group)
        self.label_20.setObjectName(u"label_20")
        self.label_20.setGeometry(QRect(20, 110, 91, 16))
        self.label_20.setFont(font3)
        self.edt_rep = QLineEdit(self.spectrasetup_group)
        self.edt_rep.setObjectName(u"edt_rep")
        self.edt_rep.setGeometry(QRect(140, 230, 155, 21))
        self.edt_rep.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.label_21 = QLabel(self.spectrasetup_group)
        self.label_21.setObjectName(u"label_21")
        self.label_21.setGeometry(QRect(20, 310, 81, 16))
        self.label_21.setFont(font3)
        self.edt_ac_blank = QLineEdit(self.spectrasetup_group)
        self.edt_ac_blank.setObjectName(u"edt_ac_blank")
        self.edt_ac_blank.setGeometry(QRect(140, 350, 155, 21))
        self.edt_ac_blank.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.edt_det_corr = QLineEdit(self.spectrasetup_group)
        self.edt_det_corr.setObjectName(u"edt_det_corr")
        self.edt_det_corr.setGeometry(QRect(140, 270, 155, 21))
        self.edt_det_corr.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.edt_filename = QLineEdit(self.spectrasetup_group)
        self.edt_filename.setObjectName(u"edt_filename")
        self.edt_filename.setGeometry(QRect(140, 310, 155, 21))
        self.edt_filename.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.label_22 = QLabel(self.spectrasetup_group)
        self.label_22.setObjectName(u"label_22")
        self.label_22.setGeometry(QRect(20, 350, 101, 16))
        self.label_22.setFont(font3)
        self.label_23 = QLabel(self.spectrasetup_group)
        self.label_23.setObjectName(u"label_23")
        self.label_23.setGeometry(QRect(20, 230, 91, 16))
        self.label_23.setFont(font3)
        self.label_24 = QLabel(self.spectrasetup_group)
        self.label_24.setObjectName(u"label_24")
        self.label_24.setGeometry(QRect(20, 270, 111, 16))
        self.label_24.setFont(font3)
        self.edt_dc_blank = QLineEdit(self.spectrasetup_group)
        self.edt_dc_blank.setObjectName(u"edt_dc_blank")
        self.edt_dc_blank.setGeometry(QRect(140, 390, 155, 21))
        self.edt_dc_blank.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.label_25 = QLabel(self.spectrasetup_group)
        self.label_25.setObjectName(u"label_25")
        self.label_25.setGeometry(QRect(20, 510, 81, 16))
        self.label_25.setFont(font3)
        self.edt_samplec = QLineEdit(self.spectrasetup_group)
        self.edt_samplec.setObjectName(u"edt_samplec")
        self.edt_samplec.setGeometry(QRect(140, 430, 155, 21))
        self.edt_samplec.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.label_27 = QLabel(self.spectrasetup_group)
        self.label_27.setObjectName(u"label_27")
        self.label_27.setGeometry(QRect(20, 390, 101, 16))
        self.label_27.setFont(font3)
        self.label_28 = QLabel(self.spectrasetup_group)
        self.label_28.setObjectName(u"label_28")
        self.label_28.setGeometry(QRect(20, 430, 121, 16))
        self.label_28.setFont(font3)
        self.edt_comment = QPlainTextEdit(self.spectrasetup_group)
        self.edt_comment.setObjectName(u"edt_comment")
        self.edt_comment.setGeometry(QRect(140, 510, 191, 91))
        self.edt_comment.setFont(font2)
        self.edt_comment.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.var_pem_off = QCheckBox(self.spectrasetup_group)
        self.var_pem_off.setObjectName(u"var_pem_off")
        self.var_pem_off.setGeometry(QRect(140, 680, 121, 16))

        self.spectraset_group = QGroupBox(self.centralwidget)
        self.spectraset_group.setObjectName(u"spectraset_group")
        self.spectraset_group.setGeometry(QRect(390, 715, 381, 146))
        self.spectraset_group.setFont(font1)
        self.spectraset_group.setAutoFillBackground(False)
        self.spectraset_group.setStyleSheet(u"background-color: rgb(195, 235, 255)")
        self.spectraset_group.setEnabled(False)
        self.btn_start = QPushButton(self.spectraset_group)
        self.btn_start.setObjectName(u"btn_start")
        self.btn_start.setGeometry(QRect(90, 30, 91, 41))
        font5 = QFont()
        font5.setFamily(u"Segoe UI Semibold")
        font5.setPointSize(13)
        self.btn_start.setFont(font5)
        self.btn_start.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.btn_abort = QPushButton(self.spectraset_group)
        self.btn_abort.setObjectName(u"btn_abort")
        self.btn_abort.setGeometry(QRect(210, 30, 91, 41))
        self.btn_abort.setFont(font5)
        self.btn_abort.setStyleSheet(u"background-color: rgb(255, 99, 99)")
        self.save_comments = QPushButton(self.spectrasetup_group)
        self.save_comments.setObjectName(u"save_comments")
        self.save_comments.setGeometry(QRect(140, 610, 51, 21))
        self.save_comments.setFont(font2)
        self.save_comments.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.progressBar = QProgressBar(self.spectrasetup_group)
        self.progressBar.setObjectName(u"progressBar")
        self.progressBar.setGeometry(QRect(80, 790, 251, 23))
        self.progressBar.setFont(font5)
        self.progressBar.setValue(0)
        self.label_33 = QLabel(self.spectrasetup_group)
        self.label_33.setObjectName(u"label_33")
        self.label_33.setGeometry(QRect(140, 650, 71, 16))
        self.label_33.setFont(font2)
        self.edt_pathl = QLineEdit(self.spectrasetup_group)
        self.edt_pathl.setObjectName(u"edt_pathl")
        self.edt_pathl.setGeometry(QRect(140, 470, 155, 21))
        self.edt_pathl.setStyleSheet(u"background-color: rgb(255, 255, 255)")
        self.label_34 = QLabel(self.spectrasetup_group)
        self.label_34.setObjectName(u"label_34")
        self.label_34.setGeometry(QRect(20, 470, 121, 16))
        self.label_34.setFont(font3)
        self.spectra_group = QGroupBox(self.centralwidget)
        self.spectra_group.setObjectName(u"spectra_group")
        self.spectra_group.setGeometry(QRect(780, 10, 691, 521))
        self.spectra_group.setFont(font1)
        self.spectra_group.setAutoFillBackground(False)
        self.spectra_group.setStyleSheet(u"background-color: rgb(195, 255, 255)")
        self.spectra_group.setEnabled(False)

        # gabs
        # Create the figure
        self.gabs_fig = Figure(figsize=(7, 5.5), dpi=50)
        # Create the subplot
        self.gabs_ax = self.gabs_fig.add_subplot(111)
        self.gabs_fig.set_facecolor("#C3FFFF")
        self.gabs_ax.set_ylabel('', fontsize=10)
        # Create the canvas
        self.gabs_canvas = FigureCanvas(self.gabs_fig)
        self.gabs_widget = QWidget(self.spectra_group)
        self.gabs_layout = QVBoxLayout(self.gabs_widget)
        self.gabs_layout.addWidget(self.gabs_canvas)
        # Set up the canvas
        self.gabs_fig.subplots_adjust(
            left=0.05,
            bottom=0.1,
            right=0.985,
            top=0.985,
            wspace=0.0,
            hspace=0.0)
        self.gabs_widget.setGeometry(20, 60, 341, 221)
        self.gabs_canvas.draw()

        # cd
        # Create the figure
        self.cd_fig = Figure(figsize=(7, 5.5), dpi=50)
        # Create the subplot
        self.cd_ax = self.cd_fig.add_subplot(111)
        self.cd_fig.set_facecolor("#C3FFFF")
        self.cd_ax.set_ylabel('', fontsize=10)
        # Create the canvas
        self.cd_canvas = FigureCanvas(self.cd_fig)
        # Add the canvas to the groupbox
        self.cd_widget = QWidget(self.spectra_group)
        self.cd_layout = QVBoxLayout(self.cd_widget)
        self.cd_layout.addWidget(self.cd_canvas)
        # Set up the canvas
        self.cd_fig.subplots_adjust(
            left=0.05,
            bottom=0.1,
            right=0.985,
            top=0.985,
            wspace=0.0,
            hspace=0.0)
        self.cd_widget.setGeometry(360, 60, 341, 221)
        self.cd_canvas.draw()

        # ld
        # Create the figure
        self.ld_fig = Figure(figsize=(7, 5.5), dpi=50)
        # Create the subplot
        self.ld_ax = self.ld_fig.add_subplot(111)
        self.ld_fig.set_facecolor("#C3FFFF")
        self.ld_ax.set_ylabel('', fontsize=10)
        # Create the canvas
        self.ld_canvas = FigureCanvas(self.ld_fig)
        # Add the canvas to the groupbox
        self.ld_widget = QWidget(self.spectra_group)
        self.ld_layout = QVBoxLayout(self.ld_widget)
        self.ld_layout.addWidget(self.ld_canvas)
        # Set up the canvas
        self.ld_fig.subplots_adjust(
            left=0.05,
            bottom=0.1,
            right=0.985,
            top=0.985,
            wspace=0.0,
            hspace=0.0)
        self.ld_widget.setGeometry(20, 290, 341, 221)
        self.ld_canvas.draw()

        # ellips
        # Create the figure
        self.ellips_fig = Figure(figsize=(7, 5.5), dpi=50)
        # Create the subplot
        self.ellips_ax = self.ellips_fig.add_subplot(111)
        self.ellips_fig.set_facecolor("#C3FFFF")
        self.ellips_ax.set_ylabel('', fontsize=10)
        # Create the canvas
        self.ellips_canvas = FigureCanvas(self.ellips_fig)
        # Add the canvas to the groupbox
        self.ellips_widget = QWidget(self.spectra_group)
        self.ellips_layout = QVBoxLayout(self.ellips_widget)
        self.ellips_layout.addWidget(self.ellips_canvas)
        # Set up the canvas
        self.ellips_fig.subplots_adjust(
            left=0.05,
            bottom=0.1,
            right=0.985,
            top=0.985,
            wspace=0.0,
            hspace=0.0)
        self.ellips_widget.setGeometry(360, 290, 341, 221)
        self.ellips_canvas.draw()


        self.debug_group = QGroupBox(self.centralwidget)
        self.debug_group.setObjectName(u"debug_group")
        self.debug_group.setGeometry(QRect(780, 540, 691, 321))
        self.debug_group.setFont(font1)
        self.debug_group.setAutoFillBackground(True)
        self.debug_log = QPlainTextEdit(self.debug_group)
        self.debug_log.setObjectName(u"debug_log")
        self.debug_log.setGeometry(QRect(10, 40, 661, 261))
        sizePolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.debug_log.sizePolicy().hasHeightForWidth())
        self.debug_log.setSizePolicy(sizePolicy)
        self.debug_log.setFont(font2)
        self.debug_log.viewport().setProperty("cursor", QCursor(Qt.IBeamCursor))
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
        self.edt_gain.setValidator(validator2)
        self.edt_phaseoffset.setValidator(validator2)
        self.edt_rep.setValidator(validator0)
        self.edt_samplec.setValidator(validator2)
        self.edt_pathl.setValidator(validator2)
        self.edt_pmt.setValidator(validator1)

        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)

    # setupUii

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
        self.devicesetup_group.setTitle(QCoreApplication.translate("MainWindow", u"Device Setup", None))
        self.btn_init.setText(QCoreApplication.translate("MainWindow", u"Initialize", None))
        self.btn_close.setText(QCoreApplication.translate("MainWindow", u"Close", None))
        self.btn_solvent.setText(QCoreApplication.translate("MainWindow", u"Base Reading", None))
        self.label.setText(QCoreApplication.translate("MainWindow", u"PEM      :", None))
        self.label_2.setText(QCoreApplication.translate("MainWindow", u"MON1  :", None))
        self.label_3.setText(QCoreApplication.translate("MainWindow", u"MON2  :", None))
        self.label_4.setText(QCoreApplication.translate("MainWindow", u"MFLI     :", None))
        self.txt_PEM.setText(QCoreApplication.translate("MainWindow", u"Not Initialized", None))
        self.txt_monoi.setText(QCoreApplication.translate("MainWindow", u"Not Initialized", None))
        self.txt_monoii.setText(QCoreApplication.translate("MainWindow", u"Not Initialized", None))
        self.txt_mfli.setText(QCoreApplication.translate("MainWindow", u"Not Initialized", None))
        self.signaltuning_group.setTitle(QCoreApplication.translate("MainWindow", u"Signal Tuning", None))
        self.label_9.setText(QCoreApplication.translate("MainWindow", u"Peak Voltage :", None))
        self.label_10.setText(QCoreApplication.translate("MainWindow", u"Avg Voltage :", None))
        self.label_11.setText(QCoreApplication.translate("MainWindow", u"PMT Input :", None))
        self.label_12.setText(QCoreApplication.translate("MainWindow", u"Approx gain :", None))
        self.label_13.setText(QCoreApplication.translate("MainWindow", u"Wavelength:", None))
        self.label_15.setText(QCoreApplication.translate("MainWindow", u"Range :", None))
        self.label_39.setText(QCoreApplication.translate("MainWindow", u"Base reading:", None))
        self.txt_avgVolt.setText(QCoreApplication.translate("MainWindow", u"peak_voltage", None))
        self.txt_maxVolt.setText(QCoreApplication.translate("MainWindow", u"avg_voltage", None))
        self.btn_set_PMT.setText(QCoreApplication.translate("MainWindow", u"Set", None))
        self.var_pem_off.setText(QCoreApplication.translate("MainWindow", u"PEM off", None))
        self.label_26.setText(QCoreApplication.translate("MainWindow", u"Phase Offset:", None))
        self.btn_set_gain.setText(QCoreApplication.translate("MainWindow", u"Set", None))
        self.btn_set_WL.setText(QCoreApplication.translate("MainWindow", u"Set", None))
        self.btn_autorange.setText(QCoreApplication.translate("MainWindow", u"AUTO", None))
        self.btn_set_phaseoffset.setText(QCoreApplication.translate("MainWindow", u"Set", None))
        self.btn_cal_phaseoffset.setText(QCoreApplication.translate("MainWindow", u"Calibrate Phase Offset", None))
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
        self.btn_start.setText(QCoreApplication.translate("MainWindow", u"Start", None))
        self.btn_abort.setText(QCoreApplication.translate("MainWindow", u"Stop", None))
        self.save_comments.setText(QCoreApplication.translate("MainWindow", u"Save", None))
        self.label_33.setText(QCoreApplication.translate("MainWindow", u"*required", None))
        self.label_34.setText(QCoreApplication.translate("MainWindow", u"Path length(mm):", None))
        self.spectra_group.setTitle(QCoreApplication.translate("MainWindow", u"Spectra", None))
        self.debug_group.setTitle(QCoreApplication.translate("MainWindow", u"Debug log", None))
        self.debug_log.setPlainText(QCoreApplication.translate("MainWindow", u"Debug log", None))

    # retranslateUi

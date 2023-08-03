import collections
import math
import os
import queue
import re
import threading as th
import time

import numpy as np
import pandas as pd
import pyvisa
from PyQt5 import QtWidgets
from PyQt5.QtCore import QTimer, QCoreApplication, Qt, pyqtSignal
from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtWidgets import QVBoxLayout, QDialog, QLabel, QPushButton

import gui
from debug import LogObject
from mfli import MFLI
from mono import Monoi, Monoii
from pem import PEM


# Combines the individual components and controls the main window
class Controller(QMainWindow, LogObject):
    # update_mono_edt_lbl_signal = pyqtSignal(float)

    version = '1.0.1'

    lowpass_filter_risetime = 0.6  # s, depends on the timeconstant of the low pass filter
    shutdown_threshold = 2.95  # Vl
    osc_refresh_delay = 100  # ms
    log_update_interval = 200  # ms
    spec_refresh_delay = 1000  # ms
    move_delay = 0.2  # s, additional delay after changing wavelength

    # A warning is printed if one value of lp_theta_std is below the threshold
    # as this indicates the presence of linear polarization in the emission
    lp_theta_std_warning_threshold = 1.0

    input_ranges = ['0.003', '0.010', '0.030', '0.100', '0.300', '1.000', '3.000']

    log_name = 'CTRL'
    acquisition_running = False

    # Parameters to calculate approx. gain from control voltage of PMT, log(gain) = slope*pmt_voltage + offset,
    # derived from manual
    pmt_slope = 4.913
    pmt_offset = 1.222
    max_gain = 885.6
    gain_norm = 4775.0

    max_volt_hist_length = 75  # number of data points in the signal tuning graph
    edt_changed_color = '#FFFF80'

    curr_spec = np.array([[],  # wavelength
                          [],  # DC
                          [],  # DC stddev
                          [],  # CD
                          [],  # CD stddev
                          [],  # I_L
                          [],  # I_L stddev
                          [],  # I_R
                          [],  # I_R stddev
                          [],  # g_abs
                          [],  # g_abs stddev
                          [],  # ld
                          [],  # ld stddev
                          [],  # molar_ellip
                          [],  # molar_ellip stddev
                          [],  # ellip
                          []])  # ellip stddev
    index_ac = 3  # in curr_spec
    index_dc = 1
    index_gabs = 9
    index_ellips = 14

    # averaged spectrum during measurement
    avg_spec = np.array([[],  # wavelenght
                         [],  # DC
                         [],  # AC
                         [],  # gabs
                         []])  # ellips

    # variables required for phase offset calibration
    cal_running = False
    cal_collecting = False
    cal_new_value = 0.0
    cal_theta_thread = None
    initialized = False
    log_signal = pyqtSignal(str)

    # ---Start of initialization/closing section---

    def __init__(self):
        super().__init__(log_name='CTRL')

        # Create window
        self.gui = gui.Ui_MainWindow()
        self.gui.setupUi(self)
        self.gui.closeSignal.connect(self.on_closing)
        self.pem_lock = th.Lock()
        self.monoi_lock = th.Lock()
        self.monoii_lock = th.Lock()
        self.lockin_daq_lock = th.Lock()
        self.lockin_osc_lock = th.Lock()

        # This trigger to stop spectra acquisition is a list to pass it by reference to the read_data thread
        self.stop_spec_trigger = [False]
        # For oscilloscope monitoring
        self.stop_osc_trigger = False
        # For phase offset calibration
        self.stop_cal_trigger = [False]
        self.spec_thread = None

        self.log_queue = queue.Queue()
        self.assign_gui_events()

        if os.path.exists("last_params.txt"):
            self.load_last_settings()

        self.set_acquisition_running(False)

        self.log_update_interval = 100
        self.log_signal.connect(self.gui.append_to_log)
        self.log_author_message()
        self.update_log()

        # Create a QTimer for the log
        self.timer = QTimer()
        # noinspection PyUnresolvedReferences
        self.timer.timeout.connect(self.update_log)
        self.timer.start(self.log_update_interval)

        self.timer = QTimer()
        self.timer.timeout.connect(self.cal_end_after_thread)
        # self.update_mono_edt_lbl_signal.connect(self.gui.update_mono_edt_lbl_slot)


    def set_initialized(self, init):
        self.initialized = init

        if self.initialized:
            self.gui.btn_init.setEnabled(False)  # disable button
            self.gui.btn_close.setEnabled(True)  # enable button
            self.gui.signaltuning_group.setEnabled(True)
            self.gui.spectrasetup_group.setEnabled(True)
            self.gui.spectra_group.setEnabled(True)
        else:
            self.gui.btn_init.setEnabled(True)  # enable button
            self.gui.btn_close.setEnabled(False)  # disable button
            self.gui.signaltuning_group.setEnabled(False)
            self.gui.spectrasetup_group.setEnabled(False)
            self.gui.spectra_group.setEnabled(False)

    def load_last_settings(self):
        def re_search(key, text):
            res = re.search(key, text)
            if res is None:
                return ''
            else:
                return res.group(1)

        with open('last_params.txt', 'r') as f:
            s = f.read()

        keywords = [r'Spectra Name = (.*)\n',
                    r'Start WL = ([0-9\.]*) nm\n',
                    r'End WL = ([0-9\.]*) nm\n',
                    r'Step = ([0-9\.]*) nm\n',
                    r'Dwell time = ([0-9\.]*) s\n',
                    r'Repetitions = ([0-9]*)\n',
                    r'Exc. WL = ([0-9\.]*) nm\n',
                    r'Comment = (.*)\n',
                    r'AC-Blank-File = (.*)\n',
                    r'Phase offset = ([0-9\.]*) deg',
                    r'DC-Blank-File = (.*)\n',
                    r'Detector Correction File = (.*)\n']

        edts = [self.gui.edt_filename,
                self.gui.edt_start,
                self.gui.edt_end,
                self.gui.edt_step,
                self.gui.edt_dwell,
                self.gui.edt_rep,
                self.gui.edt_excWL,
                self.gui.edt_comment,
                self.gui.edt_ac_blank,
                self.gui.edt_phaseoffset,
                self.gui.edt_dc_blank,
                self.gui.edt_det_corr
                ]

        for i in range(0, len(keywords)):
            val = re_search(keywords[i], s)
            if val != '':
                edts[i].setText(val)

        blank = re_search('PEM off = ([01])\n', s)
        self.gui.var_pem_off.setChecked(blank == '1')

        input_range = re_search('Input range = ([0-9\.]*)\n', s)
        index = self.gui.cbx_range.findText(input_range)
        if index >= 0:
            self.gui.cbx_range.setCurrentIndex(index)

    def set_acquisition_running(self, b):
        self.acquisition_running = b
        if self.initialized:
            self.set_active_components()

    def init_devices(self):
        try:
            rm_pem = pyvisa.ResourceManager()
            self.log('Available COM devices: {}'.format(rm_pem.list_resources()))
            self.log('Initialize PEM-200...')
            QtWidgets.QApplication.processEvents()

            self.pem_lock.acquire()
            self.pem = PEM(logObject=self, log_name='PEM')
            QtWidgets.QApplication.processEvents()
            b1 = self.pem.initialize(rm_pem, self.log_queue)
            self.pem_lock.release()
            QtWidgets.QApplication.processEvents()
            self.log('')

            if b1:
                self.log('Initialize monochromator SP-2155...')
                rm_mono = pyvisa.ResourceManager()
                QtWidgets.QApplication.processEvents()
                self.monoi_lock.acquire()
                self.monoi = Monoi(logObject=self, log_name='MONOI')
                QtWidgets.QApplication.processEvents()
                b2 = self.monoi.initialize(rm_mono, self.log_queue)
                self.monoi_lock.release()
                QtWidgets.QApplication.processEvents()
                self.log('')

                if b2:
                    self.log('Initialize monochromator SP-2155...')
                    rm_mono = pyvisa.ResourceManager()
                    QtWidgets.QApplication.processEvents()
                    self.monoii_lock.acquire()
                    self.monoii = Monoii(logObject=self, log_name='MONOII')
                    QtWidgets.QApplication.processEvents()
                    b3 = self.monoii.initialize(rm_mono, self.log_queue)
                    self.monoii_lock.release()
                    QtWidgets.QApplication.processEvents()
                    self.log('')

                    if b3:
                        self.log('Initialize lock-in amplifier MFLI for data acquisition...')
                        QtWidgets.QApplication.processEvents()
                        self.lockin_daq_lock.acquire()
                        self.lockin_daq = MFLI('dev7024', 'LID', self.log_queue, logObject=self)
                        QtWidgets.QApplication.processEvents()
                        b4 = self.lockin_daq.connect()
                        QtWidgets.QApplication.processEvents()
                        b4 = b4 and self.lockin_daq.setup_for_daq(self.pem.bessel_corr, self.pem.bessel_corr_lp)
                        self.update_PMT_voltage_edt(self.lockin_daq.pmt_volt)
                        self.lockin_daq_lock.release()
                        self.set_phaseoffset_from_edt()
                        QtWidgets.QApplication.processEvents()
                        self.log('')

                        if b4:
                            self.log('Initialize lock-in amplifier MFLI for oscilloscope monitoring...')
                            QtWidgets.QApplication.processEvents()
                            self.lockin_osc_lock.acquire()
                            self.lockin_osc = MFLI('dev7024', 'LIA', self.log_queue, logObject=self)
                            QtWidgets.QApplication.processEvents()
                            b5 = self.lockin_osc.connect()
                            QtWidgets.QApplication.processEvents()
                            b5 = b5 and self.lockin_osc.setup_for_scope()
                            self.lockin_osc_lock.release()
                            self.max_volt_history = collections.deque(maxlen=self.max_volt_hist_length)
                            self.osc_refresh_delay = 100  # ms
                            self.stop_osc_trigger = False
                            self.start_osc_monit()

                            if b5:
                                self.set_initialized(True)
                                self.movei_nm(1000)
                                self.moveii_nm(1000)
                                QtWidgets.QApplication.processEvents()
                                self.log('')
                                self.log('Initialization complete!')

        except Exception as e:
            self.set_initialized(False)
            self.log('ERROR during initialization: {}!'.format(str(e)), True)

    def disconnect_devices(self):
        self.log('')
        self.log('Closing connections to devices...')
        self.set_PMT_voltage(0.0)

        # stop everything
        self.stop_osc_trigger = True
        self.stop_spec_trigger[0] = True
        self.stop_cal_trigger[0] = True
        # wait for threads to end
        time.sleep(0.5)
        try:
            self.pem.close()
            self.monoi.close()
            self.monoii.close()
            self.lockin_daq.disconnect()
            self.lockin_osc.disconnect()
            self.log('Connections closed.')
            self.set_initialized(False)
        except Exception as e:
            self.log('Error while closing connections: {}.'.format(str(e)), True)

    def on_closing(self):
        # Here, you'll do everything that needs to be done before the window is actually closed

        if self.spec_thread is not None:
            if self.spec_thread.is_alive():
                self.abort_measurement()
                time.sleep(1)

        if self.cal_theta_thread is not None:
            if self.cal_theta_thread.is_alive():
                self.cal_stop_record()
                time.sleep(1)

        self.save_params('last')

        if self.initialized:
            self.disconnect_devices()

        # After completing all the tasks, exit the application
        QCoreApplication.instance().quit()

    # --- Start of GUI section---

    def log_author_message(self):
        self.log('CD-PLOT v{}'.format(self.version), False, True)
        self.log('Author: Langelihle (Langa) Siziba', False, True)
        self.log('https://github.com/wkitzmann/CatCPL/', False, True)  # TODO: copy and paste the github link
        self.log(
            'CD-PLOT is distributed under the GNU General Public License 3.0 ('
            'https://www.gnu.org/licenses/gpl-3.0.html).',
            False, True)
        self.log('Cite XX', False, True)

    def assign_gui_events(self):
        # Device Setup
        self.gui.btn_init.clicked.connect(self.click_init)
        self.gui.btn_close.clicked.connect(self.disconnect_devices)

        # Signal tuning
        # Signal tuning
        self.gui.btn_set_PMT.clicked.connect(self.click_set_pmt)
        self.gui.edt_pmt.textChanged.connect(lambda: self.edt_changed(self.gui.edt_pmt))
        self.gui.edt_pmt.returnPressed.connect(self.enter_pmt)

        self.gui.btn_set_gain.clicked.connect(self.click_set_gain)
        self.gui.edt_gain.textChanged.connect(lambda: self.edt_changed(self.gui.edt_gain))
        self.gui.edt_gain.returnPressed.connect(self.enter_gain)

        self.gui.btn_set_WL.clicked.connect(self.click_set_signal_WL)
        self.gui.edt_WL.textChanged.connect(lambda: self.edt_changed(self.gui.edt_WL))
        self.gui.edt_WL.returnPressed.connect(self.enter_signal_WL)

        self.gui.btn_set_phaseoffset.clicked.connect(self.click_set_phaseoffset)
        self.gui.edt_phaseoffset.textChanged.connect(lambda: self.edt_changed(self.gui.edt_phaseoffset))
        self.gui.edt_phaseoffset.returnPressed.connect(self.enter_phaseoffset)

        self.gui.cbx_range.currentIndexChanged.connect(self.change_cbx_range)
        self.gui.btn_autorange.clicked.connect(self.click_autorange)

        self.gui.btn_cal_phaseoffset.clicked.connect(self.click_cal_phaseoffset)

        # Spectra Setup
        self.gui.btn_start.clicked.connect(self.click_start_spec)
        self.gui.btn_abort.clicked.connect(self.click_abort_spec)

        # Close event
        self.gui.closeEvent = self.on_closing

    # (de)activate buttons and text components depending on the state of the software
    def set_active_components(self):
        self.gui.btn_init.setEnabled(not self.initialized)
        self.gui.btn_close.setEnabled(self.initialized)
        self.gui.spectrasetup_group.setEnabled(
            not self.acquisition_running and self.initialized and not self.cal_running)
        self.gui.signaltuning_group.setEnabled(
            not self.acquisition_running and self.initialized and not self.cal_collecting)
        self.gui.btn_start.setEnabled(not self.acquisition_running and self.initialized and not self.cal_running)
        self.gui.btn_abort.setEnabled(self.acquisition_running and self.initialized and not self.cal_running)
        self.gui.btn_cal_phaseoffset.setEnabled(
            not self.acquisition_running and self.initialized and not self.cal_running)
        self.update_mfli_status(self.initialized)

    def window_update(self):
        QApplication.processEvents()

    def update_log(self):
        # Handle all log messages currently in the queue, if any
        while not self.log_queue.empty():
            try:
                msg = self.log_queue.get(False)
                self.gui.append_to_log(msg)  # Let append_to_log handle the log update
            except queue.Empty:
                pass

    # When the user changes a value in one of the text boxes in the Signal Tuning area
    # the text box is highlighed until the value is saved
    def edt_changed(self, edt):
        palette = QPalette()
        palette.setColor(QPalette.Base, QColor(self.edt_changed_color))
        edt.setPalette(palette)

    def set_PMT_volt_from_edt(self):
        try:
            v = float(self.gui.edt_pmt.text())
            if 0.0 <= v <= 1.1:
                self.set_PMT_voltage(v)
        except ValueError as e:
            self.log(f'Error in set_PMT_voltage_from_edt: {e}', True)

    def set_gain_from_edt(self):
        try:
            g = float(self.gui.edt_gain.text())
            if g <= self.max_gain:
                self.set_PMT_voltage(self.gain_to_volt(g))
        except ValueError as e:
            self.log(f'Error in set_gain_from_edt: {e}', True)

    def set_WL_from_edt(self):
        try:
            nm = float(self.gui.edt_WL.text())
            self.movei_nm(nm)
            self.movei_nm(nm)
        except ValueError as e:
            self.log(f'Error in set_WL_from_edt: {e}', True)

    def set_phaseoffset_from_edt(self):
        try:
            po_text = self.gui.edt_phaseoffset.text()
            po = float(po_text) if po_text else 0
            self.set_phaseoffset(po)
            self.gui.edt_phaseoffset.setStyleSheet("background-color: #FFFFFF")
        except ValueError as e:
            self.log(f'Error in set_phaseoffset_from_edt: {e}', True)

    def click_init(self):
        # deactivate init button
        self.gui.btn_init.setEnabled(False)
        self.init_devices()

    def click_set_pmt(self):
        self.set_PMT_volt_from_edt()

    def enter_pmt(self):
        self.click_set_pmt()

    def click_set_gain(self):
        self.set_gain_from_edt()

    def enter_gain(self):
        self.click_set_gain()

    def click_set_signal_WL(self):
        self.set_WL_from_edt()

    def enter_signal_WL(self):
        self.click_set_signal_WL()

    def change_cbx_range(self):
        self.set_input_range(float(self.gui.cbx_range.currentText()))

    def click_autorange(self):
        self.set_auto_range()

    def click_set_phaseoffset(self):
        self.set_phaseoffset_from_edt()

    def enter_phaseoffset(self):
        self.click_set_phaseoffset()

    def click_cal_phaseoffset(self):
        self.cal_phaseoffset_start()

    def click_start_spec(self):
        self.start_spec()

    def click_abort_spec(self):
        self.abort_measurement()

    def update_phaseoffset_edt(self, value: float):
        self.gui.edt_phaseoffset.setText('{:.3f}'.format(value))

    def update_progress_bar(self, start: float, stop: float, curr: float, run: int, run_count: int,
                            time_since_start: float):
        # Calculate progress in percent
        if stop > start:
            f = (1 - (stop - curr) / (stop - start)) * 100
        else:
            f = (1 - (curr - stop) / (start - stop)) * 100

        # Remaining time is estimated from progress+passed time
        time_left = 0
        if f > 0:
            time_left = (run_count * 100 / (f + 100 * (run - 1)) - 1) * time_since_start

        # Determine proper way to display the estimated remaining time
        if time_left < 60:
            unit = 's'
        elif time_left < 3600:
            unit = 'min'
            time_left = time_left / 60
        else:
            unit = 'h'
            time_left = time_left / 3600

        # Update progress bar value
        self.gui.progressBar.setValue(int(round(f)))

        # Update label text
        self.gui.progressBar.setToolTip(
            '{:.1f} % ({:d}/{:d}), ca. {:.1f} {}'.format(f, run, run_count, time_left, unit))

    def update_mfli_status(self, b: bool):
        if b:
            self.gui.txt_mfli.setText('connected')
        else:
            self.gui.txt_mfli.setText('-')

    def update_osc_captions(self, curr: float, label):
        # setting a breakpoint here

        if not np.isnan(curr):
            label.setText('{:.1e} V'.format(curr))  # update QLabel text

    def update_osc_plots(self, max_vals):

        # start a QTimer to call the plot function at intervals
        self.timer = QTimer()
        self.timer.timeout.connect(lambda: self.gui.plot_osc(
            data_max=max_vals,
            max_len=self.max_volt_hist_length,
            time_step=self.osc_refresh_delay
        ))
        self.timer.start(self.osc_refresh_delay)  # start timer

    def update_PMT_voltage_edt(self, volt):
        self.gui.edt_pmt.setText('{:.3f}'.format(volt))
        self.gui.edt_gain.setText('{:.3f}'.format(self.volt_to_gain(volt)))
        self.gui.edt_pmt.setStyleSheet('background-color: #FFFFFF;')
        self.gui.edt_gain.setStyleSheet('background-color: #FFFFFF;')
        self.window_update()  # Adjusted this method for PyQt

    # def update_mono_edt_lbl(self, wl):
    #     self.gui.txt_monoi.setText('{:.2f} nm'.format(wl))
    #     self.gui.txt_monoii.setText('{:.2f} nm'.format(wl))
    #     self.gui.edt_WL.setText('{:.2f}'.format(wl))

    def update_pem_lbl(self, wl):
        self.gui.txt_PEM.setText('{:.2f} nm'.format(wl))


    def update_spec(self):
        if self.acquisition_running:
            self.gui.plot_spec(self.gui.gabs_fig, self.gui.gabs_canvas, self.gui.gabs_ax,
                               gabs=[self.curr_spec[0], self.curr_spec[self.index_gabs]],
                               gabs_avg=[self.avg_spec[0], self.avg_spec[3]],
                               title='Gabs')

            self.gui.plot_spec(self.gui.cd_fig, self.gui.cd_canvas, self.gui.cd_ax,
                               cd=[self.curr_spec[0], self.curr_spec[self.index_ac]],
                               cd_avg=[self.avg_spec[0], self.avg_spec[2]],
                               title='CD')

            self.gui.plot_spec(self.gui.ld_fig, self.gui.ld_canvas, self.gui.ld_ax,
                               tot=[self.curr_spec[0], self.curr_spec[self.index_dc]],
                               tot_avg=[self.avg_spec[0], self.avg_spec[1]],
                               title='DC')

            self.gui.plot_spec(self.gui.ellips_fig, self.gui.ellips_canvas, self.gui.ellips_ax,
                               ellips=[self.curr_spec[0], self.curr_spec[self.index_ellips]],
                               ellips_avg=[self.avg_spec[0], self.avg_spec[4]],
                               title='Ellips')

        if not self.spec_thread is None:
            if self.spec_thread.is_alive():
                QTimer.singleShot(self.spec_refresh_delay, self.update_spec)

                # ----End of GUI section---

    # ---Start of spectra acquisition section---

    def start_spec(self):

        def filename_exists_or_empty(name: str) -> bool:
            if name == '':
                return True
            else:
                return os.path.exists(".\\data\\" + name + ".csv")

        def check_illegal_chars(s):
            result = False
            for c in s:
                if c in '#@$%^&*{}:;"|<>/?\`~' + "'":
                    result = True
                    break
            return result

        ac_blank = self.gui.edt_ac_blank.text()
        dc_blank = self.gui.edt_dc_blank.text()
        det_corr = self.gui.edt_det_corr.text()
        filename = self.gui.edt_filename.text()
        reps = int(self.gui.edt_rep.text())

        ac_blank_exists = filename_exists_or_empty(ac_blank)
        dc_blank_exists = filename_exists_or_empty(dc_blank)
        det_corr_exists = filename_exists_or_empty(det_corr)

        if not check_illegal_chars(filename):
            try:
                if reps == 1:
                    s = ''
                else:
                    s = '_1'
                filename_exists = filename_exists_or_empty(filename + s)

                error = not ac_blank_exists or not dc_blank_exists or not det_corr_exists or filename_exists

                if not error:
                    self.stop_spec_trigger[0] = False

                    self.set_acquisition_running(True)

                    self.spec_thread = th.Thread(target=self.record_spec, args=(
                        float(self.gui.edt_start.text()),
                        float(self.gui.edt_end.text()),
                        float(self.gui.edt_step.text()),
                        float(self.gui.edt_dwell.text()),
                        reps,
                        filename,
                        ac_blank,
                        dc_blank,
                        det_corr,
                        self.gui.var_pem_off.isChecked()))
                    self.spec_thread.start()
                    self.update_spec()
                else:
                    if not ac_blank_exists:
                        self.log('Error: AC-blank file does not exist!', True)
                    if not dc_blank_exists:
                        self.log('Error: DC-blank file does not exist!', True)
                    if not det_corr_exists:
                        self.log('Error: Detector correction file does not exist!', True)
                    if filename_exists:
                        self.log('Error: Spectra filename {} already exists!'.format(filename + s), True)
            except Exception as e:
                self.log('Error in click_start_spec: ' + str(e), True)
        else:
            self.log('Error: Filename contains one of these illegal characters: ' + '#@$%^&*{}:;"|<>/?\`~' + "'")

    # will be executed in separate thread
    def record_spec(self, start_nm: float, end_nm: float, step: float, dwell_time: float, reps: int, filename: str,
                    ac_blank: str, dc_blank: str, det_corr: str, pem_off: int):

        global data

        # try:
        self.log('')
        self.log('Spectra acquisition: {:.2f} to {:.2f} nm with {:.2f} nm steps and {:.3f} s per step'.format(start_nm,
                                                                                                              end_nm,
                                                                                                              step,
                                                                                                              dwell_time))

        self.log('Starting data acquisition.')

        self.lockin_daq_lock.acquire()
        self.lockin_daq.set_dwell_time(dwell_time)
        self.lockin_daq_lock.release()

        # wait for MFLI buffer to be ready
        self.interruptable_sleep(dwell_time)

        # array of pandas dataframes with all spectral data
        dfall_spectra = np.empty(reps, dtype=object)
        # avg_spec is used to display the averaged spectrum during the measurement
        self.avg_spec = np.array([[],  # wavelength
                                  [],  # DC
                                  [],  # AC
                                  [],  # gabs
                                  []])  # ellips

        correction = ac_blank != '' or dc_blank != '' or det_corr != ''

        if start_nm > end_nm:
            inc = -step
        else:
            inc = step
        direction = np.sign(inc)

        self.update_progress_bar(0, 1, 0, 1, reps, 0)

        # Disable PEM for AC background measurement
        self.set_modulation_active(pem_off == 0)

        time_since_start = -1.0
        t0 = time.time()

        i = 0
        while (i < reps) and not self.stop_spec_trigger[0]:
            self.log('')
            self.log('Run {}/{}'.format(i + 1, reps))

            self.curr_spec = np.array(([[],  # wavelength
                                        [],  # DC
                                        [],  # DC stddev
                                        [],  # CD
                                        [],  # CD stddev
                                        [],  # I_L
                                        [],  # I_L stddev
                                        [],  # I_R
                                        [],  # I_R stddev
                                        [],  # g_abs
                                        [],  # g_abs stddev
                                        [],  # ld
                                        [],  # ld stddev
                                        [],  # molar_ellip
                                        [],  # molar_ellip stddev
                                        [],  # ellip
                                        []]))  # ellip stddev

            # self.log('start {}'.format(time.time()-t0))
            curr_nm = start_nm - inc
            while ((((direction > 0) and (curr_nm < end_nm)) or ((direction < 0) and (curr_nm > end_nm)))
                   and not self.stop_spec_trigger[0]):

                curr_nm = curr_nm + inc
                # self.log('before move {:.3f}'.format(time.time()-t0))
                self.movei_nm(curr_nm, pem_off == 0)
                self.moveii_nm(curr_nm, pem_off == 0)

                # self.log('after move {:.3f}'.format(time.time()-t0))

                self.interruptable_sleep(self.lowpass_filter_risetime)
                # self.log('afer risetime {:.3f}'.format(time.time()-t0))

                # try three times to get a successful measurement
                j = 0
                success = False
                # Try 5 times to get a valid dataset from the MFLI
                while (j < 5) and not success and not self.stop_spec_trigger[0]:
                    # self.log('before acquire {:.3f}'.format(time.time()-t0))
                    self.lockin_daq_lock.acquire()
                    # self.log('after lock {:.3f}'.format(time.time()-t0))
                    data = self.lockin_daq.read_data(self.stop_spec_trigger)
                    # self.log('after read {:.3f}'.format(time.time()-t0))
                    self.lockin_daq_lock.release()

                    if not self.stop_spec_trigger[0]:
                        # self.log('afeter release {:.3f}'.format(time.time()-t0))
                        success = data['success']
                    j += 1

                if not success and not self.stop_spec_trigger[0]:
                    self.stop_spec_trigger[0] = True
                    self.log('Could not collect data after 5 tries, aborting...', True)

                if not self.stop_spec_trigger[0]:
                    # add current wavelength to dataset
                    data_with_WL = np.array([np.concatenate(([curr_nm], data['data']))])
                    # add dataset to current spectrum
                    self.curr_spec = np.hstack((self.curr_spec, data_with_WL.T))
                    if reps > 1:
                        self.add_data_to_avg_spec(data_with_WL, i)

                time_since_start = time.time() - t0
                self.update_progress_bar(start_nm, end_nm, curr_nm, i + 1, reps, time_since_start)
                # self.log('before next step {:.3f}'.format(time.time()-t0))

            if self.stop_spec_trigger[0]:
                self.set_PMT_voltage(0.0)

            self.log('This scan took {:.0f} s.'.format(time_since_start))

            # process spectra as dataframes (df)
            dfcurr_spec = self.np_to_pd(self.curr_spec)
            if reps > 1:
                index_str = '_' + str(i + 1)
            else:
                index_str = ''
            self.save_spec(dfcurr_spec, filename + index_str)

            if correction:
                dfcurr_spec_corr = self.apply_corr(dfcurr_spec, ac_blank, dc_blank, det_corr)
                self.save_spec(dfcurr_spec_corr, filename + index_str + '_corr', False)

            dfall_spectra[i] = dfcurr_spec

            i += 1

        self.log('Stopping data acquisition.')
        self.set_acquisition_running(False)

        # averaging and correction of the averaged spectrum
        if reps > 1 and not self.stop_spec_trigger[0]:
            dfavg_spec = self.df_average_spectra(dfall_spectra)
            self.save_spec(dfavg_spec, filename + '_avg', False)

            if correction:
                dfavg_spec_corr = self.apply_corr(dfavg_spec, ac_blank, dc_blank, det_corr)
                self.save_spec(dfavg_spec_corr, filename + '_avg_corr', False)

        self.log('')
        self.log('Returning to start wavelength')
        self.set_modulation_active(True)

        self.movei_nm(start_nm, move_pem=False)
        self.moveii_nm(start_nm, move_pem=True)

        self.stop_spec_trigger[0] = False
        # except Exception as e:
        # self.log("Error in record_spec: {}".format(str(e)))

    def interruptable_sleep(self, t: float):
        start = time.time()
        while (time.time() - start < t) and not self.stop_spec_trigger[0]:
            time.sleep(0.01)

    def add_data_to_avg_spec(self, data, curr_rep: int):
        # avg_spec structure: [[WL],[DC],[AC],[gabs],[ellips]]
        if curr_rep == 0:
            self.avg_spec = np.hstack((self.avg_spec, np.array(
                ([data[0][0]], [data[0][self.index_dc]], [data[0][self.index_ac]], [data[0][self.index_gabs]],
                 [data[0][self.index_ellips]]))))
        else:
            # find index where the wavelength of the new datapoint matches
            index = np.where(self.avg_spec[0] == data[0][0])[0]
            if len(index) > 0:
                # reaverage DC and AC
                self.avg_spec[1][index[0]] = (self.avg_spec[1][index[0]] * curr_rep + data[0][self.index_dc]) / (
                        curr_rep + 1)
                self.avg_spec[2][index[0]] = (self.avg_spec[2][index[0]] * curr_rep + data[0][self.index_ac]) / (
                        curr_rep + 1)
                # recalculate gabs #TODO
                self.avg_spec[3][index[0]] = 2 * self.avg_spec[2][index[0]] / self.avg_spec[1][index[0]]

                # recalculate ellips #TODO
                self.avg_spec[4][index[0]] = 2 * self.avg_spec[2][index[0]] / self.avg_spec[2][index[0]]

                # converts a numpy array to a pandas DataFrame

    def np_to_pd(self, spec):
        df = pd.DataFrame(spec.T)
        df.columns = ['WL', 'DC', 'DC_std', 'AC', 'AC_std', 'I_L', 'I_L_std', 'I_R', 'I_R_std', 'gabs', 'gabs_std',
                      'ld', 'ld_std', 'ellip', 'ellip', 'molar_ellip', 'molar_ellip']
        df = df.set_index('WL')
        return df

    def df_average_spectra(self, dfspectra):
        self.log('')
        self.log('Averaging...')
        # create a copy of the Dataframe structure of a spectrum filled with zeros
        dfavg = dfspectra[0].copy()
        dfavg.iloc[:, :] = 0.0

        count = len(dfspectra)
        # The error of the averaged spectrum is estimated using Gaussian propagation of uncertainty
        for i in range(0, count):
            dfavg['DC'] = dfavg['DC'] + dfspectra[i]['DC'] / count
            dfavg['DC_std'] = dfavg['DC_std'] + (dfspectra[i]['DC_std'] / count) ** 2
            dfavg['AC'] = dfavg['AC'] + dfspectra[i]['AC'] / count
            dfavg['AC_std'] = dfavg['AC_std'] + (dfspectra[i]['AC_std'] / count) ** 2
            dfavg['ld'] = dfavg['ld'] + dfspectra[i]['ld'] / count
            dfavg['ld_std'] = dfavg['ld_std'] + (dfspectra[i]['ld_std'] / count) ** 2
            dfavg['mollar_ellips'] = dfavg['mollar_ellips'] + dfspectra[i]['mollar_ellips'] / count
            dfavg['molar_ellips_std'] = dfavg['molar_ellips_std'] + (dfspectra[i]['molar_ellips_std'] / count) ** 2
            dfavg['ellips'] = dfavg['ellips'] + dfspectra[i]['ellips'] / count
            dfavg['ellips_std'] = dfavg['ellips_std'] + (dfspectra[i]['ellips_std'] / count) ** 2
        dfavg['AC_std'] = dfavg['AC_std'] ** (0.5)
        dfavg['DC_std'] = dfavg['DC_std'] ** (0.5)
        dfavg['ld_std'] = dfavg['ld_std'] ** (0.5)
        dfavg['molar_ellips_std'] = dfavg['molar_ellips_std'] ** (0.5)
        dfavg['ellips_std'] = dfavg['ellips_std'] ** (0.5)

        dfavg = self.calc_cd(dfavg)

        return dfavg

    def apply_corr(self, dfspec: pd.DataFrame, ac_blank: str, dc_blank: str, det_corr: str):

        # Gives True if wavelength region is suitable
        def is_suitable(df_corr: pd.DataFrame, check_index: bool) -> bool:
            first_WL_spec = dfspec.index[0]
            last_WL_spec = dfspec.index[-1]

            first_WL_corr = df_corr.index[0]
            last_WL_corr = df_corr.index[-1]

            # Check if the wavelength region in dfspec is covered by df_det_corr
            WL_region_ok = min(first_WL_spec, last_WL_spec) >= min(first_WL_corr, last_WL_corr) and \
                           max(first_WL_spec, last_WL_spec) <= max(first_WL_corr, last_WL_corr)
            # Check if the measured wavelength values are available in the correction file (for AC and DC without
            # interpolation)
            values_ok = not check_index or dfspec.index.isin(df_corr.index).all()

            return WL_region_ok and values_ok

        # Interpolate the detector correction values to match the measured wavelength values
        def interpolate_detcorr():
            # Create a copy of the measured wavelengths and fill it with NaNs
            dfspec_nan = pd.DataFrame()
            dfspec_nan['nan'] = dfspec['AC'].copy()
            dfspec_nan.iloc[:, 0] = float('NaN')

            nonlocal df_det_corr
            # Add the measured wavelengths to the correction data, missing values in the correction data will be set
            # to NaN
            df_det_corr = pd.concat([df_det_corr, dfspec_nan], axis=1).drop('nan', axis=1)
            # Interpolate missing values in the correction data
            df_det_corr = df_det_corr.interpolate(method='index')
            # Limit WL values of correction data to measured wavelengths
            df_det_corr = df_det_corr.filter(items=dfspec_nan.index, axis=0)

        self.log('')
        self.log('Baseline correction...')

        # Correction for detector sensitivity
        # Todo global data path
        if det_corr != '':
            self.log('Detector sensitivity correction with {}'.format(".\\data\\" + det_corr + ".csv"))
            df_det_corr = pd.read_csv(filepath_or_buffer=".\\data\\" + det_corr + ".csv", sep=',', index_col='WL')

            if is_suitable(df_det_corr, False):
                interpolate_detcorr()
                dfspec['DC'] = dfspec['DC'] / df_det_corr.iloc[:, 0]
                dfspec['DC_std'] = dfspec['DC_std'] / df_det_corr.iloc[:, 0]
                dfspec['AC'] = dfspec['AC'] / df_det_corr.iloc[:, 0]
                dfspec['AC_std'] = dfspec['AC_std'] / df_det_corr.iloc[:, 0]
            else:
                self.log('Detector correction file does not cover the measured wavelength range!', True)

        # AC baseline correction
        if ac_blank != '':
            self.log('AC blank correction with {}'.format(".\\data\\" + ac_blank + ".csv"))
            df_ac_blank = pd.read_csv(filepath_or_buffer=".\\data\\" + ac_blank + ".csv", sep=',', index_col='WL')

            if is_suitable(df_ac_blank, True):
                dfspec['AC'] = dfspec['AC'] - df_ac_blank['AC']
                dfspec['AC_std'] = ((dfspec['AC_std'] / 2) ** 2 + (df_ac_blank['AC_std'] / 2) ** 2) ** 0.5
            else:
                self.log('AC blank correction file does not contain the measured wavelengths!', True)

                # DC baseline correction
        if dc_blank != '':
            self.log('DC blank correction with {}'.format(".\\data\\" + dc_blank + ".csv"))
            df_dc_blank = pd.read_csv(filepath_or_buffer=".\\data\\" + dc_blank + ".csv", sep=',', index_col='WL')

            if is_suitable(df_dc_blank, True):
                dfspec['DC'] = dfspec['DC'] - df_dc_blank['DC']
                dfspec['DC_std'] = ((dfspec['DC_std'] / 2) ** 2 + (df_dc_blank['DC_std'] / 2) ** 2) ** 0.5
            else:
                self.log('DC blank correction file does not contain the measured wavelengths!', True)

                # If there are wavelength values in the blankfiles that are not in dfspec this will give NaN values
        # Drop all rows that contain NaN values
        # The user must make sure that the blank files contain the correct values for the measurement
        dfspec = dfspec.dropna(axis=0)

        dfspec = self.calc_cd(dfspec)
        return dfspec

    def calc_cd(self, df):
        df['I_L'] = (df['AC'] + df['DC'])
        df['I_R'] = (df['DC'] - df['AC'])
        df['gabs'] = (df['I_L'] - df['I_R']) / (df['I_L'] - df['I_R'])
        # Gaussian error progression
        df['I_L_std'] = ((df['AC_std']) ** 2 + (df['DC_std']) ** 2) ** 0.5
        df['I_R_std'] = df['I_L_std'].copy()
        df['gabs_std'] = ((4 * df['I_R'] ** 2 / (df['I_L'] + df['I_R']) ** 4) * df['I_L_std'] ** 2
                          + (4 * df['I_L'] ** 2 / (df['I_L'] + df['I_R']) ** 4) * df['I_R_std'] ** 2) ** 0.5

        return df

    def save_spec(self, dfspec, filename, savefig=True):
        dfspec.to_csv(".\\data\\" + filename + '.csv', index=True)
        self.log('Data saved as: {}'.format(".\\data\\" + filename + '.csv'))
        self.save_params(".\\data\\" + filename)
        if savefig:
            self.gui.spec_fig.savefig(".\\data\\" + filename + '.png')
            self.log('Figure saved as: {}'.format(".\\data\\" + filename + '.png'))

    def save_params(self, filename):
        with open(filename + '_params.txt', 'w') as f:
            f.write('Specta Name = {}\n'.format(self.gui.edt_filename.text()))
            f.write('Time = {}\n\n'.format(time.asctime(time.localtime(time.time()))))
            f.write('Setup parameters\n')
            f.write('Start WL = {} nm\n'.format(self.gui.edt_start.text()))
            f.write('End WL = {} nm\n'.format(self.gui.edt_end.text()))
            f.write('Step = {} nm\n'.format(self.gui.edt_step.text()))
            f.write('Dwell time = {} s\n'.format(self.gui.edt_dwell.text()))
            f.write('Repetitions = {}\n'.format(self.gui.edt_rep.text()))
            f.write('Exc. WL = {} nm\n'.format(self.gui.edt_excWL.text()))
            f.write('Comment = {}\n'.format(self.gui.edt_comment.text()))
            f.write('AC-Blank-File = {}\n'.format(self.gui.edt_ac_blank.text()))
            f.write('DC-Blank-File = {}\n'.format(self.gui.edt_dc_blank.text()))
            f.write('PEM off = {:d}\n'.format(self.gui.var_pem_off.isChecked()))
            f.write('Detector Correction File = {}\n'.format(self.gui.edt_det_corr.text()))
            f.write('PMT voltage = {} V\n'.format(self.gui.edt_pmt.text()))
            f.write('PMT gain = {}\n'.format(self.gui.edt_gain.text()))
            f.write('Input range = {}\n'.format(self.gui.cbx_range.currentText()))
            f.write('Phase offset = {} deg\n'.format(self.gui.edt_phaseoffset.text()))
        self.log('Parameters saved as: {}'.format(".\\data\\" + filename + '_params.txt'))

    def abort_measurement(self):
        self.log('')
        self.log('>>Aborting measurement<<')

        self.stop_spec_trigger[0] = True
        self.reactivate_after_abort()

    def reactivate_after_abort(self):
        if self.spec_thread is not None:
            if self.spec_thread.is_alive():
                QTimer.singleShot(500, self.reactivate_after_abort)  # QTimer.singleShot() accepts milliseconds
            else:
                self.set_acquisition_running(False)
        else:
            self.set_acquisition_running(False)

    # ---end of spectra acquisition section---

    # ---Control functions start---

    def set_modulation_active(self, b):
        # deactivating phase-locked loop on PEM reference in lock-in to retain last PEM frequency
        self.lockin_daq_lock.acquire()
        self.lockin_daq.set_extref_active(0, b)
        self.lockin_daq.daq.sync()
        self.lockin_daq_lock.release()

        # deactivating pem will cut off reference signal and modulation
        self.pem_lock.acquire()
        self.pem.set_active(b)
        self.pem_lock.release()
        if not b:
            self.gui.canvas.itemconfigure(self.gui.txt_PEM, text='off')

    def set_phaseoffset(self, value):
        if self.initialized:
            self.lockin_daq_lock.acquire()
            self.lockin_daq.set_phaseoffset(value)
            self.lockin_daq_lock.release()

    def movei_nm(self, nm, move_pem=True):

        self.log('')
        self.log('Move to {} nm'.format(nm))

        if self.initialized:
            # The WL changes in PEM and Monochromators are done in separate threads to save time
            monoi_thread = th.Thread(target=self.monoi_move, args=(nm,))
            monoi_thread.start()


            if move_pem:
                self.pem_lock.acquire()
                self.pem.set_nm(nm)
                self.pem_lock.release()
                self.update_pem_lbl(nm)

            while monoi_thread.is_alive():
                time.sleep(0.04)

            # self.update_mono_edt_lbl_signal.emit(nm)

            if self.acquisition_running:
                self.interruptable_sleep(self.move_delay)
            else:
                time.sleep(self.move_delay)
        else:
            self.log('Instruments not initialized!', True)

    def moveii_nm(self, nm, move_pem=True):

        self.log('')
        self.log('Move to {} nm'.format(nm))

        if self.initialized:
            # The WL changes in PEM and Monochromators are done in separate threads to save time
            monoii_thread = th.Thread(target=self.monoii_move, args=(nm,))
            monoii_thread.start()

            if move_pem:
                self.pem_lock.acquire()
                self.pem.set_nm(nm)
                self.pem_lock.release()
                self.update_pem_lbl(nm)

            while monoii_thread.is_alive():
                time.sleep(0.04)

            # self.update_mono_edt_lbl_signal.emit(nm)

            if self.acquisition_running:
                self.interruptable_sleep(self.move_delay)
            else:
                time.sleep(self.move_delay)
        else:
            self.log('Instruments not initialized!', True)

    def monoii_move(self, nm):

        self.monoii_lock.acquire()
        self.monoii.set_nm(nm)
        self.monoii_lock.release()

    def monoi_move(self, nm):

        self.monoi_lock.acquire()
        self.monoi.set_nm(nm)
        self.monoi_lock.release()

    def volt_to_gain(self, volt):
        return 10 ** (volt * self.pmt_slope + self.pmt_offset) / self.gain_norm

    def gain_to_volt(self, gain):
        if gain < 1.0:
            return 0.0
        elif gain >= self.max_gain:
            return 1.1
        else:
            return max(min((math.log10(gain * self.gain_norm) - self.pmt_offset) / self.pmt_slope, 1.1), 0.0)

    def set_PMT_voltage(self, volt):
        try:
            self.lockin_daq_lock.acquire()
            self.lockin_daq.set_PMT_voltage(volt, False)
            self.lockin_daq_lock.release()

            self.update_PMT_voltage_edt(volt)
        except Exception as e:
            self.log('Error in set_PMT_voltage: ' + str(e), True)

    def rescue_pmt(self):
        self.set_PMT_voltage(0.0)
        self.log('Signal ({:.2f} V) higher than threshold ({:.2f} V)!! '
                 'Setting PMT to 0 V'.format(self.max_volt, self.shutdown_threshold), True)


    def set_input_range(self, f):
        self.lockin_daq_lock.acquire()
        self.lockin_daq.set_input_range(f=f, auto=False)
        self.lockin_daq_lock.release()

    def set_auto_range(self):
        self.lockin_daq_lock.acquire()
        self.lockin_daq.set_input_range(f=0.0, auto=True)
        self.gui.cbx_range.setCurrentText('{:.3f}'.format(self.lockin_daq.signal_range))
        self.lockin_daq_lock.release()


    def set_phaseoffset(self, f):
        self.lockin_daq_lock.acquire()
        self.lockin_daq.set_phaseoffset(f)
        self.update_phaseoffset_edt(f)
        self.lockin_daq_lock.release()

        # ---control functions end---

    # ---oscilloscope section start---

    def start_osc_monit(self):
         # setting a breakpoint here

        self.stop_osc_trigger = False
        self.max_volt = 0.0
        self.avg_volt = 0.0

        self.lockin_osc_lock.acquire()
        self.lockin_osc.start_scope()
        self.lockin_osc_lock.release()
        self.monit_thread = th.Thread(target=self.monit_osc_loop)
        self.monit_thread.start()

        self.refresh_osc()

    def refresh_osc(self):

        self.update_osc_captions(self.max_volt, self.gui.txt_maxVolt)
        self.update_osc_captions(self.avg_volt, self.gui.txt_avgVolt)
        self.update_osc_plots(max_vals=np.asarray(self.max_volt_history))

        if self.monit_thread.is_alive():
            QTimer.singleShot(self.osc_refresh_delay, self.refresh_osc)

    # Collects current max. voltage in self.max_volt_history, will be executed in separate thread
    def monit_osc_loop(self):

        while not self.stop_osc_trigger:
            time.sleep(self.osc_refresh_delay / 1000)

            self.lockin_osc_lock.acquire()
            scope_data = self.lockin_osc.read_scope()
            self.lockin_osc_lock.release()

            self.max_volt = scope_data[0]
            self.avg_volt = scope_data[1]
            if not np.isnan(self.max_volt):
                self.max_volt_history.append(self.max_volt)

                # Check if value reached input range limit by checking if the last 5 values are the same and
                # close to input range (>95%)
                if len(self.max_volt_history) >= 5:
                    range_limit_reached = True
                    for i in range(2, 6):
                        range_limit_reached = range_limit_reached and (
                                math.isclose(self.max_volt_history[-i], self.max_volt, abs_tol=0.000000001)
                                and (self.max_volt_history[-i] >= 0.95 * self.lockin_daq.signal_range))

                    # Check if value too high (may cause damage to PMT) for several consecutive values
                    pmt_limit_reached = True
                    for i in range(1, 4):
                        pmt_limit_reached = pmt_limit_reached and (self.max_volt_history[-i] >= self.shutdown_threshold)

                    if range_limit_reached:
                        self.set_auto_range()
                        if self.acquisition_running:
                            self.log(
                                'Input range limit reached during measurement! Restart with higher input range or lower gain. Aborting...',
                                True)
                            self.abort_measurement()
                    if pmt_limit_reached:
                        self.rescue_pmt()
                        if self.acquisition_running:
                            self.abort_measurement()

        if self.stop_osc_trigger:
            self.lockin_osc_lock.acquire()
            self.lockin_osc.stop_scope()
            self.lockin_osc_lock.release()

            self.stop_osc_trigger = False

    # ---oscilloscope section end---

    # ---Phase offset calibration section start---

    def cal_phaseoffset_start(self):
        self.log('')
        self.log('Starting calibration...')
        self.log('Current phaseoffset: {:.3f} deg'.format(self.lockin_daq.phaseoffset))

        self.cal_running = True
        self.cal_collecting = False
        self.stop_cal_trigger = [False]
        self.set_active_components()

        self.cal_new_value = float('NaN')
        self.cal_pos_theta = 0.0
        self.cal_neg_theta = 0.0

        self.cal_window = PhaseOffsetCalibrationDialog(self)

    def cal_start_record_thread(self, positive):
        self.cal_collecting = True
        self.stop_cal_trigger[0] = False
        self.set_active_components()
        self.cal_theta_thread = th.Thread(target=self.cal_record_thread, args=(positive,))
        self.cal_theta_thread.start()

    def cal_record_thread(self, positive):
        self.log('Thread started...')
        self.lockin_daq_lock.acquire()
        avg = self.lockin_daq.read_ac_theta(self.stop_cal_trigger)
        self.lockin_daq_lock.release()

        if positive:
            self.cal_pos_theta = avg
        else:
            self.cal_neg_theta = avg
        self.log('Thread stopped...')

    def cal_get_current_values(self):
        return self.lockin_daq.ac_theta_avg, self.lockin_daq.ac_theta_count

    def cal_stop_record(self):
        if self.cal_collecting:
            self.stop_cal_trigger[0] = True
            self.cal_collecting = False
            self.set_active_components()

    def cal_get_new_phaseoffset(self, skipped_pos, skipped_neg):
        result = float('NaN')
        n = 0
        difference = 0
        if not skipped_pos:
            self.log('Positive theta at {:.3f} deg'.format(self.cal_pos_theta))
            difference += self.cal_pos_theta - 90
            n += 1
        if not skipped_neg:
            self.log('Negative theta at {:.3f} deg'.format(self.cal_neg_theta))
            difference += self.cal_neg_theta + 90
            n += 1
        if n > 0:
            self.log('Change in phaseoffset: {:.3f} deg'.format(difference / n))
            result = self.lockin_daq.phaseoffset + difference / n
        self.cal_new_value = result
        return result

    def cal_apply_new(self):
        if not math.isnan(self.cal_new_value):
            self.set_phaseoffset(self.cal_new_value)

    def cal_end_after_thread(self):
        if self.cal_theta_thread is not None:
            if self.cal_theta_thread.is_alive():
                self.timer.start(100)
            else:
                self.cal_end()
        else:
            self.cal_end()

    def cal_end(self):
        self.cal_collecting = False
        self.cal_running = False
        self.stop_cal_trigger[0] = False
        self.set_active_components()
        self.cal_window.close()

        self.log('')
        self.log('End of phase calibration.')

        # Save new calibration in last parameters file
        self.save_params('last')


class PhaseOffsetCalibrationDialog(QDialog):
    update_interval = 1000  # ms

    log_name = 'CAL'

    new_offset = 0.0
    current_average = 0.0
    current_datapoints_count = 0

    skipped_pos_cal = False
    skipped_neg_cal = False

    def __init__(self, ctrl):
        super().__init__()
        self.controller = ctrl

        self.setWindowTitle('Phaseoffset Calibration')
        self.setWindowFlag(Qt.WindowCloseButtonHint, False)  # Disable X button
        self.setFixedSize(500, 400)  # Disable resizing

        self.layout = QVBoxLayout(self)

        # TODO: find out what the best phase calibration should be
        self.lbl_text = QLabel(
            'Insert a sample, move to a suitable wavelength and adjust gain to obtain strong positive CPL (e.g. Eu('
            'facam)3 in DMSO at 613 nm)',
            self)
        self.layout.addWidget(self.lbl_text)
        self.lbl_time = QLabel('Time passed (>1200 s recommended): 0 s', self)
        self.layout.addWidget(self.lbl_time)
        self.lbl_datapoints = QLabel('Number of data points: 0', self)
        self.layout.addWidget(self.lbl_datapoints)
        self.lbl_average = QLabel('Average phase: 0 deg', self)
        self.layout.addWidget(self.lbl_average)
        self.lbl_avg_pos = QLabel('Average pos. phase: --', self)
        self.layout.addWidget(self.lbl_avg_pos)
        self.lbl_avg_neg = QLabel('Average neg. phase: --', self)
        self.layout.addWidget(self.lbl_avg_neg)

        self.btn_next = QPushButton('Next', self)
        self.btn_next.clicked.connect(self.next_step)
        self.layout.addWidget(self.btn_next)
        self.btn_skip = QPushButton('Skip', self)
        self.btn_skip.clicked.connect(self.skip)
        self.layout.addWidget(self.btn_skip)
        self.btn_close = QPushButton('Close', self)
        self.btn_close.clicked.connect(self.close)
        self.layout.addWidget(self.btn_close)

        self.step = 0
        self.t0 = 0.0

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_loop)

    def next_step(self):
        self.step += 1

        if self.step == 1:
            self.lbl_text.config(text='Collecting phase of positive CPL ')
            self.t0 = time.time()
            self.timer.start(self.update_interval)
            self.controller.cal_start_record_thread(positive=True)

        elif self.step == 2:
            self.controller.cal_stop_record()
            if self.skipped_pos_cal:
                self.lbl_avg_pos.config(text='Average pos. phase: skipped')
            else:
                current_values = self.controller.cal_get_current_values()
                self.lbl_avg_pos.config(text='Average pos. phase: {:.3f} deg'.format(current_values[0]))
            self.reset_labels()
            self.lbl_text.config(
                text='Insert a sample, move to a suitable wavelength and adjust gain to obtain strong negative CPL (e.g. Eu(facam)3 in DMSO at 595 nm)')

        elif self.step == 3:
            self.lbl_text.config(text='Collecting phase of negative CPL')
            self.t0 = time.time()
            self.timer.start(self.update_interval)
            self.controller.cal_start_record_thread(positive=False)

        elif self.step == 4:
            self.controller.cal_stop_record()
            # wait for cal_theta_thread to stop
            self.show_summary_after_thread()

        elif self.step == 5:
            self.controller.cal_apply_new()
            self.controller.cal_end()
            self.deleteLater()

    # wait for the measurement thread to finish before showing the results
    def show_summary_after_thread(self):
        if not self.controller.cal_theta_thread is None:
            if self.controller.cal_theta_thread.is_alive():
                QTimer.singleShot(100, self.show_summary_after_thread)
            else:
                self.show_summary()
        else:
            self.show_summary()

    def show_summary(self):
        if self.skipped_neg_cal:
            self.lbl_avg_neg.config(text='Average neg. phase: skipped')
        else:
            current_values = self.controller.cal_get_current_values()
            self.lbl_avg_neg.config(text='Average neg. phase: {:.3f} deg'.format(current_values[0]))

        self.new_offset = self.controller.cal_get_new_phaseoffset(self.skipped_pos_cal, self.skipped_neg_cal)
        self.btn_skip['state'] = 'disabled'

        if self.skipped_pos_cal and self.skipped_neg_cal:
            self.lbl_text.config(text='Calibration was skipped.')
            self.btn_next['state'] = 'disabled'
        else:
            self.lbl_text.config(
                text='The new phase offset was determined to: {:.3f} degrees. Do you want to apply this value?'.format(
                    self.new_offset))
            self.btn_next.config(text='Save')

    def skip(self):
        if self.step == 0:
            self.log('Pos. phase: skipped')
            self.skipped_pos_cal = True
            self.step += 1
            self.next_step()
        elif self.step == 1:
            self.log('Pos. phase: skipped')
            self.skipped_pos_cal = True
            self.next_step()
        elif self.step == 2:
            self.log('Neg. phase: skipped')
            self.skipped_neg_cal = True
            self.step += 1
            self.next_step()
        elif self.step == 3:
            self.log('Neg. phase: skipped')
            self.skipped_neg_cal = True
            self.next_step()

    def update_loop(self):
        if self.step in [1, 3] and self.controller.cal_running:
            self.lbl_time.config(text='Time passed (>1200 s recommended): {:.0f} s'.format(time.time() - self.t0))
            current_values = self.controller.cal_get_current_values()
            self.lbl_average.config(text='Average phase: {:.3f} deg'.format(current_values[0]))
            self.lbl_datapoints.config(text='Number of data points: {}'.format(current_values[1]))
            self.timer.start(self.update_interval)

    def reset_labels(self):
        self.lbl_time.config(text='Time passed (>1200 s recommended): 0 s')
        self.lbl_average.config(text='Average phase: 0 deg')
        self.lbl_datapoints.config(text='Number of data points: 0')

    def close(self):
        self.log('Calibration aborted.')
        if self.step in [1, 3]:
            self.controller.cal_stop_record()
        self.controller.cal_end_after_thread()
        self.deleteLater()

    def disable_event(self):
        pass

    def closeEvent(self, event):
        self.close()

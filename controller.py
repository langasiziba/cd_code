import collections
import math
import os
import queue
import re
import time

import numpy as np
import pyvisa
from PyQt5.QtCore import QTimer, QThread, pyqtSignal, QMutex, QCoreApplication, pyqtSlot, Qt
from PyQt5.QtWidgets import QMainWindow, QApplication
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtWidgets import QVBoxLayout, QDialog, QLabel, QPushButton
import pandas as pd

import gui
from mfli import MFLI
from mono import Monoi, Monoii
from pem import PEM
from debug import LogObject


class Controller(QMainWindow, LogObject):
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

    max_volt_hist_lenght = 75  # number of data points in the signal tuning graph
    edt_changed_color = '#FFBAC5'

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
    index_lp_theta = 13

    # averaged spectrum during measurement
    avg_spec = np.array([[],  # wavelenght
                         [],  # DC
                         [],  # AC
                         []])  # gabs

    # variables required for phase offset calibration
    cal_running = False
    cal_collecting = False
    cal_new_value = 0.0
    cal_theta_thread = None
    log_signal = pyqtSignal(str, bool)
    progress_signal = pyqtSignal(float, float, float, int, int, float)
    error_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        # Locks to prevent race conditions in multithreading
        self.pem_lock = QMutex()
        self.monoi_lock = QMutex()
        self.monoii_lock = QMutex()
        self.lockin_daq_lock = QMutex()
        self.lockin_osc_lock = QMutex()
        self.pem_lock.lock()
        self.monoi_lock.lock()
        self.monoii_lock.lock()
        self.lockin_daq_lock.lock()
        self.lockin_osc_lock.lock()
        self.gui = gui

        # This trigger to stop spectra acquisition is a list to pass it by reference to the read_data thread
        self.stop_spec_trigger = [False]
        # For oscilloscope monitoring
        self.stop_osc_trigger = False
        # For phaseoffset calibration
        self.stop_cal_trigger = [False]
        self.spec_thread = None

        # Create GUI
        self.ui = gui.Ui_MainWindow()
        self.ui.setupUi(self)
        self.gui = gui.Ui_MainWindow()

        # Setup log queue and log box
        self.log_queue = queue.Queue()

        self.assign_gui_events()

        if os.path.exists("last_params.txt"):
            self.load_last_settings()

        self.set_initialized(False)
        self.set_acquisition_running(False)

        self.log_author_message()
        self.update_log()

        self.data_for_cdgraph = []
        self.data_for_g_absgraph = []
        self.data_for_molar_ellipsgraph = []
        self.data_for_ldgraph = []

        # gui portion of updating log
        self.log_timer = QTimer()
        self.log_timer.timeout.connect(self.update_log)
        self.log_timer.start(self.log_update_interval)

        # connecting clicked buttons info
        self.ui.setpmtClicked.connect(self.set_PMT_volt_from_edt)
        self.ui.offsetClicked.connect(self.set_offset_from_edt)
        self.ui.savecommentsClicked.connect(self.save_comments_from_edt)
        self.ui.gainClicked.connect(self.set_gain_from_edt)
        self.ui.rangeClicked.connect(self.set_range_from_edt)
        self.ui.setwavelengthClicked.connect(self.set_WL_from_edt)
        self.ui.initializeClicked.clicked.connect(self.init_devices)
        self.ui.rangeChosen.connect(self.set_input_range)
        self.ui.calibrateClicked.clicked.connect(self.cal_phaseoffset_start)
        self.ui.startbuttonClicked.clicked.connect(self.start_spec)
        self.ui.stopbuttonClicked.clicked.connect(self.abort_measurement)

    def set_initialized(self, init):
        self.initialized = init

        if self.initialized:
            self.gui.initialize_button.setEnabled(False)  # disable button
            self.gui.initialize_button.setStyleSheet("background-color: grey")  # change color to grey
            self.gui.close_button.setEnabled(True)  # enable button
            self.gui.close_button.setStyleSheet("background-color: white")
            self.gui.signaltuning_group.setEnabled(True)
            self.gui.spectrasetup_group.setEnabled(True)
            self.gui.spectra_group.setEnabled(True)
        else:
            self.gui.initialize_button.setEnabled(True)  # enable button
            self.gui.initialize_button.setStyleSheet("background-color: white")  # reset color
            self.gui.close_button.setEnabled(False)  # disable button
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

        f = open('last_params.txt', 'r')
        s = f.read()
        f.close()

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

        edts = ['edt_filename',
                'edt_start',
                'edt_end',
                'edt_step',
                'edt_dwell',
                'edt_rep',
                'edt_excWL',
                'edt_comment',
                'edt_ac_blank',
                'edt_phaseoffset',
                'edt_dc_blank',
                'edt_det_corr']

        for i in range(0, len(keywords)):
            val = re_search(keywords[i], s)
            if val != '':
                self.set_edt_text(edts[i], val)

        blank = re_search('PEM off = ([01])\n', s)
        if blank == '1':
            self.gui.var_pem_off.set(1)
        else:
            self.gui.var_pem_off.set(0)

        input_range = re_search('Input range = ([0-9\.]*)\n', s)
        if input_range in self.input_ranges:
            self.gui.cbx_range.set(input_range)

    def set_edt_text(self, edt, text):
        self.gui.set_text(edt, text)

    def init_devices(self):
        """Initialize all the devices used in the setup. The devices include PEM-200,
        monochromators SP-2155 and lock-in amplifier MFLI."""
        try:
            # Initialize PEM-200
            rm_pem = pyvisa.ResourceManager()
            self.log('Available COM devices: {}'.format(rm_pem.list_resources()))
            self.log('Initialize PEM-200...')
            self.window_update()
            self.pem_lock.acquire()
            self.pem = PEM()  # Replace with CD device if different
            self.window_update()
            b1 = self.pem.initialize(rm_pem, self.log_queue)
            self.pem_lock.release()
            self.window_update()
            self.log('')

            # Initialize monochromator SP-2155
            if b1:
                self.log('Initialize monochromator SP-2155...')
                rm_monoi = pyvisa.ResourceManager()
                self.window_update()
                self.monoi_lock.acquire()
                self.monoi = Monoi()  # Replace with CD device if different
                self.window_update()
                b2 = self.monoi.initialize(rm_monoi, self.log_queue)
                self.monoi_lock.release()
                self.window_update()
                self.log('')

                # Initialize lock-in amplifier MFLI for data acquisition
                if b2:
                    self.log('Initialize lock-in amplifier MFLI for data acquisition...')
                    self.window_update()
                    self.lockin_daq_lock.acquire()
                    self.lockin_daq = MFLI('dev7024', 'LID', self.log_queue)
                    self.window_update()
                    b3 = self.lockin_daq.connect()
                    self.window_update()
                    b3 = b3 and self.lockin_daq.setup_for_daq(self.pem.bessel_corr, self.pem.bessel_corr_lp)
                    self.update_PMT_voltage_edt(self.lockin_daq.pmt_volt)
                    self.lockin_daq_lock.release()
                    self.set_phaseoffset_from_edt()
                    self.window_update()
                    self.log('')

                    # Initialize lock-in amplifier MFLI for oscilloscope monitoring
                    if b3:
                        self.log('Initialize lock-in amplifier MFLI for oscilloscope monitoring...')
                        self.window_update()
                        self.lockin_osc_lock.acquire()
                        self.lockin_osc = MFLI('dev7024', 'LIA', self.log_queue)
                        self.window_update()
                        b4 = self.lockin_osc.connect()
                        self.window_update()
                        b4 = b4 and self.lockin_osc.setup_for_scope()
                        self.lockin_osc_lock.release()
                        self.max_volt_history = collections.deque(maxlen=self.max_volt_hist_lenght)
                        self.osc_refresh_delay = 100  # ms
                        self.stop_osc_trigger = False
                        self.start_osc_monit()

                        if b4:
                            self.log('Initialize monochromator 2 SP-2155...')
                            rm_monoii = pyvisa.ResourceManager()
                            self.window_update()
                            self.monoii_lock.acquire()
                            self.monoii = Monoii()  # Replace with CD device if different
                            self.window_update()
                            b5 = self.monoii.initialize(rm_monoii, self.log_queue)
                            self.monoii_lock.release()
                            self.window_update()
                            self.log('')

                            # If all devices were initialized successfully, setup is complete
                            if b5:
                                self.set_initialized(True)
                                self.move_nm(1000)
                                self.window_update()
                                self.log('')
                                self.log('Initialization complete!')
        except Exception as e:
            # If any error occurs during the initialization process, log the error and set initialization as incomplete
            self.set_initialized(False)
            self.log('ERROR during initialization: {}!'.format(str(e)), True)

    def disconnect_devices(self):
        """Disconnect all the devices used in the setup and stop all running threads."""
        self.log('')
        self.log('Closing connections to devices...')
        self.set_PMT_voltage(0.0)

        # Stop all running threads
        self.stop_osc_trigger = True
        self.stop_spec_trigger[0] = True
        self.stop_cal_trigger[0] = True

        # Allow threads to stop
        time.sleep(0.5)

        try:
            # Disconnect all devices
            self.pem.close()
            self.monoi.close()
            self.monoii.close()
            self.lockin_daq.disconnect()
            self.lockin_osc.disconnect()

            self.log('Connections closed.')
            self.set_initialized(False)

        except Exception as e:
            # If any error occurs during the disconnection process, log the error
            self.log('Error while closing connections: {}.'.format(str(e)), True)

    def on_closing(self):
        reply = QMessageBox.question(self, 'Quit', 'Do you want to quit?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            if self.spec_thread is not None:
                if self.spec_thread.isRunning():
                    self.abort_measurement()
                    time.sleep(1)
            if self.cal_theta_thread is not None:
                if self.cal_theta_thread.isRunning():
                    self.cal_stop_record()
                    time.sleep(1)

            self.save_params('last')

            if self.initialized:
                self.disconnect_devices()
            QCoreApplication.instance().quit()
        else:
            pass

    def update_log(self):
        # Handle all log messages currently in the queue, if any
        while self.log_queue.qsize():
            try:
                msg = self.log_queue.get(0)
                self.log_box.append(msg)  # in PyQt, you can append text directly to a QTextEdit
            except queue.Empty:
                pass

    def set_PMT_volt_from_edt(self, v):
        try:
            if (v <= 1.1) and (v >= 0.0):
                self.set_PMT_voltage(v)
        except ValueError as e:
            self.log('Error in set_PMT_voltage_from_edt: ' + str(e), True)

    def set_WL_from_edt(self, nm):
        try:
            self.move_nm(nm)
        except ValueError as e:
            self.log('Error in set_WL_from_edt: ' + str(e), True)

    def set_offset_from_edt(self, po):
        try:
            self.set_phaseoffset(po)  # You need to define this method.
        except ValueError as e:
            self.log('Error in set_offset_from_edt: ' + str(e), True)

    def save_comments_from_edt(self, v):
        self.save_comments(v)  # TODO:You need to define this method.

    def set_gain_from_edt(self, v):
        try:
            if v <= self.max_gain:
                self.set_PMT_voltage(self.gain_to_volt(v))  # You need to define this method.
        except ValueError as e:
            self.log('Error in set_gain_from_edt: ' + str(e), True)

    def set_range_from_edt(self, v):
        try:
            self.set_range(v)  # You need to define this method.
        except ValueError as e:
            self.log('Error in set_range_from_edt: ' + str(e), True)

    def update_progress_txt(self, start: float, stop: float, curr: float, run: int, run_count: int,
                            time_since_start: float):
        # Calculate progress in percent
        if stop > start:
            f = (1 - (stop - curr) / (stop - start)) * 100
        else:
            f = (1 - (curr - stop) / (start - stop)) * 100
        self.gui.progressBar.setValue(f)

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

        self.gui.progressBar.time_left = time_left
        self.gui.progressBar.unit = unit

    def update_osc_plots(self, max_vals):
        self.gui.plot_osc(data_max=max_vals, max_len=self.max_volt_hist_length, time_step=self.osc_refresh_delay)

    def get_data_for_cdgraph(self):
        # You would replace this with the actual method to acquire the data
        return self.data_for_cdgraph

    def get_data_for_g_absgraph(self):
        # You would replace this with the actual method to acquire the data
        return self.data_for_g_absgraph

    def get_data_for_molar_ellipsgraph(self):
        # You would replace this with the actual method to acquire the data
        return self.data_for_molar_ellipsgraph

    def get_data_for_ldgraph(self):
        # You would replace this with the actual method to acquire the data
        return self.data_for_ldgraph

        # ---Start of spectra acquisition section---

    def handle_exception(self, exception_str):
        self.log('Error in record_spec: ' + exception_str, True)

    # This function belongs to your class where the GUI is defined.
    def start_acquisition(self):
        def filename_exists_or_empty(name: str) -> bool:
            if name == '':
                return True
            else:
                return os.path.exists(".\\data\\" + name + ".csv")

        ac_blank = self.gui.edits_map["edt_ac_blank"].text()
        dc_blank = self.gui.edits_map["edt_dc_blank"].text()
        det_corr = self.gui.edits_map["edt_det_corr"].text()
        filename = self.gui.edits_map["edt_filename"].text()
        reps = int(self.gui.edits_map["edt_rep"].text())
        start_nm = float(self.gui.edits_map["edt_start"].text())
        end_nm = float(self.gui.edits_map["edt_end"].text())
        step = float(self.gui.edits_map["edt_step"].text())
        dwell_time = float(self.gui.edits_map["edt_dwell"].text())
        pem_off = self.gui.edits_map["var_pem_off"].text()

        # check if the files exist or not
        ac_blank_exists = filename_exists_or_empty(ac_blank)
        dc_blank_exists = filename_exists_or_empty(dc_blank)
        det_corr_exists = filename_exists_or_empty(det_corr)

        # For averaged measurements add the suffix of the first scan for the filename check
        if reps > 1:
            filename_check = filename + '_1'
        else:
            filename_check = filename

        filename_exists = filename_exists_or_empty(filename_check)

        error = not ac_blank_exists or not dc_blank_exists or not det_corr_exists or filename_exists

        if error:
            if not ac_blank_exists:
                self.log('Error: AC-blank file does not exist!', True)
            if not dc_blank_exists:
                self.log('Error: DC-blank file does not exist!', True)
            if not det_corr_exists:
                self.log('Error: Detector correction file does not exist!', True)
            if filename_exists:
                self.log('Error: Spectra filename {} already exists!'.format(filename_check), True)
        else:
            # Start the SpecThread with the parameters from the GUI
            self.start_spec(start_nm, end_nm, step, dwell_time, reps, filename, ac_blank, dc_blank, det_corr, pem_off)

    def start_spec(self, start_nm, end_nm, step, dwell_time, reps, filename, ac_blank, dc_blank, det_corr, pem_off):
        self.spec_thread = SpecThread(start_nm, end_nm, step, dwell_time, reps, filename, ac_blank, dc_blank,
                                      det_corr, pem_off, self)
        self.spec_thread.recordSignal.connect(self.update_spec)  # connect the signal to your update function
        self.spec_thread.exceptionSignal.connect(self.handle_exception)  # handle exceptions
        self.spec_thread.start()

    def record_spec(self, start_nm: float, end_nm: float, step: float, dwell_time: float, reps: int, filename: str,
                    ac_blank: str, dc_blank: str, det_corr: str, pem_off: int):

        def check_lp_theta_std(lp: float) -> bool:
            if lp < self.lp_theta_std_warning_threshold:
                self.log_signal.emit(
                    'Warning: Possibly linearly polarized emisssion at {:.2f} (lp_theta_std = {:.3f})!'.format(curr_nm,
                                                                                                               lp),
                    False)
                return True
            else:
                return False

        self.log_signal.emit('', False)
        self.log_signal.emit(
            'Spectra acquisition: {:.2f} to {:.2f} nm with {:.2f} nm steps and {:.3f} s per step'.format(start_nm,
                                                                                                         end_nm, step,
                                                                                                         dwell_time),
            False)

        self.log_signal.emit('Starting data acquisition.', False)

        self.lockin_daq_lock.acquire()
        self.lockin_daq.set_dwell_time(dwell_time)
        self.lockin_daq_lock.release()

        self.interruptable_sleep(dwell_time)

        dfall_spectra = np.empty(reps, dtype=object)
        self.avg_spec = np.array([[], [], [], []])

        correction = ac_blank != '' or dc_blank != '' or det_corr != ''

        if start_nm > end_nm:
            inc = -step
        else:
            inc = step
        direction = np.sign(inc)

        self.progress_signal.emit(0, 1, 0, 1, reps, 0)

        self.set_modulation_active(pem_off == 0)

        time_since_start = -1.0
        t0 = time.time()

        i = 0
        while (i < reps) and not self.stop_spec_trigger[0]:
            self.log_signal.emit('', False)
            self.log_signal.emit('Run {}/{}'.format(i + 1, reps), False)

            lp_detected = False

            self.curr_spec = np.array([[], [], [], [], [], [], [], [], [], [], [], [], [], [], [], [], [], []])

            curr_nm = start_nm - inc
            while ((((direction > 0) and (curr_nm < end_nm)) or ((direction < 0) and (curr_nm > end_nm)))
                   and not self.stop_spec_trigger[0]):

                curr_nm = curr_nm + inc
                self.move_nm(curr_nm, pem_off == 0)

                self.interruptable_sleep(self.lowpass_filter_risetime)

                j = 0
                success = False
                while (j < 5) and not success and not self.stop_spec_trigger[0]:
                    self.lockin_daq_lock.acquire()
                    data = self.lockin_daq.read_data(self.stop_spec_trigger)
                    self.lockin_daq_lock.release()

                    if not self.stop_spec_trigger[0]:
                        lp_detected = lp_detected or check_lp_theta_std(data['data'][self.index_lp_theta])
                        success = data['success']
                    j += 1

                if not success and not self.stop_spec_trigger[0]:
                    self.stop_spec_trigger[0] = True
                    self.error_signal.emit('Could not collect data after 5 tries, aborting...')

                if not self.stop_spec_trigger[0]:
                    data_with_WL = np.array([np.concatenate(([curr_nm], data['data']))])
                    self.curr_spec = np.hstack((self.curr_spec, data_with_WL.T))
                    if reps > 1:
                        self.add_data_to_avg_spec(data_with_WL, i)

                time_since_start = time.time() - t0
                self.progress_signal.emit(start_nm, end_nm, curr_nm, i + 1, reps, time_since_start)

            if self.stop_spec_trigger[0]:
                self.set_PMT_voltage(0.0)

            self.log_signal.emit('This scan took {:.0f} s.'.format(time_since_start), False)

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

            if lp_detected:
                self.log_signal.emit('', False)
                self.log_signal.emit('Warning: Possibly linearly polarized emission!', True)

            i += 1

        self.log_signal.emit('Stopping data acquisition.', False)
        self.set_acquisition_running(False)

        if reps > 1 and not self.stop_spec_trigger[0]:
            dfavg_spec = self.df_average_spectra(dfall_spectra)
            self.save_spec(dfavg_spec, filename + '_avg', False)

            if correction:
                dfavg_spec_corr = self.apply_corr(dfavg_spec, ac_blank, dc_blank, det_corr)
                self.save_spec(dfavg_spec_corr, filename + '_avg_corr', False)

        self.log_signal.emit('', False)
        self.log_signal.emit('Returning to start wavelength', False)
        self.set_modulation_active(True)
        self.move_nm(start_nm, move_pem=True)

        self.stop_spec_trigger[0] = False

    def interruptable_sleep(self, t: float):
        start = time.time()
        while (time.time() - start < t) and not self.stop_spec_trigger[0]:
            time.sleep(0.01)

    def add_data_to_avg_spec(self, data, curr_rep: int):
        # avg_spec structure: [[WL],[DC],[AC],[gabs]]
        if curr_rep == 0:
            self.avg_spec = np.hstack((self.avg_spec, np.array(
                ([data[0][0]], [data[0][self.index_dc]], [data[0][self.index_ac]], [data[0][self.index_glum]]))))
        else:
            # find index where the wavelength of the new datapoint matches
            index = np.where(self.avg_spec[0] == data[0][0])[0]
            if len(index) > 0:
                # reaverage DC and AC
                self.avg_spec[1][index[0]] = (self.avg_spec[1][index[0]] * curr_rep + data[0][self.index_dc]) / (
                        curr_rep + 1)
                self.avg_spec[2][index[0]] = (self.avg_spec[2][index[0]] * curr_rep + data[0][self.index_ac]) / (
                        curr_rep + 1)
                # recalculate glum
                self.avg_spec[3][index[0]] = 2 * self.avg_spec[2][index[0]] / self.avg_spec[1][index[0]]

                # converts a numpy array to a pandas DataFrame

    def np_to_pd(self, spec):
        df = pd.DataFrame(spec.T)
        df.columns = ['WL', 'DC', 'DC_std', 'AC', 'AC_std', 'I_L', 'I_L_std', 'I_R', 'I_R_std', 'gabs', 'gabs_std',
                      'ld', 'ld_std', 'mollar_ellips', 'molar_ellips_std', 'ellips', 'ellips_std']
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
        def is_corr_suitable(df_corr: pd.DataFrame, check_index: bool) -> bool:
            first_WL_spec = dfspec.index[0]
            last_WL_spec = dfspec.index[-1]

            first_WL_corr = df_corr.index[0]
            last_WL_corr = df_corr.index[-1]

            # Check if the wavelength region in dfspec is covered by df_det_corr
            WL_region_ok = min(first_WL_spec, last_WL_spec) >= min(first_WL_corr, last_WL_corr) and max(first_WL_spec,
                                                                                                        last_WL_spec) <= max(
                first_WL_corr, last_WL_corr)
            # Check if the measured wavelength values are available in the correction file (for AC and DC without interpolation)
            values_ok = not check_index or dfspec.index.isin(df_corr.index).all()

            return WL_region_ok and values_ok

        # Interpolate the detector correction values to match the measured wavelength values
        def interpolate_detcorr():
            # Create a copy of the measured wavelengths and fill it with NaNs
            dfspec_nan = pd.DataFrame()
            dfspec_nan['nan'] = dfspec['AC'].copy()
            dfspec_nan.iloc[:, 0] = float('NaN')

            nonlocal df_det_corr
            # Add the measured wavelengths to the correction data, missing values in the correction data will be set to NaN
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

            if is_corr_suitable(df_det_corr, False):
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

            if is_corr_suitable(df_ac_blank, True):
                dfspec['AC'] = dfspec['AC'] - df_ac_blank['AC']
                dfspec['AC_std'] = ((dfspec['AC_std'] / 2) ** 2 + (df_ac_blank['AC_std'] / 2) ** 2) ** 0.5
            else:
                self.log('AC blank correction file does not contain the measured wavelengths!', True)

                # DC baseline correction
        if dc_blank != '':
            self.log('DC blank correction with {}'.format(".\\data\\" + dc_blank + ".csv"))
            df_dc_blank = pd.read_csv(filepath_or_buffer=".\\data\\" + dc_blank + ".csv", sep=',', index_col='WL')

            if is_corr_suitable(df_dc_blank, True):
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

    def abort_measurement(self):
        self.log('')
        self.log('>>Aborting measurement<<')

        self.stop_spec_trigger[0] = True
        self.reactivate_after_abort()

    def reactivate_after_abort(self):
        if not self.spec_thread is None:
            if self.spec_thread.is_alive():
                QTimer.singleShot(500, self.reactivate_after_abort)
            else:
                self.set_acquisition_running(False)
        else:
            self.set_acquisition_running(False)

    def set_modulation_active(self, b):
        # deactivating phase-locked loop on PEM reference in lock-in to retain last PEM frequency
        self.lockin_daq_lock.lock()
        self.lockin_daq.set_extref_active(0, b)
        self.lockin_daq.daq.sync()
        self.lockin_daq_lock.unlock()

        # deactivating pem will cut off reference signal and modulation
        self.pem_lock.lock()
        self.pem.set_active(b)
        self.pem_lock.unlock()
        if not b:
            self.gui.canvas.itemconfigure(self.gui.txt_PEM, text='off')

    def set_phaseoffset(self, value):
        if self.initialized:
            lockin_daq_set_phase_offset_thread = LockinDAQSetPhaseOffsetThread(self.lockin_daq, value)
            lockin_daq_set_phase_offset_thread.start()
            lockin_daq_set_phase_offset_thread.wait()

    def move_nm(self, nm, move_pem=True):
        self.log('')
        self.log('Move to {} nm'.format(nm))
        if self.initialized:
            mono_thread = MoveThread(self.mono, nm)
            mono_thread.start()

            if move_pem:
                self.pem_lock.lock()
                self.pem.set_nm(nm)
                self.pem_lock.unlock()
                self.update_pem_lbl(nm)

            mono_thread.wait()

            self.update_mono_edt_lbl(nm)

            if self.acquisition_running:
                self.interruptable_sleep(self.move_delay)
            else:
                time.sleep(self.move_delay)
        else:
            self.log('Instruments not initialized!', True)

    def mono_move(self, nm):
        mono_move_thread = MoveThread(self.mono, nm)
        mono_move_thread.start()
        mono_move_thread.wait()

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
            lockin_daq_thread = LockinDAQThread(self.lockin_daq, volt)
            lockin_daq_thread.start()
            lockin_daq_thread.wait()

            self.update_PMT_voltage_edt(volt)
        except Exception as e:
            self.log('Error in set_PMT_voltage: ' + str(e), True)

    def rescue_pmt(self):
        self.log('Signal ({:.2f} V) higher than threshold ({:.2f} V)!! Setting PMT to 0 V'.format(self.max_volt,
                                                                                                  self.shutdown_threshold),
                 True)
        self.set_PMT_voltage(0.0)

    def set_input_range(self, f):
        self.lockin_daq_lock.lock()
        self.lockin_daq.set_input_range(f=f, auto=False)
        self.lockin_daq_lock.unlock()

    def set_auto_range(self):
        auto_range_thread = AutoRangeThread(self.lockin_daq)
        auto_range_thread.updated_signal_range.connect(lambda x: self.gui.cbx_range.setCurrentText(x))
        auto_range_thread.start()

    def set_phaseoffset(self, f):
        phase_offset_thread = PhaseOffsetThread(self.lockin_daq, f)
        phase_offset_thread.updated_phaseoffset.connect(self.update_phaseoffset_edt)
        phase_offset_thread.start()

    # ---oscilloscope section start---
    def start_osc_monit(self):
        self.oscilloscope_thread = OscilloscopeThread(self)
        self.oscilloscope_thread.max_voltage_signal.connect(self.gui.update_max_voltage)
        self.oscilloscope_thread.avg_voltage_signal.connect(self.gui.update_avg_voltage)
        self.oscilloscope_thread.range_limit_reached_signal.connect(self.handle_range_limit_reached)
        self.oscilloscope_thread.pmt_limit_reached_signal.connect(self.handle_pmt_limit_reached)
        self.oscilloscope_thread.start()

    def handle_range_limit_reached(self):
        self.set_auto_range()
        if self.acquisition_running:
            self.log(
                'Input range limit reached during measurement! Restart with higher input range or lower gain. Aborting...',
                True)
            self.abort_measurement()

    def handle_pmt_limit_reached(self):
        self.rescue_pmt()
        if self.acquisition_running:
            self.abort_measurement()

    # ---Phase offset calibration section start---

    from PyQt5.QtCore import QThread, QTimer

    # ---Phase offset calibration section start---

    class RecordThread(QThread):
        def __init__(self, parent=None, positive=None, lock=None):
            super().__init__(parent)
            self.positive = positive
            self.lock = lock

        def run(self):
            self.parent().log('Thread started...')
            with self.lock:
                avg = self.parent().lockin_daq.read_ac_theta(self.parent().stop_cal_trigger)

            if self.positive:
                self.parent().cal_pos_theta = avg
            else:
                self.parent().cal_neg_theta = avg
            self.parent().log('Thread stopped...')

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
        self.cal_theta_thread = RecordThread(self.log, self.lockin_daq, self.stop_cal_trigger,
                                             self.set_cal_pos_theta, self.set_cal_neg_theta,
                                             positive, self.lockin_daq_lock)
        self.cal_theta_thread.start()

    # these are the new setters for the cal_pos_theta and cal_neg_theta attributes
    def set_cal_pos_theta(self, value):
        self.cal_pos_theta = value

    def set_cal_neg_theta(self, value):
        self.cal_neg_theta = value

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
        if self.cal_theta_thread.isRunning():
            QTimer.singleShot(100, self.cal_end_after_thread)
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

    # ---Phase offset calibration section end---


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
        self.setModal(True)

        self.layout = QVBoxLayout(self)
        self.lbl_text = QLabel(self)
        self.layout.addWidget(self.lbl_text)
        self.lbl_time = QLabel(self)
        self.layout.addWidget(self.lbl_time)
        self.lbl_datapoints = QLabel(self)
        self.layout.addWidget(self.lbl_datapoints)
        self.lbl_average = QLabel(self)
        self.layout.addWidget(self.lbl_average)

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
            self.lbl_text.setText('Collecting phase of positive CD ')
            self.t0 = time.time()
            QTimer.singleShot(self.update_interval, self.update_loop)
            self.controller.cal_start_record_thread(positive=True)

        elif self.step == 2:
            self.controller.cal_stop_record()
            if self.skipped_pos_cal:
                self.lbl_avg_pos.setText('Average pos. phase: skipped')
            else:
                current_values = self.controller.cal_get_current_values()
                self.lbl_avg_pos.setText('Average pos. phase: {:.3f} deg'.format(current_values[0]))
            self.reset_labels()
            self.lbl_text.setText('Insert a sample, move to a suitable wavelength and adjust gain to obtain '
                                  'strong CD')

        elif self.step == 3:
            self.lbl_text.setText('Collecting phase of negative CD')
            self.t0 = time.time()
            QTimer.singleShot(self.update_interval, self.update_loop)
            self.controller.cal_start_record_thread(positive=False)

        elif self.step == 4:
            self.controller.cal_stop_record()
            # wait for cal_theta_thread to stop
            self.show_summary_after_thread()

        elif self.step == 5:
            self.controller.cal_apply_new()
            self.controller.cal_end()
            self.close()

    # Wait for the measurement thread to finish before showing the results
    def show_summary_after_thread(self):
        if self.controller.cal_theta_thread is not None:
            if self.controller.cal_theta_thread.isRunning():
                QTimer.singleShot(100, self.show_summary_after_thread)
            else:
                self.show_summary()
        else:
            self.show_summary()

    def show_summary(self):
        if self.skipped_neg_cal:
            self.lbl_avg_neg.setText('Average neg. phase: skipped')
        else:
            current_values = self.controller.cal_get_current_values()
            self.lbl_avg_neg.setText('Average neg. phase: {:.3f} deg'.format(current_values[0]))

        self.new_offset = self.controller.cal_get_new_phaseoffset(self.skipped_pos_cal, self.skipped_neg_cal)
        self.btn_skip.setDisabled(True)

        if self.skipped_pos_cal and self.skipped_neg_cal:
            self.lbl_text.setText('Calibration was skipped.')
            self.btn_next.setDisabled(True)
        else:
            self.lbl_text.setText(
                'The new phase offset was determined to: {:.3f} degrees. Do you want to apply this value?'.format(
                    self.new_offset))
            self.btn_next.setText('Save')

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
            self.lbl_time.setText('Time passed (>1200 s recommended): {:.0f} s'.format(time.time() - self.t0))
            current_values = self.controller.cal_get_current_values()
            self.lbl_average.setText('Average phase: {:.3f} deg'.format(current_values[0]))
            self.lbl_datapoints.setText('Number of data points: {}'.format(current_values[1]))
            QTimer.singleShot(self.update_interval, self.update_loop)

    def reset_labels(self):
        self.lbl_time.setText('Time passed (>1200 s recommended): 0 s')
        self.lbl_average.setText('Average phase: 0 deg')
        self.lbl_datapoints.setText('Number of data points: 0')

    def close(self):
        self.log('Calibration aborted.')
        if self.step in [1, 3]:
            self.controller.cal_stop_record()
        self.controller.cal_end_after_thread()

    def disable_event(self):
        pass


class RecordThread(QThread):
    def __init__(self, log_method, lockin_daq, stop_cal_trigger, set_pos_theta, set_neg_theta, positive=None,
                 lock=None):
        super().__init__()
        self.positive = positive
        self.lock = lock
        self.log_method = log_method
        self.lockin_daq = lockin_daq
        self.stop_cal_trigger = stop_cal_trigger
        self.set_pos_theta = set_pos_theta
        self.set_neg_theta = set_neg_theta

    def run(self):
        self.log_method('Thread started...')
        with self.lock:
            avg = self.lockin_daq.read_ac_theta(self.stop_cal_trigger)

        if self.positive:
            self.set_pos_theta(avg)
        else:
            self.set_neg_theta(avg)
        self.log_method('Thread stopped...')


class SpecThread(QThread):
    recordSignal = pyqtSignal(float, float, float, float, int, str, str, str, str, int)  # update signal
    exceptionSignal = pyqtSignal(str)  # exception signal

    def __init__(self, start_nm, end_nm, step, dwell_time, reps, filename, ac_blank, dc_blank, det_corr, pem_off,
                 controller):
        QThread.__init__(self)
        self.start_nm = start_nm
        self.end_nm = end_nm
        self.step = step
        self.dwell_time = dwell_time
        self.reps = reps
        self.filename = filename
        self.ac_blank = ac_blank
        self.dc_blank = dc_blank
        self.det_corr = det_corr
        self.pem_off = pem_off
        self.controller = controller

    def run(self):
        try:
            self.controller.record_spec(self.start_nm, self.end_nm, self.step, self.dwell_time, self.reps,
                                        self.filename, self.ac_blank, self.dc_blank, self.det_corr, self.pem_off)
        except Exception as e:
            self.exceptionSignal.emit(str(e))


class MoveThread(QThread):
    def __init__(self, mono, nm, parent=None):
        super(MoveThread, self).__init__(parent)
        self.mono = mono
        self.nm = nm

    def run(self):
        self.mono.set_nm(self.nm)


class LockinDAQThread(QThread):
    def __init__(self, lockin_daq, volt, parent=None):
        super(LockinDAQThread, self).__init__(parent)
        self.lockin_daq = lockin_daq
        self.volt = volt

    def run(self):
        self.lockin_daq.set_PMT_voltage(self.volt, False)


class LockinDAQSetPhaseOffsetThread(QThread):
    def __init__(self, lockin_daq, value, parent=None):
        super(LockinDAQSetPhaseOffsetThread, self).__init__(parent)
        self.lockin_daq = lockin_daq
        self.value = value

    def run(self):
        self.lockin_daq.set_phaseoffset(self.value)


class AutoRangeThread(QThread):
    updated_signal_range = pyqtSignal(str)

    def __init__(self, lockin_daq, parent=None):
        super(AutoRangeThread, self).__init__(parent)
        self.lockin_daq = lockin_daq

    def run(self):
        self.lockin_daq.set_input_range(f=0.0, auto=True)
        self.updated_signal_range.emit('{:.3f}'.format(self.lockin_daq.signal_range))


class PhaseOffsetThread(QThread):
    updated_phaseoffset = pyqtSignal(float)

    def __init__(self, lockin_daq, f, parent=None):
        super(PhaseOffsetThread, self).__init__(parent)
        self.lockin_daq = lockin_daq
        self.f = f

    def run(self):
        self.lockin_daq.set_phaseoffset(self.f)
        self.updated_phaseoffset.emit(self.f)


class OscilloscopeThread(QThread):
    max_voltage_signal = pyqtSignal(float)
    avg_voltage_signal = pyqtSignal(float)
    range_limit_reached_signal = pyqtSignal()
    pmt_limit_reached_signal = pyqtSignal()

    def __init__(self, controller):
        QThread.__init__(self)
        self.controller = controller
        # initialize other attributes here...

    def run(self):
        while not self.controller.stop_osc_trigger:
            time.sleep(self.controller.osc_refresh_delay / 1000)

            self.controller.lockin_osc_lock.acquire()
            scope_data = self.controller.lockin_osc.read_scope()
            self.controller.lockin_osc_lock.release()

            max_volt = scope_data[0]
            avg_volt = scope_data[1]
            if not np.isnan(max_volt):
                self.max_voltage_signal.emit(max_volt)
                self.avg_voltage_signal.emit(avg_volt)

                # Check if value reached input range limit by checking if the last 5 values are the same and
                # close to input range (>95%)
                if len(self.controller.max_volt_history) >= 5:
                    range_limit_reached = True
                    for i in range(2, 6):
                        range_limit_reached = range_limit_reached and (
                                math.isclose(self.controller.max_volt_history[-i], max_volt, abs_tol=0.000000001)
                                and (self.controller.max_volt_history[
                                         -i] >= 0.95 * self.controller.lockin_daq.signal_range))

                    # Check if value too high (may cause damage to PMT) for several consecutive values
                    pmt_limit_reached = True
                    for i in range(1, 4):
                        pmt_limit_reached = pmt_limit_reached and (
                                self.controller.max_volt_history[-i] >= self.controller.shutdown_threshold)

                    if range_limit_reached:
                        self.range_limit_reached_signal.emit()
                    if pmt_limit_reached:
                        self.pmt_limit_reached_signal.emit()

        if self.controller.stop_osc_trigger:
            self.controller.lockin_osc_lock.acquire()
            self.controller.lockin_osc.stop_scope()
            self.controller.lockin_osc_lock.release()

            self.controller.stop_osc_trigger = False


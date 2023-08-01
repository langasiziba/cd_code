import collections
import os
import queue
import re
import time

import numpy as np
import pyvisa
from PyQt5.QtCore import QTimer, QThread, pyqtSignal, QMutex, QCoreApplication
from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtWidgets import QVBoxLayout, QDialog, QLabel, QPushButton

import gui
from mfli import MFLI
from mono import Monoi, Monoii
from pem import PEM


class Controller(QMainWindow):
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

    # Parameters to calculate approx. gain from control voltage of PMT, log(gain) = slope*pmt_voltage + offset, derived from manual
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

        # Setup log queue and log box
        self.log_queue = queue.Queue()
        self.log_box = self.gui.edt_debuglog

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

    def start_spec(self):

        # this checks if the filename of the spectra exist or not
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

        # acquire the settings from the user
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
                # For averaged measurements add the suffix of the first scan for the filename check
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
                        float(self.gui.edt_start.get()),
                        float(self.gui.edt_end.get()),
                        float(self.gui.edt_step.get()),
                        float(self.gui.edt_dwell.get()),
                        reps,
                        filename,
                        ac_blank,
                        dc_blank,
                        det_corr,
                        self.gui.var_pem_off.get()))
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

        def check_lp_theta_std(lp: float) -> bool:
            if lp < self.lp_theta_std_warning_threshold:
                self.log(
                    'Warning: Possibly linearly polarized emisssion at {:.2f} (lp_theta_std = {:.3f})!'.format(curr_nm,
                                                                                                               lp),
                    False)
                return True
            else:
                return False

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
                                  []])  # glum

        correction = ac_blank != '' or dc_blank != '' or det_corr != ''

        if start_nm > end_nm:
            inc = -step
        else:
            inc = step
        direction = np.sign(inc)

        self.update_progress_txt(0, 1, 0, 1, reps, 0)

        # Disable PEM for AC background measurement
        self.set_modulation_active(pem_off == 0)

        time_since_start = -1.0
        t0 = time.time()

        i = 0
        while (i < reps) and not self.stop_spec_trigger[0]:
            self.log('')
            self.log('Run {}/{}'.format(i + 1, reps))

            lp_detected = False

            self.curr_spec = np.array([[],  # wavelenght
                                       [],  # AC
                                       [],  # AC stddev
                                       [],  # DC
                                       [],  # DC stddev
                                       [],  # I_L
                                       [],  # I_L stddev
                                       [],  # I_R
                                       [],  # I_R stddev
                                       [],  # glum
                                       [],  # glum stddev
                                       [],  # lp_r
                                       [],  # lp_r stddev
                                       [],  # lp theta
                                       [],  # lp theta stddev
                                       [],  # lp
                                       []])  # lp stddev

            # self.log('start {}'.format(time.time()-t0))
            curr_nm = start_nm - inc
            while ((((direction > 0) and (curr_nm < end_nm)) or ((direction < 0) and (curr_nm > end_nm)))
                   and not self.stop_spec_trigger[0]):

                curr_nm = curr_nm + inc
                # self.log('before move {:.3f}'.format(time.time()-t0))
                self.move_nm(curr_nm, pem_off == 0)
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
                    # self.log('afer lock {:.3f}'.format(time.time()-t0))
                    data = self.lockin_daq.read_data(self.stop_spec_trigger)
                    # self.log('after read {:.3f}'.format(time.time()-t0))
                    self.lockin_daq_lock.release()

                    if not self.stop_spec_trigger[0]:
                        # Check if there is a linearly polarized component (2f) in the signal
                        lp_detected = lp_detected or check_lp_theta_std(data['data'][self.index_lp_theta])
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
                self.update_progress_txt(start_nm, end_nm, curr_nm, i + 1, reps, time_since_start)
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

            if lp_detected:
                self.log('')
                self.log('Warning: Possibly linearly polarized emission!', True)

            i += 1

        self.log('Stopping data acquisition.')
        self.set_acquisition_running(False)

        # averaging and correction of the averaged spectrum
        if reps > 1 and not self.stop_spec_trigger[0]:
            dfavg_spec = self.df_average_spectra(dfall_spectra)
            self.save_spec(dfavg_spec, filename + '_avg', False)

            if correction:
                dfavg_spec_corr = self.apply_corr(dfavg_spec_recalc, ac_blank, dc_blank, det_corr)
                self.save_spec(dfavg_spec_corr, filename + '_avg_corr', False)

        self.log('')
        self.log('Returning to start wavelength')
        self.set_modulation_active(True)
        self.move_nm(start_nm, move_pem=True)

        self.stop_spec_trigger[0] = False
        # except Exception as e:
        # self.log("Error in record_spec: {}".format(str(e)))


    def open_cal_dialog(self):
        self.cal_dialog = PhaseOffsetCalibrationDialog(self)
        self.cal_dialog.show()

    # Implement other methods
    def cal_start_record_thread(self, positive):
        self.cal_collecting = True
        self.stop_cal_trigger[0] = False
        self.set_active_components()
        self.cal_theta_thread = RecordThread(self, positive)
        self.cal_theta_thread.exceptionSignal.connect(self.handle_thread_exception)
        self.cal_theta_thread.start()

    def edt_changed(self, var):
        edt = self.gui.input_mapping[var]
        edt.setStyleSheet("background-color: yellow")

    def handle_thread_exception(self, msg):
        # Handle the exception message in some way. For example, you could print it:
        print("Exception in RecordThread:", msg)

    def cal_stop_record(self):
        pass

    def cal_get_current_values(self):
        return 0, 0

    def cal_get_new_phaseoffset(self, skipped_pos_cal, skipped_neg_cal):
        return 0

    def cal_apply_new(self):
        pass

    def cal_end(self):
        pass



class RecordThread(QThread):
    exceptionSignal = pyqtSignal(str)  # Define a signal to emit exception messages

    def __init__(self, controller, positive):
        QThread.__init__(self)
        self.controller = controller
        self.positive = positive

    def run(self):
        try:
            self.controller.log('Thread started...')
            self.controller.lockin_daq_lock.acquire()
            avg = self.controller.lockin_daq.read_ac_theta(self.controller.stop_cal_trigger)
            self.controller.lockin_daq_lock.release()

            if self.positive:
                self.controller.cal_pos_theta = avg
            else:
                self.controller.cal_neg_theta = avg
            self.controller.log('Thread stopped...')
        except Exception as e:
            self.exceptionSignal.emit(str(e))


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
            self.lbl_text.setText('Collecting phase of positive CPL ')
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
            self.lbl_text.setText('Collecting phase of negative CPL')
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

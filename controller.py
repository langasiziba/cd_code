import time

import pyvisa
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QDialog, QLabel, QPushButton
from PyQt5.QtCore import QTimer, Qt, QThread, pyqtSignal

from mfli import MFLI
from mono import Monoi, Monoii
import collections
from PyQt5.QtWidgets import QMessageBox
from pem import PEM
import numpy as np


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

    curr_spec = np.array([[],  # wavelenght
                          [],  # DC
                          [],  # DC stddev
                          [],  # AC
                          [],  # AC stddev
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
    index_ac = 3  # in curr_spec
    index_dc = 1
    index_glum = 9
    index_lp_theta = 13

    # averaged spectrum during measurement
    avg_spec = np.array([[],  # wavelenght
                         [],  # DC
                         [],  # AC
                         []])  # glum

    # variables required for phase offset calibration
    cal_running = False
    cal_collecting = False
    cal_new_value = 0.0
    cal_theta_thread = None

    def __init__(self):
        super().__init__()
        self.cal_running = False
        self.cal_theta_thread = None
        # ... other necessary properties

    def init_devices(self):
        """Initialize all the devices used in the setup. The devices include PEM-200,
        monochromator SP-2155 and lock-in amplifiers MFLI."""
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

                        if b1:
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
            self.mono.close()
            self.lockin_daq.disconnect()
            self.lockin_osc.disconnect()

            self.log('Connections closed.')
            self.set_initialized(False)

        except Exception as e:
            # If any error occurs during the disconnection process, log the error
            self.log('Error while closing connections: {}.'.format(str(e)), True)

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


    def on_closing(self):
        """Save parameters, disconnect devices and close application when asked to quit."""
        reply = QMessageBox.question(self.gui.window, 'Quit', 'Do you want to quit?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            # Stop all running threads
            if self.spec_thread and self.spec_thread.is_alive():
                self.abort_measurement()
                time.sleep(1)

            if self.cal_theta_thread and self.cal_theta_thread.is_alive():
                self.cal_stop_record()
                time.sleep(1)

            # Save parameters and disconnect devices before closing
            self.save_params('last')

            if self.initialized:
                self.disconnect_devices()

            # Close the application window
            self.gui.window.close()

        # Rest of the class goes here...

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
        if self.step in [1,3] and self.controller.cal_running:
            self.lbl_time.setText('Time passed (>1200 s recommended): {:.0f} s'.format(time.time()-self.t0))
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
        if self.step in [1,3]:
            self.controller.cal_stop_record()
        self.controller.cal_end_after_thread()

    def disable_event(self):
        pass


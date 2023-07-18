"""MFLI coding: As for the integration with the MFLI Lock-in Amplifier, you would need to feed the reference signal
output from the PEM controller into the reference input of the MFLI. Then, in the MFLI's control software or
programming interface, you would set up a demodulator to use this reference signal for phase-sensitive detection.
This allows the MFLI to measure the amplitude and phase of the signal from the photomultiplier tube (PMT) at the
modulation frequency of the PEM."""


import math
import numpy as np
import statistics
import zhinst.utils
import zhinst.core
from debug import LogObject
import queue
from typing import Tuple
import time



# Controls the Zurich Instruments MFLI lock-in amplifier
class MFLI(LogObject):
    sampling_rate = 104.6  # s-1 data transfer rate
    time_const = 0.00811410938  # s, time constant of the low-pass filter of the lock-in amplifier
    filter_order = 3
    pmt_low_limit = 0.0  # V, low limit of control voltage for PMT
    pmt_high_limit = 1.1  # V, high limit of control voltage for PMT
    pmt_volt = 0.0  # V, control voltage of the PMT
    signal_range = 3.0  # V, default signal range
    dwell_time = 0.5  # s, default acquisition time per point
    dwell_time_scaling = 1
    data_set_size = int(np.ceil(dwell_time * sampling_rate))  # number of data points per acquisition
    dc_phaseoffset = 0.0  # degrees, results in DC phase at +90 or -90 degrees
    phaseoffset = 158.056  # degrees
    rel_lp_phaseoffset = -22  # degrees
    bessel_corr = 0.0  # correction factor for the sin(A sin(x)) modulation of the PEM, will be obtained from PEM
    bessel_corr_lp = 0.0  # correction factor for linear component, will be obtained from PEM
    ac_theta_avg = 0.0
    ac_theta_count = 0
    sqrt2 = np.sqrt(2)
    daq = None

    def __init__(self, ID:str, logname:str, log_queue:queue.Queue):
        self.devID = ID  # ID of the device which is dev7024
        self.devPath = '/' + self.devID + '/'
        self.log_name = logname
        self.log_queue = log_queue


    def connect(self) -> bool:
        try:
            # Start API Session
            self.daq = zhinst.core.ziDAQServer()
            self.daq.connectDevice(self.devID)

            # Issue a warning and return False if the release version of the API used in the session (daq) does not
            # have the same release version as the Data Server (that the API is connected to).
            zhinst.utils.utils.api_server_version_check(self.daq)
            return True
        except Exception as e:
            print('Error connecting: {}'.format(str(e)))
            return False

    def disconnect(self):
        print('Disconnecting...')
        try:
            self.daq.disconnectDevice(self.devID)
        except Exception as e:
            print('Error during disconnecting: {}'.format(str(e)))

    def setup_device(self, pmt: bool, ch1: bool, ch2: bool, ch3: bool, ch4: bool, daqm: bool, scp: bool,
                     bessel: float = 0.0, bessel_lp: float = 0.0) -> bool:
        try:
            if pmt:
                print('Setting up device...')
                print('PMT voltage control...')
                # Set upper and lower limit for PMT control voltage via Aux Out 1 of MFLI
                self.daq.setDouble(self.devPath + 'auxouts/0/limitlower', self.pmt_low_limit)
                self.daq.setDouble(self.devPath + 'auxouts/0/limitupper', self.pmt_high_limit)
                # Set output of Aux Out 1 to Manual
                self.daq.setInt(self.devPath + 'auxouts/0/outputselect', -1)
                self.set_PMT_voltage(0.0, False)
                self.set_input_range(3.0)

            if ch1:
                print('Channel 1...')
                # Channel 1 (AC, CD)
                self.daq.setInt(self.devPath + 'demods/0/adcselect', 0)
                self.daq.setInt(self.devPath + 'extrefs/0/enable', 0)
                self.daq.setDouble(self.devPath + 'demods/0/phaseshift', self.phaseoffset)
                self.daq.setInt(self.devPath + 'demods/0/oscselect', 0)
                self.daq.setDouble(self.devPath + 'sigins/0/scaling', 1)
                # filter timeconst
                self.daq.setInt(self.devPath + 'demods/0/order', self.filter_order)
                self.daq.setDouble(self.devPath + 'demods/0/timeconstant', self.time_const)
                # transfer rate
                self.daq.setDouble(self.devPath + 'demods/0/rate', self.sampling_rate)
                self.daq.setInt(self.devPath + 'demods/0/enable', 1)

            if ch2:
                print('Channel 2...')
                # Channel 2 (ExtRef)
                self.daq.setInt(self.devPath + 'demods/1/adcselect', 8)
                self.daq.setInt(self.devPath + 'extrefs/0/enable', 1)
                # deactivate data transfer
                self.daq.setInt(self.devPath + 'demods/1/enable', 0)

            if ch3:
                print('Channel 3...')
                # Channel 3 (DC, 0 Hz)
                self.daq.setInt(self.devPath + 'demods/2/adcselect', 0)
                self.daq.setDouble(self.devPath + 'oscs/1/freq', 0)
                self.daq.setDouble(self.devPath + 'demods/2/phaseshift', self.dc_phaseoffset)
                self.daq.setInt(self.devPath + 'demods/2/order', self.filter_order)
                self.daq.setDouble(self.devPath + 'demods/2/timeconstant', self.time_const)
                self.daq.setDouble(self.devPath + 'demods/2/rate', self.sampling_rate)
                self.daq.setInt(self.devPath + 'demods/2/enable', 1)

            if ch4:
                print('Channel 4...')
                # Channel 4 (CD, Linear Dichroism)
                self.daq.setInt(self.devPath + 'extrefs/1/enable', 0)
                self.daq.setInt(self.devPath + 'demods/3/adcselect', 0)
                self.daq.setDouble(self.devPath + 'demods/3/phaseshift', self.phaseoffset + self.rel_lp_phaseoffset)
                self.daq.setInt(self.devPath + 'demods/3/oscselect', 0)
                self.daq.setInt(self.devPath + 'demods/3/harmonic', 2)
                self.daq.setDouble(self.devPath + 'sigins/0/scaling', 1)
                # filter timeconst
                self.daq.setInt(self.devPath + 'demods/3/order', self.filter_order)
                self.daq.setDouble(self.devPath + 'demods/3/timeconstant', self.time_const)
                # transfer rate
                self.daq.setDouble(self.devPath + 'demods/3/rate', self.sampling_rate)
                self.daq.setInt(self.devPath + 'demods/3/enable', 1)

            if daqm:
                print('Data Acquisition Module...')
                self.daq.setInt(self.devPath + 'daq/0/enable', 1)
                self.daq.sync()

            if scp:
                print('Oscilloscope...')
                self.daq.setInt(self.devPath + 'scopes/0/enable', 1)
                self.daq.sync()

            self.bessel_corr = bessel
            self.bessel_corr_lp = bessel_lp
            return True
        except Exception as e:
            print('Error setting up device: {}'.format(str(e)))
            return False

    def set_PMT_voltage(self, voltage: float, sync: bool = True):
        self.pmt_volt = voltage
        self.daq.setDouble(self.devPath + 'auxouts/0/output', voltage)
        if sync:
            self.daq.sync()

    def set_input_range(self, range_value: float, sync: bool = True):
        self.signal_range = range_value
        self.daq.setDouble(self.devPath + 'sigins/0/range', range_value)
        if sync:
            self.daq.sync()

    def set_dwell_time(self, dwell_time: float):
        self.dwell_time = dwell_time
        self.data_set_size = int(np.ceil(self.dwell_time * self.sampling_rate))

    def set_phaseoffset(self, f: float):
        self.phaseoffset = f
        self.daq.setDouble(self.devPath + 'demods/0/phaseshift', self.phaseoffset)
        self.daq.setDouble(self.devPath + 'demods/3/phaseshift', self.phaseoffset)
        self.daq.sync()

    def start_scope(self):
        self.daq.setInt(self.devPath + 'scopes/0/enable', 1)
        self.daq.sync()

    def read_scope(self):
        data = self.daq.scope_snapshot(0)

        max_volt = 0.0
        avg_volt = 0.0
        if self.devPath + 'scopes/0/wave' in data:
            if 'wave' in data[self.devPath + 'scopes/0/wave'][0][0]:
                for chunk in data[self.devPath + 'scopes/0/wave'][0][0]['wave']:
                    max_volt = max(max_volt, chunk.max())
                    avg_volt = statistics.mean(chunk)
            else:
                max_volt = float('nan')
                avg_volt = float('nan')
        else:
            max_volt = float('nan')
            avg_volt = float('nan')

        return [max_volt, avg_volt]

    def stop_scope(self):
        self.daq.setInt(self.devPath + 'scopes/0/enable', 0)
        self.daq.sync()

    def set_extref_active(self, osc_index: int, b: bool):
        if b:
            i = 1  # on
        else:
            i = 0  # off
        self.daq.setInt(self.devPath + 'extrefs/' + str(osc_index) + '/enable', i)

    def read_data(self, ext_abort_flag: list) -> dict:
        def np_array_tail(arr: np.array, n: int):
            if n == 0:
                return arr[0:0]
            else:
                return arr[-n:]

        def subscribe_to_nodes(paths):
            for path in paths:
                self.daq.subscribe(path)

        def prepare_nodes(paths):
            for path in paths:
                self.daq.poll(0)

        def poll_data(paths) -> np.array:
            poll_time_step = min(0.1, self.dwell_time * 1.3)

            raw_xy = [[[], []], [[], []], [[], []]]  # array_x = sample (0, 2, 3), array_y = x, y
            filtered_xy = [[], []]  # array_x = sample, array_y = x, y

            data_count = 0
            data_per_step = poll_time_step * self.sampling_rate
            expected_poll_count = np.ceil(self.data_set_size / data_per_step)

            subscribe_to_nodes(paths)

            i = 0
            while (data_count < self.data_set_size) and not ext_abort_flag[0] and (i < expected_poll_count + 10):
                prepare_nodes(paths)
                data_chunk = self.daq.poll(poll_time_step, 100, 0, True)

                if is_data_complete(data_chunk, self.node_paths):
                    for j in range(0, 3):
                        raw_xy[j][0].extend(data_chunk[self.node_paths[j]]['timestamp'])
                        raw_xy[j][1].extend(data_chunk[self.node_paths[j]]['value'])

                last_overlap = np.intersect1d(np.intersect1d(np.array(raw_xy[0][0]), np.array(raw_xy[1][0])),
                                              np.array(raw_xy[2][0]))
                data_count = last_overlap.size

                if self.data_set_size - data_count < data_per_step:
                    poll_time_step = max(math.ceil((self.data_set_size - data_count) / self.sampling_rate * 1.2), 0.025)

                i += 1

            self.daq.unsubscribe('*')

            overlap_timestamps = np_array_tail(last_overlap, int(self.data_set_size))

            for k in range(0, 3):
                overlap_bools = np.isin(np.array(raw_xy[k][0]), overlap_timestamps)
                filtered_xy[0].extend(np.array(raw_xy[k][0])[overlap_bools])
                filtered_xy[1].extend(np.array(raw_xy[k][1])[overlap_bools])

            return np.array(filtered_xy)

        def get_sign(theta):
            if np.isnan(theta):
                return 0
            else:
                return np.sign(theta)

        def is_data_complete(chunk, paths) -> bool:
            result = True
            for path in paths:
                result = result and path in chunk

            return result

        def get_r(xy: np.array) -> np.array:
            return np.sqrt(xy[0] ** 2 + xy[1] ** 2)

        def get_theta(xy: np.array) -> np.array:
            return np.arctan2(xy[1], xy[0])

        def get_nan_filter(raw: np.array) -> np.array:
            nan = [True for _ in range(0, raw[0, 0].shape[0])]
            for a in range(0, raw.shape[0]):
                for b in range(0, raw.shape[1]):
                    nan = np.logical_and(nan, np.logical_not(np.isnan(raw[a, b])))
            return nan

        def apply_nan_filter(raw: np.array, nan: np.array) -> np.array:
            for a in range(0, raw.shape[0]):
                for b in range(0, raw.shape[1]):
                    raw[a, b] = raw[a, b][nan]
            return raw

        self.log('Starting data acquisition. ({} s)'.format(self.dwell_time))
        error = False

        raw_data = poll_data(self.node_paths)
        no_data = len(raw_data[0]) == 0

        if not no_data:
            nan_filter = get_nan_filter(raw_data)
            all_nan = not nan_filter.any()

            if not all_nan:
                raw_data = apply_nan_filter(raw_data, nan_filter)

                ac_raw = get_r(raw_data[0])
                ac_theta = get_theta(raw_data[0])

                dc_raw = get_r(raw_data[1])
                dc_theta = get_theta(raw_data[1])

                cd_raw = get_r(raw_data[2])
                cd_theta = get_theta(raw_data[2])

                sgn = np.vectorize(get_sign)

                ac = np.multiply(ac_raw, sgn(ac_theta)) * self.sqrt2 * self.bessel_corr
                dc = np.multiply(dc_raw, sgn(dc_theta)) / self.sqrt2
                cd = np.multiply(cd_raw, sgn(cd_theta)) * self.sqrt2 * self.bessel_corr

                if ac.shape[0] > 0:
                    return {'success': True,
                            'data': [
                                np.average(dc),
                                np.std(dc),
                                np.average(ac),
                                np.std(ac),
                                np.average(cd),
                                np.std(cd)]}
                else:
                    error = True
                    self.log(
                        'Error during calculation of corrected values and glum! Returning zeros. Printing raw data.',
                        True)
                    print(raw_data)
            else:
                error = True
                self.log(
                    'Error: All NaN in at least one of the channels (AC, DC, Theta, CD or CD theta)! Returning zeros. Printing raw data.',
                    True)
                print(raw_data)
        else:
            error = True
            self.log('Missing data from MFLI. Returning zeros.', True)
        if error:
            return {'success': False,
                    'data': np.zeros(6)}

    def get_pmt_spectra(self) -> Tuple[np.ndarray, np.ndarray]:
        self.setup_device(pmt=True, ch1=False, ch2=False, ch3=False, ch4=False, daqm=True, scp=False)

        # Configure the PMT settings and acquire the spectra data
        self.set_PMT_voltage(1.0)  # Set the PMT control voltage

        # Wait for settling time or perform any necessary initialization steps
        time.sleep(10)  # Wait for 10 seconds

        # Acquire the spectra data
        spectra_data = self.read_data()

        # Extract the relevant PMT spectra from the acquired data
        pmt_spectra = spectra_data['data'][2]  # Assuming the PMT spectra is at index 2

        # Optionally, you can also retrieve the x-axis values for the PMT spectra
        x_values = np.arange(len(pmt_spectra))  # Generate x-axis values based on the data length

        return x_values, pmt_spectra

    def read_ac_theta(self, ext_abort_flag: list) -> float:
        path = self.devPath + 'demods/0/sample'
        theta = []
        self.ac_theta_avg = 0.0
        self.ac_theta_count = 0

        self.log('Recording AC theta...')

        self.daq.subscribe(path)

        while not ext_abort_flag[0]:
            data_chunk = self.daq.poll(0.1, 50, 0, True)
            if path in data_chunk:
                x = data_chunk[path]['x']
                y = data_chunk[path]['y']
                new_theta = np.arctan2(y, x) * 180 / np.pi
                theta.extend(new_theta)
                self.ac_theta_avg = np.average(theta)
                self.ac_theta_count = len(theta)

        self.daq.unsubscribe('*')
        self.log('Stop recording AC theta...')
        ext_abort_flag[0] = False
        return self.ac_theta_avg

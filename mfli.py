"""MFLI coding: As for the integration with the MFLI Lock-in Amplifier, you would need to feed the reference signal
output from the PEM controller into the reference input of the MFLI. Then, in the MFLI's control software or
programming interface, you would set up a demodulator to use this reference signal for phase-sensitive detection.
This allows the MFLI to measure the amplitude and phase of the signal from the photomultiplier tube (PMT) at the
modulation frequency of the PEM."""
from PyQt5.QtCore import pyqtSlot, pyqtSignal
from debug import LogObject, VisaDevice
import zhinst.core
import zhinst.utils
import time
import math
import numpy as np
import statistics
import queue


from IPython.core.interactiveshell import InteractiveShell

InteractiveShell.ast_node_interactivity = "all"


class MFLI(VisaDevice):
    sampling_rate = 104.6  # s-1 data transfer rate
    time_const = 0.00811410938  # s, time constant of the low-pass filter of the lock-in amplifier
    filter_order = 3

    # Low and high limit of control voltage for PMT
    pmt_low_limit = 0.0  # V
    pmt_high_limit = 1.1  # V

    pmt_volt = 0.0  # V control voltage of the PMT
    signal_range = 3.0  # V, default signal range
    dwell_time = 0.5  # s, default acquisition time per point
    dwell_time_scaling = 1
    data_set_size = np.ceil(dwell_time * sampling_rate)  # number of data points per acquisition

    dc_phaseoffset = 0.0  # degrees, results in DC phase at +90 or -90 degrees
    # phaseoffset of the demodulators with respect to the PEM reference signal
    # will be loaded from previous measurements and can be calibrated during runtime
    phaseoffset = 158.056  # degrees
    # relative phaseoffset of 2f component vs. 1f component
    rel_lp_phaseoffset = -22  # degrees

    bessel_corr = 0.0  # correction factor for the sin(A sin(x)) modulation of the PEM, will be obtained from PEM
    bessel_corr_lp = 0.0  # correction factor for linear component, will be obtained from PEM

    # variables necessary for phaseoffset calibration
    ac_theta_avg = 0.0
    ac_theta_count = 0

    sqrt2 = np.sqrt(2)
    no_path = False
    no_wave = False


    def __init__(self, ID: str, log_name: str, log_queue: queue.Queue, logObject=None):
        super().__init__(logObject=logObject, log_name=log_name)
        self.scope = None
        self.devID = ID  # ID of the device, for example dev3902
        self.devPath = '/' + self.devID + '/'
        self.log_name = log_name
        self.log_queue = log_queue

    def connect(self) -> bool:
        try:
            # Device Discovery
            d = zhinst.core.ziDiscovery()
            self.props = d.get(d.find(self.devID))

            # Start API Session
            self.daq = zhinst.core.ziDAQServer(self.props['serveraddress'], self.props['serverport'],
                                               self.props['apilevel'])
            self.daq.connectDevice(self.devID, self.props['connected'])

            # Issue a warning and return False if the release version of the API used in the session (daq) does not have the same release version as the Data Server (that the API is connected to).
            zhinst.utils.utils.api_server_version_check(self.daq)
            return True
        except Exception as e:
            self.log('Error connecting: {}'.format(str(e)), True)
            return False

    def disconnect(self):
        self.log('Disconnecting...')
        try:
            self.daq.disconnectDevice(self.devID)
        except Exception as e:
            self.log('Error during disconnecting: {}'.format(str(e)), True)

    # initialize the api session for data acquisition (daq)
    def setup_for_daq(self, bessel, bessel_lp) -> bool:
        return self.setup_device(True, True, True, True, False, bessel, bessel_lp)

    # initialize the api session for monitoring the oscilloscope (used for signal tuning)
    def setup_for_scope(self) -> bool:
        return self.setup_device(False, False, False, False, True)

    def setup_device(self, pmt: bool, ch1: bool, ch2: bool, daqm: bool, scp: bool,
                     bessel: float = 0.0, bessel_lp: float = 0.0) -> bool:
        try:
            if pmt:
                self.log('Setting up device...')
                self.log('PMT voltage control...')
                # Set upper and lower limit for PMT control voltage via Aux Out 1 of MFLI
                self.daq.setDouble(self.devPath + 'auxouts/0/limitlower', self.pmt_low_limit)
                self.daq.setDouble(self.devPath + 'auxouts/0/limitupper', self.pmt_high_limit)
                # Set output of Aux Out 1 to Manual
                self.daq.setInt(self.devPath + 'auxouts/0/outputselect', -1)
                self.set_PMT_voltage(0.0, False)
                self.set_input_range(3.0)

            if ch1:
                self.log('Channel 1...')
                # Channel 1 (AC, CD) #TODO: test at 0 Hz
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
                self.log('Channel 2...')
                #Channel 2 (ExtRef)
                self.daq.setInt(self.devPath+'demods/1/adcselect', 8)
                self.daq.setInt(self.devPath+'extrefs/0/enable', 1)
                #deactivate data transfer
                self.daq.setInt(self.devPath+'demods/1/enable', 0)


            if daqm:
                self.node_paths = [self.devPath + 'demods/0/sample']
                self.bessel_corr = bessel
                self.bessel_corr_lp = bessel_lp

            if scp:
                self.log('Oscilloscope...')
                self.scope = self.daq.scopeModule()
                self.scope.set('averager/weight', 0)
                self.scope.set('averager/restart', 0)
                self.scope.set('mode', 1)
                # set scope sampling rate to 60 MHz
                self.daq.setInt(self.devPath + 'scopes/0/time', 0)
                self.daq.setInt(self.devPath + 'scopes/0/trigenable', 0)
                self.daq.setInt(self.devPath + 'scopes/0/enable', 0)

                self.scope.unsubscribe('*')
                self.scope.subscribe(self.devPath + 'scopes/0/wave')
                self.daq.setDouble(self.devPath + 'scopes/0/length', 4096)
                self.scope.set('/historylength', 1)
                self.daq.setInt(self.devPath + 'scopes/0/enable', 0)
                self.daq.setInt(self.devPath + 'scopes/0/channels/0/inputselect', 0)

            # Perform a global synchronisation between the device and the data server:
            # Ensure that the settings have taken effect on the device before issuing
            # the getSample() command.
            self.daq.sync()

            self.log('Setup complete.')
            return True
        except Exception as e:
            self.log('Error in MFLI setup: ' + str(e), True)
            return False

    def set_PMT_voltage(self, volt: float, autorange: bool = True):
        self.log('')
        self.log('Setting PMT voltage to: {:.3f} V'.format(volt))
        if (volt <= self.pmt_high_limit) and (volt >= self.pmt_low_limit):
            self.daq.setDouble(self.devPath + 'auxouts/0/offset', volt)
            self.pmt_volt = volt
            self.daq.sync()

            self.log('Please wait 10 s for stabilization before starting a measurement.')
            if autorange:
                time.sleep(2)
                self.set_input_range(f=0.0, auto=True)
        else:
            self.log("PMT voltage not set because out of range (0.0-1.1 V): " + str(volt) + " V")

    def set_input_range(self, f: float, auto: bool = False):
        if auto:
            self.daq.setInt(self.devPath + 'sigins/0/autorange', 1)
        else:
            self.daq.setDouble(self.devPath + 'sigins/0/range', f)
        self.daq.sync()
        time.sleep(1.5)
        self.daq.sync()
        self.signal_range = self.daq.getDouble(self.devPath + 'sigins/0/range')
        self.log('')
        self.log('Signal range adjusted to {:.3f} V.'.format(self.signal_range))

    def set_dwell_time(self, t: float):
        self.log('')
        self.log('Setting dwell time to {:.0f} s.'.format(t))
        # Min. dwell time is 1/sampling rate/dwell_time_scaling to collect 1 datapoint per data chunk
        self.dwell_time = max(t, 1 / self.sampling_rate)  # TODO Adjust polling duration?
        self.data_set_size = np.ceil(self.dwell_time * self.sampling_rate)
        # self.daq_module.set('duration', self.dwell_time)
        # self.daq_module.set('grid/cols', self.data_set_size)
        # self.daq.sync()
        self.log('Dwell time set to {} s = {:.0f} data points.'.format(self.dwell_time, self.data_set_size))

    def set_phaseoffset(self, f: float):
        self.phaseoffset = f
        self.daq.setDouble(self.devPath + 'demods/0/phaseshift', self.phaseoffset)
        self.daq.sync()
        self.log('Phase offset set to {:.3f} deg'.format(self.phaseoffset))

    # activate oscilloscope
    def start_scope(self):
        self.scope.set('clearhistory', 1)
        self.scope.execute()
        self.daq.setInt(self.devPath + 'scopes/0/enable', 1)
        self.daq.sync()

        # read data from oscilloscope and return max. and avg. signal

    def read_scope(self):
        if self.scope is None:
            # Handle this case, maybe raise a more descriptive error or log a warning
            raise ValueError("Scope has not been initialized!")
        else:
            data = self.scope.read(True)

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
        self.scope.finish()
        self.daq.setInt(self.devPath + 'scopes/0/enable', 0)
        self.daq.sync()

        # deactivate external reference for a certain oscillator. Used for measurements without modulation by PEM

    def set_extref_active(self, osc_index: int, b: bool):
        if b:
            i = 1  # on
        else:
            i = 0  # off
        self.daq.setInt(self.devPath + 'extrefs/' + str(osc_index) + '/enable', i)

    # reads demodulator data from MFLI and returns calculated gabs etc.
    # This function is run in a separate thread, that can be aborted by ext_abort_flag[0]
    # provided by Controller instance
    def read_data(self, ext_abort_flag: list) -> dict:

        # returns the last n elements of a numpy array
        def np_array_tail(arr: np.array, n: int):
            if n == 0:
                return arr[0:0]
            else:
                return arr[-n:]

        def subscribe_to_nodes(paths):
            # Subscribe to data streams
            for path in paths:
                self.daq.subscribe(path)
                # clear buffer
            self.daq.sync()

            # ensures that all nodes send data regardless of whether the values changed or not

        def prepare_nodes(paths):
            for path in paths:
                self.daq.getAsEvent(path)

        def poll_data(paths) -> np.array:
            poll_time_step = min(0.1, self.dwell_time * 1.3)

            raw_xy = [[[], [], []]]  # added one more sublist for avg voltage
            filtered_xy = [[[], []]]  # added one more sublist for filtered avg voltage

            data_count = 0
            data_per_step = poll_time_step * self.sampling_rate
            expected_poll_count = np.ceil(self.data_set_size / data_per_step)

            # start data buffering
            subscribe_to_nodes(paths)

            i = 0
            while (data_count < self.data_set_size) and not ext_abort_flag[0] and (i < expected_poll_count + 10):
                prepare_nodes(paths)
                # collects data for poll_time_step
                data_chunk = self.daq.poll(poll_time_step, 100, 0, True)

                if is_data_complete(data_chunk, self.node_paths):
                    # add new data to raw_xy
                    raw_xy[0][0].extend(data_chunk[self.node_paths[0]]['timestamp'])
                    raw_xy[0][1].extend(data_chunk[self.node_paths[0]]['x'])
                    raw_xy[0][2].extend(data_chunk[self.node_paths[0]]['y'])

                # find overlap of timestamps between the three samples
                last_overlap = np.array(raw_xy[0])
                data_count = last_overlap.size

                # if only a few values are missing, reduce the poll time accordingly
                if self.data_set_size - data_count < data_per_step:
                    poll_time_step = max(math.ceil((self.data_set_size - data_count) / self.sampling_rate * 1.2), 0.025)

                i += 1
            # Stop data buffering
            self.daq.unsubscribe('*')

            # identify the timestamps that are identical in all three samples, reduce number of data points to data_set_size (to avoid different numbers of data points at different wavelengths)
            overlap_timestamps = np_array_tail(last_overlap, int(self.data_set_size))

            # filter the x, y, and avg voltage data
            # create a list of bools that marks whether a timestamp is in a sample data set or not
            overlap_bools = np.isin(np.array(raw_xy[0][0]), overlap_timestamps)
            # save the filtered x, y, and avg voltage data in filtered_xy
            filtered_xy[0][0] = np.array(raw_xy[0][1])[overlap_bools]
            filtered_xy[0][1] = np.array(raw_xy[0][2])[overlap_bools]

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

        # calculate amplitude R from X and Y
        def get_r(xy: np.array) -> np.array:
            return np.sqrt(xy[0] ** 2 + xy[1] ** 2)

        # calculate phase theta from X and Y
        def get_theta(xy: np.array) -> np.array:
            return np.arctan2(xy[1], xy[0])

            # generate a filter array of bools that filters out NaN values, False = NaN-value at this index

        def get_nan_filter(raw: np.array) -> np.array:
            nan = [True for _ in range(0, raw[0, 0].shape[0])]
            for a in range(0, raw.shape[0]):
                for b in range(0, raw.shape[1]):
                    nan = np.logical_and(nan, np.logical_not(np.isnan(raw[a, b])))
            return nan

        # applies the NaN filter to the individual data
        def apply_nan_filter(raw: np.array, nan: np.array) -> np.array:
            for a in range(0, raw.shape[0]):
                for b in range(0, raw.shape[1]):
                    raw[a, b] = raw[a, b][nan]
            return raw

        self.log('Starting data aquisition. ({} s)'.format(self.dwell_time))
        error = False

        # Format raw_data: array_x: AC, DC, LP, array_y: x, y
        raw_data = poll_data(self.node_paths)
        no_data = len(raw_data[0][0]) == 0

        if not no_data:
            nan_filter = get_nan_filter(raw_data)
            all_nan = not nan_filter.any()

            if not all_nan:
                raw_data = apply_nan_filter(raw_data, nan_filter)

                ac_raw = get_r(raw_data[0][:2])  # first two sets of data
                dc_raw = np.average(ac_raw)  # third set of data

                ac_theta = get_theta(raw_data[0])

                sgn = np.vectorize(get_sign)

                # apply sign, correct raw values (Vrms->Vpk) and Bessel correction for AC
                ac = np.multiply(ac_raw, sgn(ac_theta)) * self.sqrt2 * self.bessel_corr
                dc = dc_raw
                # The following are set to dc to be calculated in the controller
                CD = dc
                I_L = dc
                I_R = dc
                gabs = dc
                m_ellip = dc
                ellip = dc

                # print out the average
                # The error of the values is calculated as the standard deviation in the data set that is collected for one wavelength
                if ac.shape[0] > 0:
                    return {'success': True,
                            'data': [
                                np.average(dc),
                                np.std(dc),
                                np.average(ac),
                                np.std(ac),
                                np.average(CD),
                                np.std(CD),
                                np.average(I_L),
                                np.std(I_L),
                                np.average(I_R),
                                np.std(I_R),
                                np.average(gabs),
                                np.std(gabs),
                                np.average(m_ellip),
                                np.std(m_ellip),
                                np.average(ellip),
                                np.std(ellip)]}

                else:
                    error = True
                    self.log(
                        'Error during calculation of corrected values and gabs! Returning zeros. Printing raw data.',
                        True)
                    print(raw_data)
            else:
                error = True
                self.log(
                    'Error: All NaN in at least one of the channels (AC, DC, Theta, LP or LP theta)! Returning zeros. '
                    'Printing raw data.',
                    True)
                print(raw_data)
        else:
            error = True
            self.log('Missing data from MFLI. Returning zeros.', True)
        if error:
            return {'success': False,
                    'data': np.zeros(4)}

    # reads the phase of CPL, returns the average value
    def read_ac_theta(self, ext_abort_flag: list) -> float:
        path = self.devPath + 'demods/0/sample'
        theta = []
        self.ac_theta_avg = 0.0
        self.ac_theta_count = 0

        self.log('Recording AC theta...')

        # This function uses poll instead of read for performance reasons. Also no temporal alignment of the data is
        # required
        self.daq.subscribe(path)
        self.daq.sync()

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
        self.daq.sync()
        self.log('Stop recording AC theta...')
        ext_abort_flag[0] = False
        return self.ac_theta_avg

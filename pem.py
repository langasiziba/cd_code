"""The following code is specifically designed to control the PEM. The PEM will circularly polarize the light"""

from debug import VisaDevice
from debug import ECommError
import pyvisa
import re
import math
import scipy.special
import queue


class PEM(VisaDevice):
    # A class to control a Hinds PEM controller 200 V01 device

    def __init__(self, name='ASRL3::INSTR', model='Hinds PEM controller 200 V01', log_name='PEM', retardation=0.25):
        super().__init__()
        self.name = name
        self.model = model
        self.log_name = log_name
        self.retardation = retardation
        self.float_acc = 0.025

        # Correction factors
        self.bessel_corr = 1 / (2 * scipy.special.jv(1, self.retardation * 2 * scipy.pi))
        self.bessel_corr_lp = 1 / (2 * scipy.special.jv(2, self.retardation * 2 * scipy.pi))

    def initialize(self, rm: pyvisa.ResourceManager, log_queue: queue.Queue) -> bool:
        self.rm = rm
        self.log_queue = log_queue
        try:
            self.inst = self.rm.open_resource(self.name, timeout=10)
            self.log('Successfully connected to: ' + self.name)
            self.inst.write_termination = ';'
            self.inst.read_termination = '\n'
            self.inst.baud_rate = 250000
            self.inst.timeout = 3000  # setting timeout
            if self.check_response():
                self.log("Initialization successful!")
                self.log("Test successful!")
                self.log("Retardation = {}.".format(self.retardation))
                self.log("Bessel correction factor = {:.4f}.".format(self.bessel_corr))
                self.initialized = True  # The initialized flag should be accessed with self
                return True
            else:
                self.log("Fail to initialize.", error=True)  # Emit a log signal for initialization failure
                self.log("Test failed. Try reconnecting PEM.")
                return False
        except Exception as e:
            self.log("Error connecting to: " + self.name + ". " + str(e), error=True, no_id=False)
            return False

    def extract_value(self, s: str) -> str:
        return re.search(r'\((.*?)\)', s).group(1)

    # Tests if the PEM is behaving as expected
    def check_response(self) -> bool:
        r1 = self.get_id()
        r2 = self.extract_value(self.set_active(True))
        return (r1 == self.model) and (int(r2) == 1)

    def retry_query(self, q: str, grp: str, isset: bool = False, value=0, isfloat: bool = False, n: int = 3) -> str:
        """
        Retry the query n times and verify the result against expected values.

        Args:
            q (str): Query string to be executed.
            grp (str): Expected group value for comparison.
            set (bool): Flag indicating whether it's a set operation.
            value (int/float): Expected value for comparison.
            isfloat (bool): Flag indicating whether the value should be treated as a float.
            n (int): Number of retry attempts.
        Returns:
            str: The result string of the query.
        Raises:
            ECommError: If the query fails after the maximum number of retries.
        """
        success = False
        i = 0
        s = ''

        while not success and i < n:
            try:
                i += 1
                s = self.log_query(q)
                r = re.search(r'\[(.*?)\]\((.*?)\)', s)

                if isset:
                    if isfloat:
                        success = (r.group(1) == grp) and math.isclose(float(r.group(2)), value, abs_tol=self.float_acc)
                    else:
                        success = (r.group(1) == grp) and (int(r.group(2) == value))
                else:
                    success = (r.group(1) == grp)
            except pyvisa.VisaIOError as e:
                self.log("{}: {:d}) Error with query {}: {}.".format(self.name, i, q, str(e)), True)
                success = False

        if not success:
            raise ECommError("Error @{}: Error with query {} (tried {:d} times).".format(self.name, q, i), True)

        return s

    # set PEM to active mode
    def set_active(self, active: bool) -> str:
        query = ':SYS:PEMO {:d}'.format(int(active == True))
        return self.retry_query(q=query, grp='PEMOUT')

    # set PEM to idle mode
    def set_idle(self, idle: bool) -> str:
        query = ':SYS:IDLE {:d}'.format(int(idle == True))
        return self.retry_query(q=query, grp='PEMOUT')

    # get PEM's ID
    def get_id(self) -> str:
        id_string = self.retry_query(q='*IDN?', grp='IDN')
        return self.extract_value(id_string)

    # check if PEM is stable
    def get_stable(self) -> str:
        stable_string = self.retry_query(q=':MOD:STABLE?', grp='STABLE')
        return self.extract_value(stable_string)

    def get_freq(self) -> str:
        freq_string = self.retry_query(q=':MOD:FREQ?', grp='FREQUENCY')
        return self.extract_value(freq_string)

    # get amplitude and range as well as set them
    def get_amp(self) -> str:
        amp_string = self.retry_query(q=':MOD:AMP?', grp='AMP')
        return self.extract_value(amp_string)

    def set_amp(self, f: float) -> str:
        query = ':MOD:AMP {:.2f}'.format(f)
        return self.retry_query(q=query, grp='AMP', isset=True, value=f, isfloat=True)

    def get_amp_range(self) -> str:
        return self.retry_query(q=':MOD:AMPR?', grp='AMPR')

    def get_amp_range_low(self) -> str:
        s = self.get_amp_range()
        return re.search(r'\((.*?),(.*?)\)', s).group(1)

    def get_amp_range_high(self) -> str:
        s = self.get_amp_range()
        return re.search(r'\((.*?),(.*?)\)', s).group(2)

    # get and set drive voltage
    def get_drive(self) -> str:
        drive_string = self.retry_query(q=':MOD:DRV?', grp='DRIVE')
        return self.extract_value(drive_string)

    def set_drive(self, f: float) -> str:
        query = ':MOD:DRV {:.2f}'.format(f)
        return self.retry_query(q=query, grp='DRIVE', isset=True, value=f, isfloat=True)

    # Sets wavelength and returns current wavelength value
    def set_nm(self, nm: float) -> str:
        return self.extract_value(self.set_amp(nm * self.retardation))

    def get_nm(self, nm: float):
        return float(self.get_amp()) / self.retardation

    # get the current and the phase error (0-1 scale)
    def get_cp_error(self) -> str:
        return self.retry_query(q=':SYS:CPE?', grp='CPE')

    def get_current_error(self) -> str:
        s = self.get_cp_error()
        return re.search(r'\((.*?),(.*?)\)', s).group(1)

    def get_phase_error(self) -> str:
        s = self.get_cp_error()
        return re.search(r'\((.*?),(.*?)\)', s).group(2)

    def get_voltage_info(self) -> str:
        return self.retry_query(q=':SYS:VC?', grp='VC')

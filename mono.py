from debug import VisaDevice
from debug import ECommError
import pyvisa
import queue


class Monoi(VisaDevice):
    # Edit these for different model
    name = 'ASRL4::INSTR'
    model = 'SP-2-150i'
    serial = '21551955'
    ok = 'ok'
    log_name = 'MONI'

    def initialize(self, rm: pyvisa.ResourceManager, log_queue: queue.Queue) -> bool:
        """
        Initializes the monochromator device.
        """

        self.rm = rm
        self.log_queue = log_queue

        try:
            self.inst = self.rm.open_resource(self.name, timeout=10)
            self.log('Successfully connected to: ' + self.name)
            self.inst.read_termination = '\r\n'
            self.inst.write_termination = '\r'
            self.inst.baud_rate = 9600
            self.inst.timeout = 5000  # ms
        except pyvisa.VisaIOError as e:
            self.log("Error connecting to: " + self.name + ", try using a different USB port: " + str(e), True)
            return False

        if self.check_response():
            self.log("Test successful!")
            initialized = True
            return True
        else:
            self.log("Test failed. Try restarting PC or connecting via a different USB port.", True)
            return False

    def check_response(self) -> bool:
        """
        Checks the monochromator's response and functionality.

        Returns:
            bool: True if the response is successful, False otherwise.
        """
        r1 = self.log_query('MODEL')
        r2 = self.log_query('SERIAL')
        r3 = self.log_query('MODEL')
        r4 = self.log_query('SERIAL')
        self.log("Move to 1000 nm...")
        r5 = self.log_query('1000 GOTO')
        self.log("Move to 0 nm...")
        r6 = self.log_query('0 GOTO')

        return (r1 == r3) and (r2 == r4) and (self.model in r1) and (self.serial in r2) and (self.ok in r5) and (
                    self.ok in r6)

    def retry_query(self, q: str, n: int = 3) -> str:
        """
        Retries the query  three times and returns the response.
        Returns:
            str: The response string.
        """
        success = False
        i = 0
        s = ""

        while (not success) and (i < n):
            i += 1
            try:
                s = self.log_query(q)
                success = self.ok in s
            except pyvisa.VisaIOError as e:
                self.log("{:d}) Error with query {} @{}: {}.".format(i, q, self.name, str(e)), True)
                success = False

        # If the query fails after the maximum number of retries.
        if not success:
            raise ECommError("Error @{} with query {} (tried {:d} times).".format(self.name, q, i), True)
        else:
            return s

    def get_model(self) -> str:
        # Retrieves the monochromator's model.
        return self.retry_query('MODEL')

    def get_serial(self) -> str:
        # Retrieves the monochromator's serial number.
        return self.retry_query('SERIAL')

    def get_nm(self) -> str:
        # Retrieves the current wavelength of the monochromator.
        return self.retry_query('?NM')

    def set_nm(self, nm: float) -> str:
        # Sets the monochromator's wavelength to the specified value.
        return self.retry_query('{:.2f} GOTO'.format(nm))

    # def scan_wavelengths(self, min_wavelength: float, max_wavelength: float, step: float):
    #     # Scans the monochromator's wavelength from the minimum to the maximum value with a specified step.
    #
    #     wavelength = min_wavelength
    #     while wavelength <= max_wavelength:
    #         self.log("Setting wavelength to {:.2f} nm...".format(wavelength))
    #         self.set_nm(wavelength)
    #         # Do your measurements or operations here

    #       wavelength += step

class Monoii(VisaDevice):
    # Edit these for different model
    name = 'ASRL4::INSTR'
    model = 'SP-2-150i'
    serial = '21551956'
    ok = 'ok'
    log_name = 'MONII'

    def initialize(self, rm: pyvisa.ResourceManager, log_queue: queue.Queue) -> bool:
        """
        Initializes the monochromator device.
        """

        self.rm = rm
        self.log_queue = log_queue

        try:
            self.inst = self.rm.open_resource(self.name, timeout=10)
            self.log('Successfully connected to: ' + self.name)
            self.inst.read_termination = '\r\n'
            self.inst.write_termination = '\r'
            self.inst.baud_rate = 9600
            self.inst.timeout = 5000  # ms
        except pyvisa.VisaIOError as e:
            self.log("Error connecting to: " + self.name + ", try using a different USB port: " + str(e), True)
            return False

        if self.check_response():
            self.log("Test successful!")
            initialized = True
            return True
        else:
            self.log("Test failed. Try restarting PC or connecting via a different USB port.", True)
            return False

    def check_response(self) -> bool:
        """
        Checks the monochromator's response and functionality.

        Returns:
            bool: True if the response is successful, False otherwise.
        """
        r1 = self.log_query('MODEL')
        r2 = self.log_query('SERIAL')
        r3 = self.log_query('MODEL')
        r4 = self.log_query('SERIAL')
        self.log("Move to 1000 nm...")
        r5 = self.log_query('1000 GOTO')
        self.log("Move to 0 nm...")
        r6 = self.log_query('0 GOTO')

        return (r1 == r3) and (r2 == r4) and (self.model in r1) and (self.serial in r2) and (self.ok in r5) and (
                    self.ok in r6)

    def retry_query(self, q: str, n: int = 3) -> str:
        """
        Retries the query  three times and returns the response.
        Returns:
            str: The response string.
        """
        success = False
        i = 0
        s = ""

        while (not success) and (i < n):
            i += 1
            try:
                s = self.log_query(q)
                success = self.ok in s
            except pyvisa.VisaIOError as e:
                self.log("{:d}) Error with query {} @{}: {}.".format(i, q, self.name, str(e)), True)
                success = False

        # If the query fails after the maximum number of retries.
        if not success:
            raise ECommError("Error @{} with query {} (tried {:d} times).".format(self.name, q, i), True)
        else:
            return s

    def get_model(self) -> str:
        # Retrieves the monochromator's model.
        return self.retry_query('MODEL')

    def get_serial(self) -> str:
        # Retrieves the monochromator's serial number.
        return self.retry_query('SERIAL')

    def get_nm(self) -> str:
        # Retrieves the current wavelength of the monochromator.
        return self.retry_query('?NM')

    def set_nm(self, nm: float) -> str:
        # Sets the monochromator's wavelength to the specified value.
        return self.retry_query('{:.2f} GOTO'.format(nm))
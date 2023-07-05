import tkinter as tk  # Import the Tkinter library for creating GUIs
from queue import Queue  # Import the Queue class from the queue module
from datetime import datetime  # Import the datetime class from the datetime module
import queue
import time
import pyvisa
import re
import math
import scipy.special

"""Detection of error in the PEM and monochromator behavior during tests"""


class ECommError(Exception):
    pass


"""This part of the code controls is the error log. Through the following program we are able to display an error
log using a central box and in the debug log that displays the error in the format [Error type][Date, Time][Error] This class 
will also be used to control error handling for the devices in the system"""


class LogObject:
    def __init__(self, log_name=''):  # Initialize the LogObject instance
        self.log_name = log_name
        self.initialized = False  # Initialize as False, to be set True when initialization of all devices is successful
        self.log_queue = Queue()

    def log(self, s: str, error: bool = False, no_id: bool = False):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Get the current date and time
        ss = '[{}] {}'.format(timestamp, s)
        if not no_id:
            ss = '[{}] {}'.format(self.log_name, ss)  # Add log name if no_id is False (initialized to false)
        print(ss)  # Print the log message

        # Check if there is an error or 'error' keyword in the message
        if error or 'error' in ss.lower():
            self.show_error_box(ss)  # Show error dialog if there is an error
            self.log_queue.put(ss)  # Add the log message to the queue even if it's an error message

        # If it's not an error message and log_queue is not None, add message to the queue
        elif not self.log_queue.empty():
            self.log_queue.put(ss)  # Add the log message to the queue

    def log_ask(self, q: str):  # Method for logging questions
        self.log('<< {}'.format(q))  # Log the question with '<<' added in front

    def log_answer(self, s: str):  # Method for logging answers
        self.log('>> {}'.format(s))  # Log the answer with '>>' added in front

    def show_error_box(self, s: str):  # Method for showing an error dialog (generated from tkinter)
        try:
            win = tk.Toplevel()  # Create a new window
            tk.Label(win, text=s, bg='white').pack()
            tk.Button(win, text='OK', command=win.destroy).pack()
            win.resizable(False, False)
            win.attributes('-topmost', 'true')
            win.configure(bg='white')
            self.place_central(win)
        except Exception as dialog_error:  # If an error occurs
            print("Error showing error dialog: ", dialog_error)  # Print an error message

    def place_central(self, win):
        win.attributes("-alpha", 0.0)
        win.update()

        ws = win.winfo_screenwidth()
        hs = win.winfo_screenheight()
        w = win.winfo_width()
        h = win.winfo_height()
        x = (ws / 2) - (w / 2)
        y = (hs / 2) - (h / 2)

        win.geometry('%dx%d+%d+%d' % (w, h, x, y))
        win.attributes("-alpha", 1.0)

    def close(self):
        self.log('Closing logger...')
        self.initialized = False
        self.log('Logger closed.')


"""The class below id designed to log errors from the devices and display them"""


class VisaDevice(LogObject):
    # A class to interact with a Visa device with logging capabilities

    def log_query(self, q: str) -> str:
        # Performs a query and logs the query and its response
        self.log_ask(q)
        s = self.inst.query(q)
        self.log_answer(s)
        return s

    def debug_query(self, q: str) -> None:
        # Performs a query for debugging purposes, with timeout handling
        self.inst.write(q)
        self.log_ask(q)
        start_time = time.time()
        while time.time() - start_time < self.inst.timeout / 1000:
            try:
                self.log_answer(self.inst.read_bytes(1))
            except pyvisa.VisaIOError:
                self.log("Debug query timeout.")
                break

    def close(self) -> None:
        # Closes the connection with the device
        self.log('Closing connection...')
        self.inst.close()
        self.log('Connection closed.')
        self.initialized = False


"""The following code is specifically designed to control the PEM. The PEM will circularly polarize the light"""


class PEM(VisaDevice):
    # A class to control a Hinds PEM controller 200 V01 device

    def init_pem(self, name='ASRL3::INSTR', model='Hinds PEM controller 200 V01', log_name='PEM', retardation=0.25):
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
            self.inst.timeout = 3000
            if self.check_response():
                self.log("Test successful!")
                self.log("Retardation = {}.".format(self.retardation))
                self.log("Bessel correction factor = {:.4f}.".format(self.bessel_corr))
                self.initialized = True  # The initialized flag should be accessed with self
                return True
            else:
                self.log("Test failed. Try restarting PC.")
                return False
        except Exception as e:
            self.log("Error connecting to: " + self.name + ". " + str(e), True)
            return False

    def extract_value(self, s: str) -> str:
        return re.search(r'\((.*?)\)', s).group(1)

    # Tests if the PEM is behaving as expected
    def check_response(self) -> bool:
        r1 = self.get_id()
        r2 = self.extract_value(self.set_active(True))
        return (r1 == self.model) and (int(r2) == 1)

    def retry_query(self, q: str, grp: str, isSet: bool = False, value=0, isFloat: bool = False, n: int = 3) -> str:
        success = False
        i = 0
        s = ''
        while (not success) and (i < 3):
            try:
                i += 1
                s = self.log_query(q)
                r = re.search(r'\[(.*?)\]\((.*?)\)', s)
                if isSet:
                    if isFloat:
                        success = (r.group(1) == grp) and (
                            math.isclose(float(r.group(2)), value, abs_tol=self.float_acc))
                    else:
                        success = (r.group(1) == grp) and (int(r.group(2) == value))
                else:
                    success = (r.group(1) == grp)
            except pyvisa.VisaIOError as e:
                self.log("{}: {:d}) Error with query {}: {}.".format(self.name, i, q, str(e)), True)
                success = False
        if not success:
            raise ECommError("Error @{}: Error with query {} (tried {:d} times).".format(self.name, q, i), True)
        else:
            return s


""" def set_active(self, active: bool) -> str:
        return self.retry_query(q=':SYS:PEMO {:d}'.format(int(active == True)), grp='PEMOUT')

    def set_idle(self, idle: bool) -> str:
        return self.retry_query(q=':SYS:IDLE {:d}'.format(int(idle == True)), grp='PIDLE')

    def get_id_raw(self) -> str:
        return self.retry_query(q='*IDN?', grp='IDN')

    def get_id(self) -> str:
        return self.extract_value(self.get_id_raw())

    def get_stable_raw(self) -> str:
        return self.retry_query(q=':MOD:STABLE?', grp='STABLE')

    def get_stable(self) -> str:
        return self.extract_value(self.get_stable_raw())

    def get_freq_raw(self) -> str:
        return self.retry_query(q=':MOD:FREQ?', grp='FREQUENCY')

    def get_freq(self) -> str:
        return self.extract_value(self.get_freq_raw())

    def get_amp_raw(self) -> str:
        return self.retry_query(q=':MOD:AMP?', grp='AMP')

    def get_amp(self) -> str:
        return self.extract_value(self.get_amp_raw())

    def set_amp(self, f: float) -> str:
        return self.retry_query(q=':MOD:AMP {:.2f}'.format(f), grp='AMP', isSet=True, value=f, isFloat=True)

    def get_amp_range_raw(self) -> str:
        return self.retry_query(q=':MOD:AMPR?', grp='AMPR')

    def get_amp_range_low(self) -> str:
        s = get_amp_range_raw()
        return re.search(r'\((.*?),(.*?)\)', s).group(1)

    def get_amp_range_high(self) -> str:
        s = get_amp_range_raw()
        return re.search(r'\((.*?),(.*?)\)', s).group(2)

    def get_drv_raw(self) -> str:
        return self.retry_query(q=':MOD:DRV?', grp='DRIVE')

    def get_drv(self) -> str:
        return self.extract_value(self.get_drv_raw())

    def set_drv(self, f: float) -> str:
        return self.retry_query(q=':MOD:DRV {:.2f}'.format(f), grp='DRIVE', isSet=True, value=f, isFloat=True)

    # Sets wavelength and returns current wavelength value
    def set_nm(self, nm: float) -> str:
        return self.extract_value(self.set_amp(nm * self.retardation))

    def get_nm(self, nm: float) -> str:
        return float(self.get_amp()) / self.retardation

    def get_cp_error_raw(self) -> str:
        return self.retry_query(q=':SYS:CPE?', grp='CPE')

    # relative current error (0-2.5)
    def get_current_error(self) -> str:
        s = get_cp_error_raw()
        return re.search(r'\((.*?),(.*?)\)', s).group(1)

    # relative phase error (0-1)
    def get_phase_error(self) -> str:
        s = get_cp_error_raw()
        return re.search(r'\((.*?),(.*?)\)', s).group(2)

    def get_voltage_info(self) -> str:
        return self.retry_query(q=':SYS:VC?', grp='VC')
    """

"""MFLI coding: As for the integration with the MFLI Lock-in Amplifier, you would need to feed the reference signal 
output from the PEM controller into the reference input of the MFLI. Then, in the MFLI's control software or 
programming interface, you would set up a demodulator to use this reference signal for phase-sensitive detection. 
This allows the MFLI to measure the amplitude and phase of the signal from the photomultiplier tube (PMT) at the 
modulation frequency of the PEM."""



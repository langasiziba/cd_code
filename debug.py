import tkinter as tk  # Import the Tkinter library for creating GUIs
from queue import Queue  # Import the Queue class from the queue module
from datetime import datetime  # Import the datetime class from the datetime module
import time
import pyvisa


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


"The class below is designed to log errors from the devices and display them"


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

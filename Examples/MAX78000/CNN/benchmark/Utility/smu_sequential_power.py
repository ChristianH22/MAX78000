import serial
from serial import SerialException
from threading import Thread
from threading import Event
from queue import Queue
import ast
import time
import os
import pandas as pd
import re
import datetime
from core.devices import AbstractSourceMeter, MockSourceMeter, SourceMeter, TracingSourceMeter, RequestError
from collections import defaultdict, deque
import numpy as np
from typing import NoReturn
from multiprocessing import Process
from multiprocessing import Event as ProcessEvent
from multiprocessing import Queue as ProcessQueue
from dataclasses import dataclass, field


# Set the sampling rate and the amount of samples per inference
samples: str = "10000"  # str
rate: str = "min" # seconds, str. min for minimum trigger interval (2e-5)

if rate == "min":
    rate_int = float(2e-5)
else:
    rate_int = float(rate)
samples_int = int(samples)


class PowerCollectionProcess(Process):
    """ 
    Process for power collection
    
    Purpose to interface with the Keysight B2901A SMU, collect voltage, current, and power data.
    Ultimately stores data to dictionary object, and placed into a queue.
     
    """
    
    def __init__(self, source_meter_name: str, data: defaultdict, data_queue: ProcessQueue, collection_event: ProcessEvent, ready_event: ProcessEvent, shutdown_event: ProcessEvent, first_sample: ProcessEvent, buffer_event: ProcessEvent):
        """ 
        Initializes process instance
        
        Holds sourcemeter information, data queue, and ProcessEvent Flags
        
        """
        super().__init__()
        self.sm_name = source_meter_name
        self.data_queue = data_queue
        self.collection_event = collection_event
        self.shutdown_event = shutdown_event
        self.ready_event = ready_event
        self.buffer_event = buffer_event
        self.first_sample = first_sample
        self.data = data

    def run(self) -> NoReturn:
        """ 
        Runs process
        
        Recieves flag to collect data on interval specified by the serial port (main thread)
        
        """
    
        #For trace buffer
        source_meter = TracingSourceMeter.get_instance(self.sm_name)
        
        # For one-shot power measure
        # source_meter = SourceMeter.get_instance(self.sm_name)

        # Operate entirely within context of the source_meter, important for performance
        with source_meter as sm:
            
            # Set voltage to 5 and current limit to 100: accounts for current spike on power-up
            sm.set_voltage(5.0)
            sm.set_current_limit(100.0)

            # For trace buffer
            sm.configure_trace("trac", "volt,curr")
            sm.configure_output()

            while not self.shutdown_event.is_set():

                # Logic to capture full impulse, with increased bandwidth for highly variant current impulse
                self.ready_event.wait()
                if self.shutdown_event.is_set():
                    break
            
                self.collection_event.set()
            
                # clear trace buffer
                sm.clear_trace("trac")

                # Sets trigger to idle, and sets trace to write mode
                sm.start_current()

                # self.data = {"Voltage(V)": [], "Current(A)": [], "Power(W)": []}
                self.data = {"Measurements": []}
                trigger = 0
              
                # Loop to collect power measurements, runs until collection_event flag is cleared or until trace buffer is full
                while self.collection_event.is_set():
                    if trigger == 0:

                        # Set the trigger for the trace once
                        sm.set_trigger(rate, samples, "trac")
                    trigger +=1
                    used_mem = sm.get_free_trace("trac")
                    comma_index = used_mem.find(",")

                    # available variable used to calculate remaining memory in trace
                    available = int(used_mem[1:comma_index])

                    # if (available < 4800000) and (flag == 0):
                    #     flag += 1
                    #     self.first_sample.set()
                    
                    # 4800000 is the full size of the trace buffer. Each sample is 48 bytes (100,000 samples total)
                    if (available <= ((4800000 - (samples_int*48))+1)):

                        # Logic to indicate the buffer is complete
                        self.buffer_event.set()

                        # Indicates collection event is over, communicates with main loop
                        self.collection_event.clear()


                        # self.first_sample.clear()
                        if self.shutdown_event.is_set():
                            break
                    
                        
                # Collect trace data when flag is closed. measurements contains an np.array of voltage and current data 
                # (voltage on even indicies, current on odd indicies)
                measurements = sm.retrieve_data("trac")

                # not important 
                self.first_sample.clear()

                # Clear buffer 
                sm.clear_trace("trac")

                # prints the length of your measurements. Should be twice the size of your samples
                print(len(measurements))
                
                # Prepare data for processing thread
                self.data["Measurements"].append(measurements.flatten().astype(float).tolist())
                
                        
                # Store data dictionary in queue
                self.data_queue.put(self.data)



def data_saving(results_path, data: defaultdict, csv_shutdown: Event):
    """ 
    Thread to save data sequentially 
    
    Ensures power measurements are collected and saved sequentially. In the event that an error occurs,
    there is no data loss
     
    """

    while not csv_shutdown.is_set():
        if len(data) != 0:

            # create directory in "YYYYMMDD" format
            run_date = datetime.datetime.now().strftime("%Y%m%d")
            directory = os.path.join(results_path, run_date)
            os.makedirs(directory, exist_ok= True)
            for name, measurements in data.items():
                
                # create .csv file in "YYYYMMDD_HHMMSS_<logits>.csv" format
                logits = str(name).replace("\r", "").replace("\n", "").replace(" ", "")
                load_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                csv_name = f"{load_time}_{logits}.csv"
                run_date_path = os.path.join(directory, csv_name)
                
                # current_data = measurements["Current(A)"][0]

                # save to pandas dataframe
                df = pd.DataFrame()

                # Odd indicies
                df["Current(A)"] = measurements["Measurements"][0][1::2]
                # Even indicies
                df["Voltage(V)"] = measurements["Measurements"][0][::2]
                
                power = (np.array(measurements["Measurements"][0][1::2])) * (np.array(measurements["Measurements"][0][::2]))
                df["Power(W)"] = power
                
                df.to_csv(run_date_path)
            data.clear()


                


def collect_binaries(ser: serial.Serial):
    """ 
    Return /bin/ file's buffer for processing

    This function returns all binary audio files under /bin/ located on the SD Card, by 
    using the Serial logic to cd into the /bin/ file on open, and then running the 'ls' command.
    Saves buffer output as a string.
    
    Function can later be modified to return the command array, which is currently done in the main thread.
    
    """

    loop_iteration = 0
    buffer = ""
    while loop_iteration < 3:  
        if ser.in_waiting > 0:
            value = ser.read(ser.in_waiting).decode("ascii")
            buffer += value
            print(value, end='')
        if "$ " in buffer:
            if loop_iteration == 0:
                buffer = ""

                # 'cd' into /bin/
                ser.write(("cd bin" + "\r\n").encode(encoding="ascii"))
                loop_iteration += 1
            elif loop_iteration == 1:
                buffer = ""

                # print files under /bin/
                ser.write(("ls" + "\r\n").encode(encoding="ascii"))
                loop_iteration += 1
            elif loop_iteration == 2:
                
                # return buffer as a string
                return buffer
    return buffer



if __name__ == "__main__":
    """ 
    Main Thread to inferface with serial
    
    The main thread's purpose is to run serial commands, and provide control flow to the data thread and power collection process.
    Current functionality loops through all binary audio files, runs inference on each, and collects power measurements within the 
    appropriate window. Power measurements begin on the serial notice for a command request (denoted by "$ "), and end 
    on the following command request. The logic assumes that if there is a newly recognized "$ " in buffer, the previous command (typically
    an inference) is complete, and it is safe to move to the next power collection cycle. This window also provides high bandwidth 
    to collect accurate power impulses, and allows for variance.
    
    """

    # Variables
    shutdown_event = ProcessEvent()
    collection_event = ProcessEvent()
    ready_event = ProcessEvent()
    buffer_event = ProcessEvent()
    first_sample = ProcessEvent()
    data_queue = ProcessQueue()
    inputQueue = Queue()
    outputQueue = Queue()
    csv_stop = Event()
    csv_ready = Event()
    csv_shutdown = Event()
    data = defaultdict(list)



    
    results_path = "results"
    
    # Create power collection instance, and begin process
    process1 = PowerCollectionProcess(
        source_meter_name="USB0::0x0957::0x8B18::MY51143212::INSTR",
        data = data,
        data_queue = data_queue,
        collection_event=collection_event,
        ready_event= ready_event,
        shutdown_event= shutdown_event,
        buffer_event = buffer_event,
        first_sample = first_sample
    )
    process1.start()
    time.sleep(7)

    # Begin data collection thread
    data_thread = Thread(target= data_saving, args = (results_path, data, csv_shutdown))
    data_thread.start()

    # Populate Serial interface with startup information
    print("Press SW4 Button on MAX78000")
    ser = serial.Serial(port = "COM3", baudrate = 115200)
    time.sleep(4)
    
    # Create command array that takes '/bin/' files on the SD Card and formats them as <ri> command prompts
    # Stored in command_array
    binaries_string: str
    binaries_string = collect_binaries(ser)
    lines = binaries_string.splitlines()
    command_array = []
    for unprocessed_files in lines:
        if unprocessed_files.find(".bin") != -1:
            command_array.append("ri " + unprocessed_files[5:])  
    command_array.append("end")

    # Create serial interface for thread/process control flow: iterates through all files in /bin/
    command_loop = 0
    buffer = "$ "
    temp_string = ""
    time.sleep(0.06)

    while command_loop < len(command_array):
        try:
            if ser.in_waiting > 0:
                value = ser.read(ser.in_waiting).decode("ascii")
                buffer += value
                temp_string += value
                print(value, end='')
        except SerialException as e:
            print("Serial Connection Failed: Retrying...")
            print(e)
            ser = serial.Serial(port = "COM3", baudrate = 115200)
            continue
           


        # if (command_loop != 0):
        #         buffer_event.wait()
                   
        # Searches for command request in buffer
        
        if "$ " in buffer:
            
            
            # Initializes collection_event flag t clear -> ends power collection on each following command request.
            
            # collection_event.clear()
            
            
            

            # Collect logits, printed between abc** flag and cba*** flag (reference inference.c)
            if (command_loop != 0):
                key = temp_string[(temp_string.find("**cah**") + len("**cah**")):(temp_string.find("**hac**"))]

                # Match logits with power measurement data
                data[key] = data_queue.get()
                # time.sleep(1)
            
            # Starts power collection
            
            if command_loop != (len(command_array)-1):
                ready_event.set()
                
                # allow some time to capture the full start of waveform
                time.sleep(0.012)

                # Tried adding a wait for first sample, did not work.
                # time.sleep((samples_int * rate_int)+0.005)
                # first_sample.wait()
                

            # Reset buffer and temp_string to find logits
            buffer = ""
            temp_string = ""

            # Initializes buffer_event to be cleared, prior to command enter
            buffer_event.clear()

            # Write command to serial interface, and run inference
            input = command_array[command_loop]
            ser.write((input + "\r\n").encode(encoding="ascii"))
            
            

            

            # Clear ready_event so when file is complete, process wait's for reset
            ready_event.clear()
            if command_loop != (len(command_array)-1):
                # wait for buffer to finish, full size is 4800000 bytes (48 bytes per sample)
                buffer_event.wait()
            
            # Sleep for a proper amount of time so samples have time to collect
            # time.sleep(((samples_int) * (rate_int))+0.05)
            
            

            command_loop += 1

    # End threads
    time.sleep(0.012)
    csv_shutdown.set()

    shutdown_event.set()
    ready_event.set()

    data_thread.join()
    process1.join()
    
    

        

                
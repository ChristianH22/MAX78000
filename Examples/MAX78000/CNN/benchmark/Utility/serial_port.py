#### first, create follow instructions under egfet-experiment-controls/Setup/PrepareEnvironment ###
## Activate egfet_devices pyenv with .\eget_devices\Scripts\activate
import serial
from threading import Thread, Event, Lock
from queue import *

import time
import os
import pandas as pd
import re
import datetime
from core.devices import AbstractSourceMeter, MockSourceMeter, SourceMeter, RequestError
from collections import defaultdict, deque
import numpy as np

ser = serial.Serial(port = "COM3", baudrate = 115200)

def sendCommand(kill):

    command = input()
    if (command == "kill"):
        kill += 1
    ser.write((command + "\r\n").encode(encoding="ascii"))
    return kill


if __name__ == "__main__":
    print("Press SW4 button on MAX78000")
    buffer = ""
    kill = 0
    while kill == 0:
        if ser.in_waiting > 0:
            value = ser.read(ser.in_waiting).decode("ascii")
            buffer += value
            print(value, end='')
            if "$ " in buffer:
                buffer = ""
                kill = sendCommand(kill)
                

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Feb 2 17:21 2021

@author: disaev

"""

import os.path as op
import threading
import uuid
import time

import numpy as np

import pylsl
from pylsl import StreamInfo, StreamOutlet

from neurobooth_os.mock.mock_device_streamer import MockLSLDevice, MockMbient, MockCamera
from neurobooth_os.iout.iphone_device import IPhone
import socket
from neurobooth_os.gui import _start_lsl_session,_stop_lsl_and_save,_record_lsl
import neurobooth_os.config as cfg
import liesl
from liesl.files.labrecorder.cli_wrapper import LabRecorderCLI


if __name__ == "__main__":

    from neurobooth_os.iout.marker import marker_stream

    
    dev_stream = MockLSLDevice(name="mock", nchans   =5)
    with dev_stream:
        time.sleep(0.2)# time.sleep(10)
    mbient = MockMbient()
    cam = MockCamera()
    marker = marker_stream(outlet_id='')

    #---- IPhone part
    MOCK=True
    iphone=IPhone('123456')
    
#,{'name':'IPhone','hostname':'IPhone_hostname'}
    recorderMac=LabRecorderCLI('/Users/dmitry/anaconda/anaconda3/envs/nb_dev/lib/python3.9/site-packages/liesl/files/labrecorder/lib/LabRecorderCLI')
    session = liesl.Session(prefix='', recorder=recorderMac,streamargs=[{'name':'Marker'}],mainfolder='/Users/dmitry/projects/neurobooth-lsl-files/')
    session.start_recording()
    if MOCK:
        HOST = '127.0.0.1'                 # Symbolic name meaning the local host
        PORT = 50010     # Arbitrary non-privileged port
        s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        s.connect((HOST,PORT))
        iphone.sock=s
        iphone.connected=True
        iphone._mock_handshake()
    else:
        iphone.handshake() # Sends "@STANDBY" -> waits for "@READY" 

    cam.start()
    dev_stream.start()
    mbient.start()

    iphone.start_recording() # Starts Listening thread. Sends "@START" -> expects "@STARTTIMESTAMP"
    time.sleep(30) # 30 sec sleep - in the meantime Listening thread catches "@INPROGRESSTIMESTAMP"
    iphone.stop_recording() #Sends "@STOP" -> expects "@STOPTIMESTAMP". Closes the Listening thread

    print(iphone._allmessages)
    #------

    marker.push_sample([f"Stream-mark"])

    cam.stop()
    dev_stream.stop()
    mbient.stop()

    session.stop_recording()
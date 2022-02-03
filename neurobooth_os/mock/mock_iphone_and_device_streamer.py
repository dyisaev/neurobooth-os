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
import neurobooth_os.mock.mock_device_streamer as mocker


if __name__ == "__main__":

    from neurobooth_os.iout.marker import marker_stream

    stream_names = {'MockLSLDevice': 'mock_lsl', 'MockMbient': 'mock_mbient',
                'MockCamera': 'mock_camera', 'marker_stream': 'Marker','IPhoneRecorder':'iphone'}
    streamargs = [{'name': stream_name} for stream_name in stream_names.values()]

    dev_stream = mocker.MockLSLDevice(name=stream_names['MockLSLDevice'], nchans=5)
    mbient = mocker.MockMbient(name=stream_names['MockMbient'])
    cam = mocker.MockCamera(name=stream_names['MockCamera'])
    marker = marker_stream(name=stream_names['marker_stream'])

    #---- IPhone part
    MOCK=True
    iphone=IPhone(name=stream_names['IPhoneRecorder'],sess_id='123456')
    streamargs = [{'name': stream_name} for stream_name in stream_names.values()]

#,{'name':'IPhone','hostname':'IPhone_hostname'}
    recorderMac=LabRecorderCLI('/opt/homebrew/Cellar/labrecorder/1.14.2/LabRecorder/LabRecorderCLI.app/Contents/MacOS/LabRecorderCLI')
    session = liesl.Session(prefix='', recorder=recorderMac,streamargs=streamargs,mainfolder='/Users/dmitry/projects/neurobooth-lsl-files/')
    session.start_recording()
    
    cam.start()
    dev_stream.start()
    mbient.start()

    try:
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


        iphone.start_recording() # Starts Listening thread. Sends "@START" -> expects "@STARTTIMESTAMP"
        time.sleep(30) # 30 sec sleep - in the meantime Listening thread catches "@INPROGRESSTIMESTAMP"
        iphone.stop_recording() #Sends "@STOP" -> expects "@STOPTIMESTAMP". Closes the Listening thread
    except:
        pass

    print(iphone._allmessages)
    #------

    marker.push_sample([f"Stream-mark"])

    cam.stop()
    dev_stream.stop()
    mbient.stop()

    session.stop_recording()
from email import message_from_string
from logging import raiseExceptions
import socket
import json
import struct
import threading
import time
from datetime import datetime
import select
import uuid

from neurobooth_os.iout.marker import marker_stream

from neurobooth_os.iout.usbmux import MuxConnection, PlistProtocol, USBMux, BinaryProtocol

IPHONE_PORT=2345 #IPhone should have socket on this port open, if we're connecting to it.

class IPhoneError(Exception):
    pass

class IPhoneListeningThread(threading.Thread):
    def __init__(self,*args):
        self._iphone=args[0]
        self._start_ts_received=False
        self._stop_ts_received=False
        self._running=True
        self._recording=True
        threading.Thread.__init__(self)

    def run(self):
        #step 1: receive @STARTTIMESTAMP
        msg,version,type,resp_tag=self._iphone._getpacket()
        self._iphone._validate_message(msg)
        if msg['MessageType']!='@STARTTIMESTAMP':
            raise IPhoneError('Cannot Start Video recording. No START->STARTTIMESTAMP connection with Iphone.')
        # do we need to validate other fields here?

        self._iphone._process_message(msg,resp_tag)

        self._recording=True
        self._start_ts_received=True
        #step 2: listen to @INPROGRESSTIMESTAMP and break on @STOPTIMESTAMP
        while self._running:
            try:
                msg,version,type,resp_tag=self._iphone._getpacket()
                self._iphone._validate_message(msg)
                if not msg['MessageType'] in ['@INPROGRESSTIMESTAMP','@STOPTIMESTAMP']:
                    raise IPhoneError(f'Message of type: {msg["MessageType"]} appeared in listening thread.')
                #process message - send timestamps to LSL, etc
                
                self._iphone._process_message(msg,resp_tag)

                print(f'Listener received: {msg}')
                if msg['MessageType']=='@STOPTIMESTAMP':
                    self._stop_ts_received=True
                    self._recording=False
            except:
                pass
            
    def stop(self):
        self._running=False


class IPhone:
    TYPE_MESSAGE=101
    VERSION=1
    MESSAGE_TYPES=set(['@START','@STOP','@STANDBY','@READY','@DUMP','@STARTTIMESTAMP','@INPROGRESSTIMESTAMP','@STOPTIMESTAMP'])
    MESSAGE_KEYS=set(['MessageType','SessionID','TimeStamp','Message'])
    def __init__(self,name,sess_id=''):
        self.connected=False
        self.recording=False
        self.tag=0
        self.iphone_sessionID=sess_id
        self._allmessages=[]
        self.name=name
        self.create_outlet()

    def _validate_message(self,message):
        if len(message)!=len(self.MESSAGE_KEYS):
            raise IPhoneError(f'Message has incorrect length: {message}')
        for key in message:
            if key not in self.MESSAGE_KEYS:
                raise IPhoneError(f'Message has incorrect key: {key} not allowed. {message}')
        return True    
    def _message(self,msg_type,ts='',msg=''):
        if not msg_type in self.MESSAGE_TYPES:
            raise IPhoneError(f'Message type "{msg_type}" not in allowed message type list')
        return {"MessageType": msg_type,
            "SessionID": self.iphone_sessionID,
            "TimeStamp": ts,
            "Message": msg
        }
    def _json_wrap(self,message):
        json_msg=json.dumps(message)
        json_msg='####'+json_msg # add 4 bytes
        return json_msg
    def _json_unwrap(self,payload):
        message=json.loads(payload[4:])
        return message
    def _sendpacket(self,msg_type):
        if not self.connected:
            raise IPhoneError('IPhone is not connected')
        msg=self._message(msg_type)
        #Append message to list of messages
        self._process_message(msg,self.tag)

        payload=self._json_wrap(msg).encode('utf-8')
        payload_size=len(payload)
        packet=struct.pack("!IIII",self.VERSION,self.TYPE_MESSAGE,self.tag,payload_size)+payload
        self.sock.send(packet)
    def _getpacket(self,timeout_in_seconds=20):
        ready,_,_ = select.select([self.sock], [], [], timeout_in_seconds)
        #print(ready)
        if ready:
            first_frame=self.sock.recv(16)
            version,type,tag,payload_size = struct.unpack("!IIII", first_frame)
            payload = self.sock.recv(payload_size)
            msg=self._json_unwrap(payload)
            return msg,version,type,tag
        else:
            raise IPhoneError(f'Timeout for packet receive exceeded ({timeout_in_seconds} sec)')

    def handshake(self):
        self.usbmux=USBMux()
        if not self.usbmux.devices:
            self.usbmux.process(0.1)
        for dev in self.usbmux.devices:
            print(dev)
        if len(self.usbmux.devices)==1:
            self.device=self.usbmux.devices[0]
            self.sock=self.usbmux.connect(self.device,IPHONE_PORT)
            self.sock.setblocking(0)
            self.connected=True
            tag=self.tag
            self._sendpacket('@STANDBY')
            msg,version,type,resp_tag=self._getpacket()
            self._validate_message(msg)
            self._process_message(msg)
            if msg['MessageType']!='@READY':
                self.sock.close() #close the socket on our side to avoid hanging sockets
                raise IPhoneError('Cannot establish STANDBY->READY connection with Iphone')
            # if tag!=resp_tag (check with Steven)
            #process message - send timestamps to LSL, etc.
            self._process_message(msg,resp_tag)
            self.tag+=1
            return 0
        else:
            return -1

    def _mock_handshake(self):
        tag=self.tag
        self._sendpacket('@STANDBY')
        msg,version,type,resp_tag=self._getpacket()
        self._validate_message(msg)
        if msg['MessageType']!='@READY':
            self.sock.close() #close the socket on our side to avoid hanging sockets
            raise IPhoneError('Cannot establish STANDBY->READY connection with Iphone')
        # if tag!=resp_tag (check with Steven)
        #process message - send timestamps to LSL, etc.
        self._process_message(msg,resp_tag)
        return 0    
    def start_recording(self):
        if not self.connected:
            return -1
        tag=self.tag
        self._listen_thread=IPhoneListeningThread(self)
        self._listen_thread.start()
        self._sendpacket('@START')
        return 0
    def stop_recording(self):
        self._listen_thread.stop()
        self._sendpacket('@STOP')
        time.sleep(4)
        self._listen_thread.join(timeout=3)
        if self._listen_thread.is_alive():
            raise IPhoneError('Cannot stop the recording thread')
        return 0 
    def _process_message(self,msg,tag):
        self._allmessages.append({'message':msg,'ctr_timestamp':str(datetime.now()),'tag':tag})
        self.outlet.push_sample([f"message_:_{msg}||ctr_timestamp_:_{time.time()}||tag_:_{tag}"])
    def create_outlet(self):
        self.outlet_id = str(uuid.uuid4())
        self.outlet=marker_stream(self.name,self.outlet_id)



if __name__ == "__main__":
    MOCK=True

    iphone=IPhone('123456')
    if MOCK:
        HOST = '127.0.0.1'                 # Symbolic name meaning the local host
        PORT = 50009     # Arbitrary non-privileged port
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

    print(iphone._allmessages)
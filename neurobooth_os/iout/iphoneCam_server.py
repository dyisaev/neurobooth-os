
from socket import *
from datetime import datetime
import threading
from time import sleep
import json
from iphone_device import IPhone

c = threading.Condition()
quit=False


# https://stackoverflow.com/a/62277798
def is_socket_closed(sock: socket) -> bool:
    try:
        # this will try to read bytes without blocking and also without removing them from buffer (peek only)
        data = sock.recv(16, MSG_DONTWAIT | MSG_PEEK)
        if len(data) == 0:
            return True
    except BlockingIOError:
        return False  # socket is open and reading from it would block
    except ConnectionResetError:
        return True  # socket was closed for some other reason
    except Exception as e:
        print(e)
        #logger.exception("unexpected exception when checking if a socket is closed")
        return False
    return False

def keyboard_thread(conn,file):
    global quit
    while not quit:
        kb_input=input('YOUR COMMAND:')
        if kb_input=='QUIT':
            c.acquire()
            quit=True
            c.notify_all()
            c.release()
            break
        if not is_socket_closed(conn):
            iphone._sendpacket(kb_input)
            #conn.send(('IPHONE_'+str(datetime.now())+'_'+kb_input+'\n').encode())
        file.write('IPHONE_'+kb_input+'\t'+str(datetime.now())+'\n')
    return
def socket_thread(conn,file):
    global quit
    while not quit:
        try:
            data = conn.recv(1024,MSG_DONTWAIT)
        except BlockingIOError as e:
            continue
        if not data: continue
        print (data)
        if data==b'START':
            file.write(data.decode("utf-8")+'\t'+str(datetime.now())+'\n')
        elif data==b'STOP':
            file.write(data.decode("utf-8")+'\t'+str(datetime.now())+'\n')  
            c.acquire()
            quit=True
            c.notify_all()
            c.release()
        else:
            file.write(data.decode("utf-8")+'\t'+str(datetime.now())+'\n')

HOST = '127.0.0.1'                 # Symbolic name meaning the local host
PORT = 50010       # Arbitrary non-privileged port
SERVER_LOG='SERVER_LOG.TXT'
s = socket(AF_INET,SOCK_STREAM)
s.bind((HOST, PORT))
s.listen(1)
conn, addr = s.accept()

iphone=IPhone('19111984')
iphone.sock=conn
iphone.connected=True


#empty SERVER_LOG
file=open(SERVER_LOG,'w')
file.close()
file=open(SERVER_LOG,'a')
file.write('LOG STARTED\t'+str(datetime.now())+'\n')


kb_thread = threading.Thread(target=keyboard_thread, args=(conn,file))
sock_thread= threading.Thread(target=socket_thread, args=(conn,file))

kb_thread.start()
sock_thread.start()


while not quit:
    sleep(0.2)

if kb_thread:
    print(kb_thread)
    kb_thread.join()
if sock_thread:
    print(sock_thread)
    sock_thread.join()

conn.close()
s.close()
if file:
    file.close()

from pylsl import StreamInfo, StreamOutlet



class IPhoneRecorder():

    def __init__(self):
        return
    def start_recording(self):
        return
    def stop_recording(self):
        return
    def send_audio_marker(self):
        return
    def listen(self,task): 
        # should we have here a pointer to task and run this asynchronously,
        # and in case we receive something, we invoke the Task_IPhone function to send marker?
        return
    
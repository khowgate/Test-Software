from multiprocessing import Lock, Process, Queue, current_process
import time
import queue # imported for using queue.Empty exception
from modules import DC_PSU

global reportQue

controlQue = Queue()
reportQue = Queue()

DC = DC_PSU()


def run(reportQue,controlQue):
    
    while True:
        if not controlQue.empty():
            command = controlQue.get()
            print('receving Command '+str(command))
        else:
            print('Doing Work')
            reportQue.put('Work_Done')
            time.sleep(2)    
    return True

if __name__=='__main__':
    
    Inital_voltage_limit = 1
    Inital_current_limit = 0.1
    Overcurrent_protection = 1
    
    psu_operation = Process(target=run, args=(reportQue,controlQue,)) 
    psu_operation.start()
    
    i = 0
    while True:
        i +=1
        print(controlQue.empty(),i)
        if not reportQue.empty():
            print(reportQue.get())
        
      
        
        if i == 10:
            i = 0
            controlQue.put('Change_Output')
        time.sleep(0.5)
        
        if KeyboardInterrupt:
            


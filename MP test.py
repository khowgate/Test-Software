from multiprocessing import Lock, Process, Queue, current_process
import time
import queue # imported for using queue.Empty exception
from modules import DC_PSU

global reportQue

controlQue = Queue()
reportQue = Queue()

DC = DC_PSU()

def run(instrument ,Inital_voltage_limit, Inital_current_limit, Overcurrent_protection, controlQue, reportQue):
     err = 0
     DC.SetOutputState(instrument, state='Off')
     
     print(instrument, Inital_voltage_limit,Inital_current_limit)        
     DC.Inital_voltage_limit = Inital_voltage_limit
     DC.Inital_current_limit = Inital_current_limit
     DC.Vset(Inital_voltage_limit, instrument)
     DC.Iset(Inital_current_limit, instrument)
     DC.SetOverCurrentProtection(instrument, Overcurrent_protection)
     DC.SetOutputState(instrument, state='On')
     
     
         
     while True:
         if controlQue.empty():
             V = DC.Vget(instrument)
             I = DC.Iget(instrument)
             #self.logger.db_write('PSU'+str(instrument)+' V','N/A',V)
             #self.logger.db_write('PSU'+str(instrument)+' V','N/A',I)
         

             if DC.GetOutputState(instrument) == 'Off':
                 # print('OCP Trip')
                 err += 1
                 reportQue.put('PSU'+str(instrument)+' FAULT NO.'+str(err))
                 time.sleep(1)
                 DC.SetOutputState(instrument, state='On')
                     
             if err >2:
                 DC.SetOutputState(instrument, state='Off')
                 return reportQue.put('PSU'+str(instrument)+' TERMINAL FAULT')
             print(V,I, err)
             time.sleep(0.5)
     
         else:
             if 'new_V' in controlQue.get():
                 DC.Vset(controlQue.get()['new_V'], instrument)
             elif 'new_I' in controlQue.get():
                 DC.Vset(controlQue.get()['new_I'], instrument)
             else:
                 print(controlQue.get())
     return True


if __name__=='__main__':
    
    Inital_voltage_limit = 1
    Inital_current_limit = 0.1
    Overcurrent_protection = 1
    units = DC.list_available()
    instrument = units[1]
    

    psu_operation = Process(target=run, args=(instrument, Inital_voltage_limit,Inital_current_limit,Overcurrent_protection, controlQue, reportQue)) 
    psu_operation.start()
    
    while True:
        print(reportQue.empty())
        if not reportQue.empty():
            print(reportQue.get())
        time.sleep(5)
        


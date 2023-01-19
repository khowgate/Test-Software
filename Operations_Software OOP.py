import PySimpleGUI as sg
import time
from datetime import datetime
from multiprocessing.pool import ThreadPool
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from omnipy import control, collection, analysis, utils
from datetime import datetime
from multiprocessing import Process, Queue
from pyfirmata import Arduino

controlQue = Queue()
reportQue = Queue()
stateQue = Queue()
DC = control.DC_PSU()

plt.ion()

err= {'err':0,'txt':''}

dbKeys = open('secrets.txt', 'r')
Lines = dbKeys.readlines()

dbSync = utils.db_tools(Lines[1].strip(), Lines[0].strip(), 'Log_data')


def psuLoggingStart(port,voltage,current):

    if float(values['-PSUV-']) > 12:
        raise Exception('Supply Limit Requested exceeds soft limit (12V)')
    psu_operation = pool.apply_async(collection.PSU_run, (dbSync,DC,port,voltage,current,1,controlQue,reportQue))


def runSetup(fig_agg1):
    print('before run def')
    def run(Vstart, Vstop, Vstep, step, timeout):
        camDelay = float(values['-CAMDELAY-'])*1e-3
        pulseTime = 5e-3
        start = time.time()
        ignition = 0
        while True:
            
            time.sleep(0.1)
            
            currentVolts = 5*(voltInPin.read()/2**10)*1e5
            print((time.time()-start) > timeout,currentVolts)

            if currentVolts > Vstart or (time.time()-start) > timeout:
                    print('sequance start')
                    
                    camPin.write(1)
                    time.sleep(pulseTime)
                    camPin.write(0)
                    print('camPulse')

                    time.sleep(camDelay)

                    ignPin.write(1)
                    time.sleep(pulseTime)
                    ignPin.write(0)
                    print('ignPulse')

                    ignition += 1
                    try:
                        b, bit = analysis.Raw_Data_Collection(disp_sensor,6,freqLaser, ax, cx) # Displasment Sesor Procseeing
                        fig_agg1.draw()
                    except:
                        bit = 0
                    
                    fig_tool.LogDisp('-BIT-', bit)
                    fig_tool.LogDisp('-LASTV-', currentVolts)
                    fig_tool.LogDisp('-SHOTN-', ignition)
                    fig_tool.LogDisp('-SENSORH-', 0)
                    dbSync.db_write('Bit_test', 'test', bit)

                    start = time.time()

                
                    stop = False
                    if ignition >= step:
                        print('stop event')
                        errDump.write('\nStop event, user or ignition max exit\nIgnition No.'+str(ignition)+'Ignition max'+str(step)+'\n')
                        controlQue.put('stop')
                        stop = True
                    if not reportQue.empty():
                        print('stop event')
                        statment = reportQue.get()

                        psuErr += 1
                        errDump.write(statment+'\n')
                        if psuErr > 3:
                            fig_tool.LogDisp('-LOG-',statment)
                            stop = True
                        fig_tool.LogDisp('-LOG-',statment)
                    if not controlQue.empty():
                        print('stop event')
                        errDump.write('Stop event, control que break\n')
                        if 'stop' in controlQue.get():
                            stop = True
                    if stop:
                        stateQue.put('stop')
                        break

            
            if Vstop != Vstart:
                Vstart += Vstep
                run(Vstart,Vstop,Vstep,step)

        return   

    print('after run def')    
    err = ''
    event = ''
    

    if 'psu_port' in globals():
        try:
            psuLoggingStart(psu_port,int(values['-PSUV-']),int(values['-PSUA-'])/1000)
        except Exception as Arguments:
            err = Arguments
    
    if 'psu2_port' in globals():
        try:
            psuLoggingStart(psu2_port,int(values['-PSU2V-']),int(values['-PSU2A-'])/1000)
        except Exception as Arguments:
            err = Arguments

    freqLaser = 2000

    errDump = open('runEventDump.txt', 'w')
    now = datetime.now()
    date_time = now.strftime("%m/%d/%Y, %H:%M:%S")
    errDump.write('\nTest Date/time'+date_time)
    timeout = float(values['-TIMEOUT-'])

    if values['-COM5-'] == 'V-Fix':
        Vstart = int(values['-VOLTS-'])
        step = int(values['-SHOOT-'])
        print(Vstart,step)
        
        async_result4 = pool.apply_async(run, (Vstart,Vstart,100,step,timeout))
    elif values['-COM5-'] == 'V-Sweep':
        Vstart = int(values['-SWP_STRT-'])
        Vstop = int(values['SWP_STOP-'])
        Vstep = int(values['SWP_STEP-'])
        step = int(values['-SWP_SHOT-'])
        async_result4 = pool.apply_async(run, (Vstart,Vstop,Vstart,step,timeout))
    else:
        raise Exception('Mode value not recognised')




instruments = DC.list_available()
COM_PORTS = []   
ports = {}
for instrument in instruments:
    COM = 'COM'+''.join(x for x in instrument if x.isdigit())
    COM_PORTS.append(COM)
    ports[COM] = instrument
 

voltages = [1500,2000]
potential_shots = [100,200,300,400,500,600,700,800,900,1000]
potential_freq = [0.1,0.2,0.3]
#Last_Image = r'C:\Users\KristianHowgate\OneDrive - omnidea.net\Documents\Work\PFT BBM\BBM Block Diagram.png'
Last_Ibit = 0.01
Last_V = 1700
shots = 137
heath = 100
step = 6
freqLaser=2000



image_elem = sg.Image(data=utils.get_img_data('2.4.0002.JPG', first=True))

modes = [1500]
col1 = sg.Col([
        [sg.Frame('',[[sg.Text('Toggle ADC24'),sg.Button(button_text ='Toggle',size=(15,1),key='-VLOG_EN-')],
        [sg.Text('Arduino COM Port'), sg.Combo(COM_PORTS,size=(15,22), key='-COM-',enable_events=True)],
        [sg.Button(button_text ='Connect',size=(15,1),key='-ARDUINO_CON-'),  utils.LEDIndicator('-ARDUINO_STATUS-')],
        [sg.Text('ILD1420 COM Port'), sg.Combo(COM_PORTS,size=(15,22), key='-COM2-',enable_events=True)],
        [sg.Button(button_text ='Connect',size=(15,1),key='-SENS_CON-'),  utils.LEDIndicator('-SENS_STATUS-'), sg.Button(button_text ='Test',size=(15,1),key='-DIS_TEST-')],
        [sg.Text('PSU COM Port'), sg.Combo(COM_PORTS,size=(15,22), key='-COM3-',enable_events=True)],
        [sg.Button(button_text ='Connect',size=(15,1),key='-PSU_CON-'),  utils.LEDIndicator('-PSU_STATUS-')],
        [sg.Text('PSU2 COM Port'), sg.Combo(COM_PORTS,size=(15,22), key='-COM4-',enable_events=True)],
        [sg.Button(button_text ='Connect',size=(15,1),key='-PSU2_CON-'),  utils.LEDIndicator('-PSU2_STATUS-')]])],
        [sg.Text('Operation Mode'), sg.Combo(['V-Fix','V-Sweep'],size=(15,22), key='-COM5-')],
        [sg.Text('Camera Pre-Trigger (ms)'), sg.Input(default_text='200',size=(15,22), key='-CAMDELAY-')],
         
        [sg.TabGroup([[sg.Tab('V-Fix',[[sg.Text('Voltage Selection'), sg.Combo(voltages,default_value= 1500,size=(15,22), key='-VOLTS-',enable_events=True)],
                                    [sg.Text('Target Shot No.'), sg.Spin(potential_shots,size=(15,22), key='-SHOOT-',enable_events=True)],
                                    [sg.Text('Fixed Voltage Output (V)'), sg.Input(default_text='12',size=(15,22), key='-PSUV-',enable_events=True)],
                                    [sg.Text('Fixed Current Limit (mA)'), sg.Input(default_text='50',size=(15,22), key='-PSUA-',enable_events=True)],
                                    [sg.Text('Power Supply Overide Control'),sg.Button(button_text ='Test',size=(15,1),key='-PSUSET-')]])],
                    [sg.Tab('V-Sweep',[[sg.Text('Sweep Start Voltage'), sg.Combo(voltages,size=(15,22), key='-SWP_STRT-',enable_events=True)],
                                    [sg.Text('Sweep Stop Voltage'), sg.Combo(voltages,size=(15,22), key='-SWP_STOP-',enable_events=True)],
                                    [sg.Text('Voltage between Steps'), sg.Combo([50,100,200],size=(15,22), key='-SWP_STEP-',enable_events=True)],
                                    [sg.Text('No. Shots/step'), sg.Input(default_text='50',size=(15,22), key='-SWP_SHOT-',enable_events=True)]])],
                    [sg.Tab('Ignitor',[[sg.Text('Fixed Voltage Output (V)'), sg.Input(default_text='12',size=(15,22), key='-PSU2V-',enable_events=True)],
                                    [sg.Text('Fixed Current Limit (mA)'), sg.Input(default_text='50',size=(15,22), key='-PSU2A-',enable_events=True)],
                                    [sg.Text('Power Supply Overide Control'),sg.Button(button_text ='Test',size=(15,1),key='-PSU2SET-')],
                                    [sg.Text('Ignitor Timeout'), sg.Input(default_text='10',size=(15,22), key='-TIMEOUT-')],
                                    [sg.Text('Ignition Freq (not supported)'), sg.Spin(potential_freq,size=(15,22), key='-FREQ-',enable_events=True)]])]])],
         
         
        [sg.Button(button_text ='Run',size=(15,1),key='-RUN-')]])

col2 = [[sg.Text('Last Image')],
        [image_elem]
    ]


col3 = sg.Frame('',[[sg.Frame('',[[sg.Text('IBIT')],[sg.StatusBar('',k='-BIT-',s=(5,2))]]),
         sg.Frame('',[[sg.Text('Last Voltage')],[sg.StatusBar('',k='-LASTV-',s=(5,2))]]),
         sg.Frame('',[[sg.Text('Shot No.')],[sg.StatusBar('',k='-SHOTN-',s=(5,2))]]),
         sg.Frame('',[[sg.Text('Sensor Heath')],[sg.StatusBar('',k='-SENSORH-',s=(5,2))]]) ],
        [sg.Canvas(size=(400,200),key='-GRAPH1-')],[sg.Canvas(size=(400,200),key='-GRAPH3-',visible=False)],
        [sg.Canvas(size=(400,200),key='-GRAPH2-')]])
        

col4 = sg.Frame('',[[sg.Text('Log')],
        [sg.StatusBar('', k='-LOG-', s=(200,1))]])


# layout_frame_1 = [[sg.Frame('',port)], [sg.Frame('',col1)]]

# layout_frame_2 = sg.Frame('',col2), sg.Frame('',col3)


layout = [[col1,col3],[col4]]

window = sg.Window('Test', layout,finalize=True)

fig_tool = utils.figure_tools(window)


fig_tool.SetLED('-ARDUINO_STATUS-', 'red')
fig_tool.SetLED('-SENS_STATUS-', 'red')
fig_tool.SetLED('-PSU_STATUS-', 'red')
fig_tool.SetLED('-PSU2_STATUS-', 'red')

#Graph 1
canvas_elem1 = window['-GRAPH1-']
canvas1 = canvas_elem1.TKCanvas

fig1 = Figure(figsize=(10,4))
fig_agg1 = fig_tool.draw_figure(canvas1, fig1)
ax = fig1.add_subplot(111)
ax.set_xlabel("X axis")
ax.set_ylabel("Y axis")
ax.grid()


#Graph 2
canvas_elem2 = window['-GRAPH2-']
canvas2 = canvas_elem2.TKCanvas

fig2 = Figure(figsize=(10,4))
bx = fig2.add_subplot(111)
bx.set_xlabel("X axis")
bx.set_ylabel("Y axis")
bx.grid()
fig_agg2 = fig_tool.draw_figure(canvas2, fig2)



run_vlog = True
run_dis = True
run_log = True
delay = 0
i=0
pool = ThreadPool(processes=6)
disp_sensor = 0

if __name__=='__main__':

    while True:
        
        
        i += 1
        event, values = window.read()
        
        
        
        if event=='-ARDUINO_CON-':
            fig_tool.SetLED('-ARDUINO_STATUS-', 'orange')
            try:
                board = Arduino(values['-COM-'])
                camPin, ignPin, voltInPin = control.arduinoBuiltIn(board)
                fig_tool.SetLED('-ARDUINO_STATUS-', 'green')
            except Exception as Arguments:
                err = Arguments.args
                fig_tool.SetLED('-ARDUINO_STATUS-', 'red')  
            fig_tool.LogDisp('-LOG-',err)   
        
        
        if event=='-SENS_CON-':  
            fig_tool.SetLED('-SENS_STATUS-', 'orange')
            try:
                disp_sensor = control.ILD(values['-COM2-'])
                data, t = disp_sensor.poll()
                fig_tool.SetLED('-SENS_STATUS-', 'green')
            except Exception as Arguments:
                disp_sensor = 0
                fig_tool.SetLED('-SENS_STATUS-', 'red')
                err = Arguments.args     
            fig_tool.LogDisp('-LOG-', err)  
        
        
        if event=='-PSU_CON-':
            fig_tool.SetLED('-PSU_STATUS-', 'orange')
            try:
                psu_port = ports[values['-COM3-']]
                DC.SetOutputState(psu_port, state='Off')
                print(psu_port,DC.identify(psu_port))
                fig_tool.SetLED('-PSU_STATUS-', 'green')
            except Exception as Arguments:
                fig_tool.SetLED('-PSU_STATUS-', 'red')
                err = Arguments
            fig_tool.LogDisp('-LOG-', err)

        if event=='-PSU_CON2-':
            fig_tool.SetLED('-PSU2_STATUS-','orange')
            try:
                psu2_port = ports[values['-COM4-']]
                DC.SetOutputState(psu2_port, state='Off')
                print(psu2_port,DC.identify(psu2_port))
                fig_tool.SetLED('-PSU2_STATUS-', 'green')
            except Exception as Arguments:
                fig_tool.SetLED('-PSU2_STATUS-', 'red')
                err = Arguments
            fig_tool.LogDisp('-LOG-', err)
        
        if event=='-DIS_TEST-':
            if disp_sensor != 0 :
                if run_dis:
                    try:
                        print('Testing')
                        module1 = collection.PollDis
                        event=''
                        async_result2 = pool.apply_async(module1,(disp_sensor, ax, fig_agg1, controlQue))
                        
                        run_dis = False
                        err = ''
                    except:
                        err = 'ILD Not Open'
                else:
                    print('Stopping')
                    controlQue.put('stop')
                    time.sleep(0.5)
                    run_dis = True
                fig_tool.LogDisp('-LOG-',err)
        
        if event=='-VLOG_EN-':
            if run_vlog:
                print('run')          
                try:
                    unit = control.ADC24() 
                    module2 = collection.VoltLog
                    async_result1 = pool.apply_async(module2, (dbSync,unit, bx, fig_agg2, controlQue))
                    err = ''
                except:
                    err = 'ADC24 Connection Failed'
                event=''
                run_vlog = False
            else:
                print('Stopping')
                controlQue.put('stop')
                run_vlog = True
                
            fig_tool.LogDisp('-LOG-',err)
                
        if event=='-RUN-' or not stateQue.empty():
            if not stateQue.empty():
                stateQue.get()
                run_log = False

            fig_tool.delete_figure_agg(fig_agg1)
            if run_log:
                run_log = False
                fig3 = Figure(figsize=(10,4))
                ax = fig3.add_subplot(121)
                cx = fig3.add_subplot(122)
                
                ax.set_xlabel('Time (s)')
                ax.set_ylabel('Amplitude ($\mu$m)')
                ax.grid(b=True, which='major', axis='y',alpha=0.5)
                ax.grid(b=True, which='major', axis='x',alpha=0.5)
                
                cx.set_xlabel('frequency(Hz)')
                cx.set_ylabel('Amplitude')
                cx.grid(b=True, which='major', axis='y',alpha=0.5)
                cx.grid(b=True, which='major', axis='x',alpha=0.5)
                print('drawing figure')

                fig_agg1 = fig_tool.draw_figure(canvas1, fig3)
                runSetup(fig_agg1)
            else:
                run_log = True
                controlQue.put(['stop']*4)
                fig_agg1 = fig_tool.draw_figure(canvas1, fig1)
                
            fig_tool.LogDisp('-LOG-',err)  
        
        if event=='-PSUSET-':
            print(values['-PSUV-'],(int(values['-PSUA-'])/1000))
            try:
                DC.Vset(float(values['-PSUV-']), psu_port)
                DC.Iset(float(int(values['-PSUA-'])/1000), psu_port)
            except:
                fig_tool.LogDisp('-LOG-', 'Failled to set PSU Values')
        
            
        if event == "Exit" or event == sg.WIN_CLOSED:
            print('close')
            controlQue.put(['stop']*4)
            try:
                disp_sensor.close()
            except:
                pass
            try:
                unit.close()
            except:
                pass
            try:
                board.exit()
            except:
                pass
            window.Close()
            break        

         
    
        
     

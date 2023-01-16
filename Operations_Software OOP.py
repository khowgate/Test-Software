import PySimpleGUI as sg
import time
from datetime import datetime
from multiprocessing.pool import ThreadPool
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from PIL import Image, ImageTk
import io
from omnipy import control, collection, analysis, utils
from datetime import datetime
from multiprocessing import Process, Queue
from pyfirmata import Arduino

controlQue = Queue()
reportQue = Queue()
DC = control.DC_PSU()

plt.ion()

err= {'err':0,'txt':''}

dbKeys = open('secrets.txt', 'r')
Lines = dbKeys.readlines()



dbSync = utils.db_tools(Lines[1].strip(), Lines[0].strip(), 'Log_data')

def LEDIndicator(key=None, radius=30):
    return sg.Graph(canvas_size=(radius, radius),
             graph_bottom_left=(-radius, -radius),
             graph_top_right=(radius, radius),
             pad=(0, 0), key=key)

def get_img_data(f, maxsize=(800, 600), first=False):
    """Generate image data using PIL
    """
    img = Image.open(f)
    img.thumbnail(maxsize)
    if first:                     # tkinter is inactive the first time
        bio = io.BytesIO()
        img.save(bio, format="PNG")
        del img
        return bio.getvalue()
    return ImageTk.PhotoImage(img)


def run(volts,camPreTrig,camPin,ignPin,voltInPin):
    
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

    fig_agg3 = fig_tool.draw_figure(canvas1, fig3)

    ign_t_id =[]
    ignition = 0
    step= 6
    freqLaser = 2000

    pulseTime = 5e-3

    start = time.time()
    psuErr = 0

    errDump = open('runEventDump.txt', 'w')
    now = datetime.now()
    date_time = now.strftime("%m/%d/%Y, %H:%M:%S")
    errDump.write('\nTest Date/time'+date_time)
    
    while True:
        
        time.sleep(0.1)
        print((time.time()-start))
        currentVolts = 5*(voltInPin.read()/2**10)*1e5

        if currentVolts > volts or (time.time()-start) > 10:
                print('sequance start')
                
                camPin.write(1)
                time.sleep(pulseTime)
                camPin.write(0)
                print('camPulse')

                time.sleep(camPreTrig)

                ignPin.write(1)
                time.sleep(pulseTime)
                ignPin.write(0)
                print('ignPulse')

                ignition += 1
                try:
                    b, bit = analysis.Raw_Data_Collection(disp_sensor,step,freqLaser, ax, cx) # Displasment Sesor Procseeing
                    fig_agg3.draw()
                except:
                    bit = 0
                
                fig_tool.LogDisp('-BIT-', bit)
                fig_tool.LogDisp('-LASTV-', currentVolts)
                fig_tool.LogDisp('-SHOTN-', ignition)
                fig_tool.LogDisp('-SENSORH-', 0)
                dbSync.db_write('Bit_test', 'test', bit)

                start = time.time()

            
        if event=='-RUN-' or ignition >= max_ignitions:
            print('stop event')
            errDump.write('\nStop event, user or ignition max exit\nIgnition No.'+str(ignition)+'Ignition max'+str(max_ignitions)+'\n')
            fig_tool.delete_figure_agg(fig_agg3)
            controlQue.put('stop')
            break
        if not reportQue.empty():
            print('stop event')
            statment = reportQue.get()

            psuErr += 1
            errDump.write(statment+'\n')
            if psuErr > 3:
                fig_tool.LogDisp('-LOG-',statment)
                break
            fig_tool.LogDisp('-LOG-',statment)
        if not controlQue.empty():
            print('stop event')
            errDump.write('Stop event, control que break\n')
            if 'stop' in controlQue.get():
                break


    return   


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



image_elem = sg.Image(data=get_img_data('2.4.0002.JPG', first=True))

modes = [1500]
col1 = sg.Col([
        [sg.Frame('',[[sg.Text('Toggle ADC24'),sg.Button(button_text ='Toggle',size=(15,1),key='-VLOG_EN-')],
        [sg.Text('Arduino COM Port'), sg.Combo(COM_PORTS,size=(15,22), key='-COM-',enable_events=True)],
        [sg.Button(button_text ='Connect',size=(15,1),key='-ARDUINO_CON-'),  LEDIndicator('-ARDUINO_STATUS-')],
        [sg.Text('ILD1420 COM Port'), sg.Combo(COM_PORTS,size=(15,22), key='-COM2-',enable_events=True)],
        [sg.Button(button_text ='Connect',size=(15,1),key='-SENS_CON-'),  LEDIndicator('-SENS_STATUS-'), sg.Button(button_text ='Test',size=(15,1),key='-DIS_TEST-')],
        [sg.Text('PSU COM Port'), sg.Combo(COM_PORTS,size=(15,22), key='-COM3-',enable_events=True)],
        [sg.Button(button_text ='Connect',size=(15,1),key='-PSU_CON-'),  LEDIndicator('-PSU_STATUS-')],
        [sg.Text('PSU2 COM Port'), sg.Combo(COM_PORTS,size=(15,22), key='-COM4-',enable_events=True)],
        [sg.Button(button_text ='Connect',size=(15,1),key='-PSU2_CON-'),  LEDIndicator('-PSU2_STATUS-')]])],
        [sg.Text('Operation Mode'), sg.Combo(['V-Fix','V-Sweep'],size=(15,22), key='-COM5-')],
        [sg.Text('Camera Pre-Trigger (ms)'), sg.Input(default_text='50',size=(15,22), key='-CAMDELAY-',enable_events=True)],
         
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
                
        if event=='-RUN-':
            if run_log:
                err = ''
                event = ''
                run_log = False
                fig_tool.delete_figure_agg(fig_agg1)    
                Inital_voltage_limit = int(values['-PSUV-'])
                Inital_current_limit = int(values['-PSUA-'])/1000
                Overcurrent_protection = 1
                print(values['-SHOOT-']  ,values['-FREQ-'],values['-CAMDELAY-'])
                max_ignitions = float(values['-SHOOT-'])   
                ignition_frequency = float(values['-FREQ-'])
                camera_delay = float(values['-CAMDELAY-'])*1e-3

                module3 = collection.PSU_run

                try:
                    psu_operation = pool.apply_async(module3, (dbSync,DC,instrument ,Inital_voltage_limit, Inital_current_limit, Overcurrent_protection, controlQue, reportQue))
                except:
                    err += 'PSU1 not connected'
                try:
                    psu2_operation = pool.apply_async(module3, (dbSync,DC,instrument ,Inital_voltage_limit, Inital_current_limit, Overcurrent_protection, controlQue, reportQue))
                except:
                    err += 'PSU2 not connected'
                async_result4 = pool.apply_async(run, (values['-VOLTS-'],camera_delay, camPin, ignPin, voltInPin))
            else:
                run_log = True
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
            controlQue.put('stop')
            controlQue.put('stop')
            controlQue.put('stop')
            controlQue.put('stop')
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

         
    
        
     

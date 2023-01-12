import PySimpleGUI as sg

import time
from datetime import datetime
from multiprocessing.pool import ThreadPool
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageTk
import io
import pandas as pd
from scipy.signal import find_peaks
from scipy.fft import fft, fftfreq
from scipy.optimize import curve_fit
import omnipy
from datetime import datetime
from multiprocessing import Process, Queue
from pyfirmata import Arduino, util
from pyfirmata.util import Iterator

controlQue = Queue()
reportQue = Queue()
DC = omnipy.DC_PSU()

plt.ion()

err= {'err':0,'txt':''}

dbKeys = open('secrets.txt', 'r')
Lines = dbKeys.readlines()



dbSync = omnipy.db_tools(Lines[1].strip(), Lines[0].strip(), 'Log_data')

def LEDIndicator(key=None, radius=30):
    return sg.Graph(canvas_size=(radius, radius),
             graph_bottom_left=(-radius, -radius),
             graph_top_right=(radius, radius),
             pad=(0, 0), key=key)

def PSU_run(instrument ,Inital_voltage_limit, Inital_current_limit, Overcurrent_protection, controlQue, reportQue):
     err = 0
     DC.SetOutputState(instrument, state='Off')
     
     # print(instrument, Inital_voltage_limit,Inital_current_limit)        
     DC.Inital_voltage_limit = Inital_voltage_limit
     DC.Inital_current_limit = Inital_current_limit
     DC.Vset(Inital_voltage_limit, instrument)
     DC.Iset(Inital_current_limit, instrument)
     DC.SetOverCurrentProtection(instrument, Overcurrent_protection)
     DC.SetOutputState(instrument, state='On')
     
     start_time2 = time.time()
     
     print('psu control loop confirm')
     while True:
         if controlQue.empty():
             if time.time() - start_time2 > 2:
                 V = DC.Vget(instrument)
                 I = DC.Iget(instrument)
                 dbSync.db_write(instrument,'V',V)
                 dbSync.db_write(instrument,'I',I)
                 start_time2 = time.time()
                 print(V,I, err)

             if DC.GetOutputState(instrument) == 'Off':
                 # print('OCP Trip')
                 err += 1
                 reportQue.put(instrument+' FAULT NO.'+str(err))
                 time.sleep(1)
                    
             if err >2:
                 DC.SetOutputState(instrument, state='Off')
                 return reportQue.put(instrument+' TERMINAL FAULT')
             
     
         else:
            command = controlQue.get()
            if 'new_V' in command:
                 DC.Vset(command['new_V'], instrument)
            elif 'new_I' in command:
                 DC.Vset(command['new_I'], instrument)
            elif 'stop' in command:
                DC.SetOutputState(instrument, state='Off')
                print('PSU log stopping')
                break
            else:
                 print(controlQue.get())
        
     return True

def VoltLog(ax, fig_agg2):

    data = [[],[]]
    t = []
     
    channels= [1,3]
    ranges = ['HRDL_78_MV','HRDL_78_MV']
    conversion_times = ['HRDL_100MS','HRDL_100MS']
    
    unit.setup_channels(channels,ranges, conversion_times)    #Setup Channel

    while True:
 
        i = 0
        raw = unit.getV()
        x = 0
        for val in raw:
            data[x].append(val)
            x += 1
        now = datetime.now()
        t_ = now.strftime("%H:%M:%S:%f")
        t.append(t_)
        
        ax.cla()
        if len(t) > 199:
            t = t[1:201]
            x = 0
            while x < len(channels):
                data[x] = data[x][1:201]
                x += 1
        for dat in data:
            ax.plot(t,dat,  color='purple')
        ax.grid()
        
        pos = 0
        if i > 19:
            for dat in data:  
                try:
                    dbSync.db_write('Temp', 'Sens '+str(pos), dat[-1])
                except:
                    print('server connection Issue')
                pos +=1
            i=0
            
        #print(data[0])
        #print(t)
        if len(t) <25:
            ax.set(xticks=[t[0],t[-1]])
            #print(t[0],t[-1])
        elif len(t) <175:
            middleIndex = int(len(t)/2)
            ax.set(xticks=[t[0],t[middleIndex],t[-1]])
            #print(t[0],t[middleIndex],t[-1])
        else :
        #len(t) <198:
            middleIndex = int(len(t)/2)
            bottomIndex = int(len(t[0:middleIndex])/2)
            ax.set(xticks=[t[0],t[bottomIndex],t[middleIndex],t[bottomIndex+middleIndex],t[-1]])
                              
        fig_agg2.draw()
        
        if event=='-VLOG_EN-':
            print('Vlog Stop')
            unit.close()
            break
        if not controlQue.empty():
            if 'stop' in controlQue.get():
                
                break


def PollDis(ax, fig_agg1):
    print('Poll Start')
    t = []
    data = []
    while True:
        data_raw, t_raw = disp_sensor.poll()
        data.append(data_raw), t.append(t_raw)
        if len(t) > 100:
            t = t[1:102]
            data =data[1:102]
        ax.cla()                    # clear the subplot
        ax.grid()                   # draw the grid
        ax.plot(t,data,  color='purple')
        
        if len(t) <20:
            ax.set(xticks=[t[0],t[-1]])
            #print(t[0],t[-1])
        elif len(t) <80:
            middleIndex = int(len(t)/2)
            ax.set(xticks=[t[0],t[middleIndex],t[-1]])
        else :
            middleIndex = int(len(t)/2)
            bottomIndex = int(len(t[0:middleIndex])/2)
            ax.set(xticks=[t[0],t[bottomIndex],t[middleIndex],t[bottomIndex+middleIndex],t[-1]])
        fig_agg1.draw()
        time.sleep(0.05)
        if event=='-DIS_TEST-':
            print('Poll Stop')
            break


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

def Ibit(mp,L,dx): 
    g = 9.8066
    dx = dx*1e-6
    mp = mp*1e-3
    L = L*1e-2
    Y = np.sqrt(1-(np.power((dx/L),2)))
    return mp*np.sqrt(2*g*L*(1-Y))

class fitClass:
    def __init__(self):
        pass    
    def funcSin(self,t,A,phi): # remove lamb if dumping factor is not being considered
        w = 2*np.pi*self.f
        #Dump =A*np.exp(-lamb*t)
        #return Dump*np.sin(w*t+phi)
        return A*np.sin(w*t+phi)

def fitting_before (peak_number_after_discharge,df,frqY):
    #BEFORE DISCHARGE
    #TIMESTAP DEFINITION
    timeStart1=-3
    timeStop1=-0.2

    timeStart2=0.2
    timeStop2=3
    
#CURVE FIT
    df_aux1=df.drop(df[df['Time [s]'] > timeStop1].index)
    df_aux1.drop(df_aux1[df_aux1['Time [s]'] < timeStart1].index, inplace=True)

    y_1=df_aux1['Distance'].to_numpy()
    x_1=df_aux1['Time [s]'].to_numpy()
    
    
    x_fit_1=np.linspace(timeStart1,timeStop1,num=1000)
     
    df_aux2=df.drop(df[df['Time [s]'] > timeStop2].index)
    df_aux2.drop(df_aux2[df_aux2['Time [s]'] < timeStart2].index, inplace=True)
    
    y_2=df_aux2['Distance'].to_numpy()
    x_2=df_aux2['Time [s]'].to_numpy()

    x_fit_2=np.linspace(timeStart2,timeStop2,num=1000)
    

    inst = fitClass()
    inst.f = frqY
    coeffs1, coeffs_cov1 = curve_fit(inst.funcSin, x_1, 1000*y_1)
    print('f=%0.2f Hz, A=%0.2f um, phase=%0.2f rad'%(frqY,coeffs1[0],coeffs1[1]))

    coeffs2, coeffs_cov2 = curve_fit(inst.funcSin, x_2, 1000*y_2)
    print('f=%0.2f Hz, A=%0.2f um, phase=%0.2f rad'%(frqY,coeffs2[0],coeffs2[1]))
    #,bounds=(0,[600.,360.,0.5]))
    x_fit_1=np.linspace(timeStart1,timeStop1,num=10000)
    x_fit_2=np.linspace(timeStart2,timeStop2,num=10000)
    
    
    A=coeffs1[0]
    alpha=coeffs1[1]
    M=coeffs2[0]
    phi=coeffs2[1]
    
    c1=A*np.cos(alpha)
    s1=A*np.sin(alpha)
    c2=M*np.cos(phi)
    s2=M*np.sin(phi)

    B=0
    B=np.sqrt((c1-c2)**2+(s1-s2)**2)
    
    return x_fit_1, x_fit_2, coeffs1, coeffs2, B, inst, timeStart1, timeStop2

def Raw_Data_Collection(step,freqLaser, ax, cx):

    print('process start')
    time.sleep(step/2)
    
    raw_data = pd.DataFrame()
    raw_data['1'] = disp_sensor.block_data()
    #print(raw_data)

    dt=1/freqLaser

    df = pd.DataFrame()

    df["Distance"] = raw_data[(len(raw_data['1'])-step*freqLaser):len(raw_data['1']-1)]
    tfinal=dt*step*freqLaser
    df["Time [s]"] = np.arange(0,tfinal,dt)
    offset=df.mean()
    df= (df-offset)
    
    
    #plot results
    print('plot reached')
    ax.cla()                    # clear the subplot
    ax.grid()
    ax.plot(df["Time [s]"],df["Distance"],'r-',lw='1',label='raw data')
    print(df["Time [s]"],df["Distance"])
    #plt.xlim(4,5.5)
    ax.legend(loc='best')

    amplitude=(df['Distance'].max()-df['Distance'].min())/2 #millimeter
    print('Max Amplitude = %0.2f mm'%amplitude)

    y=df['Distance'].to_numpy()
    x=df['Time [s]'].to_numpy()

    # Number of sample points
    N = len(x)
    # sample spacing
    T = dt
    yf = fft(y)
    xf = fftfreq(N, T)[:N//2]

    peakY = np.max(2.0/N * np.abs(yf[0:N//2])) # Find max peak
    locY = np.argmax(2.0/N * np.abs(yf[0:N//2])) # Find its location
    frqY = xf[locY] # Get the actual frequency value
    T=1/frqY #Get period
    
    
    
    cx.cla()                    # clear the subplot
    cx.grid()
    cx.semilogx(xf, 2.0/N * np.abs(yf[0:N//2]),label='Peak=%0.2f Hz'%frqY)
    cx.legend(loc='best')
    peaks, _ = find_peaks(df['Distance'], height=0, distance=1000)
    np.diff(peaks)
    #plt.plot(df['Time [s]'],df['Distance'], "-")
    #plt.plot(df['Time [s]'][peaks],df['Distance'][peaks], "x")

    shots = [None]*peaks.size
    matrix = {}
    h     = 0
    x     = 0
    count = 0 

    (x_fit_1, x_fit_2, coeffs1, coeffs2, B, inst,timeStart1, timeStop2)= fitting_before(x+1,df,frqY)
    
    mp= 5e-6
    L = 0.1
    
    bit = Ibit(mp,L,B)
    
    #Update display
    #Log values
    
    
    return B, bit


def closest(lst, K):
      
     lst = np.asarray(lst)
     idx = (np.abs(lst - K)).argmin()
     return idx


def arduino_setup(board):
    it = util.Iterator(board)
    it.start()
    cam = board.get_pin('d:12:o')
    ign = board.get_pin('d:13:o')
    volt = board.get_pin('a:0:i')
    # volt.enable_reporting()

    return cam, ign, volt

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
                    b, bit = Raw_Data_Collection(step, freqLaser, ax, cx) # Displasment Sesor Procseeing
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


port  = [[sg.Text('Toggle ADC24'),sg.Button(button_text ='Toggle',size=(15,1),key='-VLOG_EN-')],
        [sg.Text('Arduino COM Port'), sg.Combo(COM_PORTS,size=(15,22), key='-COM-',enable_events=True)],
        [sg.Button(button_text ='Connect',size=(15,1),key='-ARDUINO_CON-'),  LEDIndicator('-ARDUINO_STATUS-')],
        [sg.Text('ILD1420 COM Port'), sg.Combo(COM_PORTS,size=(15,22), key='-COM2-',enable_events=True)],
        [sg.Button(button_text ='Connect',size=(15,1),key='-SENS_CON-'),  LEDIndicator('-SENS_STATUS-'), sg.Button(button_text ='Test',size=(15,1),key='-DIS_TEST-')],
        [sg.Text('PSU COM Port'), sg.Combo(COM_PORTS,size=(15,22), key='-COM3-',enable_events=True)],
        [sg.Button(button_text ='Connect',size=(15,1),key='-PSU_CON-'),  LEDIndicator('-PSU_STATUS-')],
        [sg.Text('PSU2 COM Port'), sg.Combo(COM_PORTS,size=(15,22), key='-COM4-',enable_events=True)],
        [sg.Button(button_text ='Connect',size=(15,1),key='-PSU2_CON-'),  LEDIndicator('-PSU2_STATUS-')]]


col1 = [[sg.Text('Voltage Selection'), sg.Combo(voltages,default_value= 1500,size=(15,22), key='-VOLTS-',enable_events=True)],
         [sg.Text('Target Shot No.'), sg.Spin(potential_shots,size=(15,22), key='-SHOOT-',enable_events=True)],
         [sg.Text('Ignition Frequency'), sg.Spin(potential_freq,size=(15,22), key='-FREQ-',enable_events=True)],
         [sg.Text('Camera Pre-Trigger (ms)'), sg.Input(default_text='50',size=(15,22), key='-CAMDELAY-',enable_events=True)],
         [sg.Text('Power Supply Overide Control'),sg.Button(button_text ='Test',size=(15,1),key='-PSUSET-')],
         [sg.Text('Fixed Voltage Output (V)'), sg.Input(default_text='12',size=(15,22), key='-PSUV-',enable_events=True)],
         [sg.Text('Fixed Current Limit (mA)'), sg.Input(default_text='50',size=(15,22), key='-PSUA-',enable_events=True)],
         [sg.Text('Data Logging Selection')],
         [sg.Text('Thermal',size=(10,1)),sg.Radio('OFF',1, size=(10,2), enable_events=True, key='-THERM-'),sg.Radio('ON',1, size=(10,2), enable_events=True, key='-THERM-')],
         [sg.Text('Power', size=(10,1)),sg.Radio('OFF',2, size=(10,2), enable_events=True, key='-PWR-'),sg.Radio('ON',2, size=(10,2), enable_events=True, key='-PWR-')],
         [sg.Button(button_text ='Run',size=(15,1),key='-RUN-')],
         ]

col2 = [[sg.Text('Last Image')],
        [image_elem]
    ]


col3 = [[sg.Frame('',[[sg.Text('IBIT')],[sg.StatusBar('',k='-BIT-',s=(5,2))]]),
         sg.Frame('',[[sg.Text('Last Voltage')],[sg.StatusBar('',k='-LASTV-',s=(5,2))]]),
         sg.Frame('',[[sg.Text('Shot No.')],[sg.StatusBar('',k='-SHOTN-',s=(5,2))]]),
         sg.Frame('',[[sg.Text('Sensor Heath')],[sg.StatusBar('',k='-SENSORH-',s=(5,2))]]) ],
        [sg.Canvas(size=(400,200),key='-GRAPH1-')],[sg.Canvas(size=(400,200),key='-GRAPH3-',visible=False)],
        [sg.Canvas(size=(400,200),key='-GRAPH2-')]]
        

col4 = [[sg.Text('Log')],
        [sg.StatusBar('', k='-LOG-', s=(200,1))]]

# layout_frame_1 = [[sg.Frame('',port)], [sg.Frame('',col1)]]

# layout_frame_2 = sg.Frame('',col2), sg.Frame('',col3)




layout = [
        [sg.Frame('',port+col1),
        sg.Frame('',col2),
        sg.Frame('',col3)],
        [sg.Frame('',col4)]
    ]

window = sg.Window('Test', layout,finalize=True)

fig_tool = omnipy.figure_tools(window)


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
                camPin, ignPin, voltInPin = arduino_setup(board)
                fig_tool.SetLED('-ARDUINO_STATUS-', 'green')
            except Exception as Arguments:
                err = Arguments.args
                fig_tool.SetLED('-ARDUINO_STATUS-', 'red')  
            fig_tool.LogDisp('-LOG-',err)   
        
        
        if event=='-SENS_CON-':  
            fig_tool.SetLED('-SENS_STATUS-', 'orange')
            try:
                disp_sensor = omnipy.ILD(values['-COM2-'])
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
                        async_result2 = pool.apply_async(PollDis,(ax, fig_agg1))
                        event=''
                        run_dis = False
                        err = ''
                    except:
                        err = 'ADC Not Open'
                else:
                    print('Stopping')
                    time.sleep(0.5)
                    run_dis = True
                fig_tool.LogDisp('-LOG-',err)
        
        if event=='-VLOG_EN-':
            if run_vlog:
                print('run')          
                try:
                    unit = omnipy.ADC24()   
                    async_result1 = pool.apply_async(VoltLog, (bx, fig_agg2))
                    err = ''
                except:
                    err = 'ADC24 Connection Failed'
                event=''
                run_vlog = False
            else:
                print('Stop')
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
                try:
                    psu_operation = pool.apply_async(PSU_run, (psu_port, Inital_voltage_limit,Inital_current_limit,Overcurrent_protection, controlQue, reportQue))
                except:
                    err += 'PSU1 not connected'
                try:
                    psu2_operation = pool.apply_async(PSU_run, (psu2_port, 12,Inital_current_limit,Overcurrent_protection, controlQue, reportQue))
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

         
    
        
     

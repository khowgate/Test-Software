import PySimpleGUI as sg
import serial
import time
from instruments.micro_epsilon import MEDAQLib
from datetime import datetime
from multiprocessing.pool import ThreadPool
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import ctypes
from picosdk.picohrdl import picohrdl as hrdl
from picosdk.functions import assert_pico2000_ok
import numpy as np
from PIL import Image, ImageTk
import io
import pandas as pd
from scipy.signal import find_peaks
from scipy.fft import fft, fftfreq
from scipy.optimize import curve_fit
import influxdb_client, os, time
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from Tenma import DC_PSU

plt.ion()

err= {'err':0,'txt':''}

#influxdb setup

token = 'L2L-aCeEGP7R1g5D2nVTh3j4AEkOC_YXVlGuE-rsEScuLb3oRBNMsuLRZZvPRH6VZsaE99iJWjMb5DZ-tl5h2g=='
url = "http://localhost:8086"

client = influxdb_client.InfluxDBClient(url=url, token=token, org=org)

write_api = client.write_api(write_options=SYNCHRONOUS)

def db_write(point, field, data):
    # print(data)
    try:
        point = (
          Point(point)
          .field(field, float(data))
        )
    except:
        point = (
          Point(point)
          .field(field, float(data[0]))
        )
    print('point created')
    write_api.write(bucket="Log_data", org="Omnidea Ltd.", record=point)
    print('write Complte')
    

def draw_figure(canvas, figure, loc=(0, 0)):
    plt.close()
    figure_canvas_agg = FigureCanvasTkAgg(figure, canvas)
    figure_canvas_agg.draw()
    figure_canvas_agg.get_tk_widget().pack(side='top', fill='both', expand=1)
    return figure_canvas_agg

def delete_figure_agg(figure_agg):
    figure_agg.get_tk_widget().forget()
    plt.close('all')

def LEDIndicator(key=None, radius=30):
    return sg.Graph(canvas_size=(radius, radius),
             graph_bottom_left=(-radius, -radius),
             graph_top_right=(radius, radius),
             pad=(0, 0), key=key)

def SetLED(window, key, color):
    graph = window[key]
    graph.erase()
    graph.draw_circle((0, 0), 12, fill_color=color, line_color=color)
    #print('Colour Change')
    
class Updater:
    
    def __init__(self, window):
        self.window=window
        
    def LogDisp(self, key, err):
        disp = self.window[key]
        print(err)
        now = datetime.now()
        current_time = now.strftime("%H:%M:%S")
        try:
            disp.update(value=('['+current_time+']  '+str(err['txt'])))
        except:
            disp.update(value=('['+current_time+']  '+repr(err)))

        
def VoltCon():
    chandle = ctypes.c_int16()
    status = {}
    # Open unit
    status["openUnit"] = hrdl.HRDLOpenUnit()
    assert_pico2000_ok(status["openUnit"])
    chandle=status["openUnit"]

    # Set mains noise rejection
    # Reject 50 Hz mains noise
    status["mainsRejection"] = hrdl.HRDLSetMains(chandle, 0)
    assert_pico2000_ok(status["mainsRejection"])
    return chandle, status

def VoltLog(chandle, status, ax, fig_agg2):
    print('Vlog Started')
    i = 0
    t = []
    data = []
    max_counts = []
    IDs = [1,3,5,7,9,11,13,15]
    range = hrdl.HRDL_VOLTAGERANGE["HRDL_78_MV"]
    conversionTime = hrdl.HRDL_CONVERSIONTIME["HRDL_100MS"]
    overflow = ctypes.c_int16(0)
    value = ctypes.c_int32()
    print('setup commplete')
    for ID in IDs:
        data.append([])
        pos = int((ID-1)/2)
        Vmax = 2500/(2**range)
        # print(Vmax)
        min_count = ctypes.c_int32()
        max_count = ctypes.c_int32()
        status['ADCCounts'] = hrdl.HRDLGetMinMaxAdcCounts(chandle, ctypes.byref(min_count), ctypes.byref(max_count), ID)
        max_counts.append(max_count.value)
    
    # print('max counts = ', max_counts)
    while True:
        i += 1
        now = datetime.now()
        t_ = now.strftime("%H:%M:%S:%f")
        t.append(t_)
        if len(t) > 199:
            t = t[1:201]
        for ID in IDs:
            pos = int((ID-1)/2)
            status["getSingleValue"] = hrdl.HRDLGetSingleValue(chandle, ID, range, conversionTime, 0, ctypes.byref(overflow), ctypes.byref(value))
            data[pos].append((value.value/max_counts[pos])*Vmax)
            if len(data[pos]) > 199:
                data[pos] = data[pos][1:201]
    
        assert_pico2000_ok(status["getSingleValue"])    
        ax.cla()                    # clear the subplot
        ax.grid()                  # draw the grid
        #print(t[0],t[-1])
        #ax.set(xticks=np.linspace(t[0],t[-1], 5))
       
        for dat in data: 
            ax.plot(t,dat,  color='purple') 
        pos = 0
        if i > 19:
            for dat in data:  
                try:
                    db_write('Temp', 'Sens '+str(pos), dat[-1])
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
            break
        #time.sleep(0.09)
        
        #if event=='-IGNITION-':
            #new asynic task
                #avarge data
                #update display
        
    # return data    
    


def ArduinoConnect(p):
    try:
        arduino = serial.Serial(port=p, baudrate=115200, timeout=.1)
        arduino.reset_input_buffer()
        err= {'err':0,'txt':''}
    except Exception as Arguments:
        err= {'err':-1,'txt':Arguments.args}
        arduino =[]
    return arduino, err

def PollDis(s1, sensor, ax, fig_agg1):
    t = [] 
    data = []
    print('Poll Start')
    while True:
        now = datetime.now()
        t_ = now.strftime("%H:%M:%S:%f")
        t.append(t_)
        print(t)
        if len(t) > 100:
            t = t[1:102]
        unit = s1.poll(sensor,1)
        if unit[0] > 50 or unit[0] < 0:
            unit = [0]
            #print('err')
        data.append(unit[0]) 
        #print(unit[0])
        if len(data) > 100:
            data = data[1:102]
        print(t,unit)
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
    print('failure')

def DispSensConnect(p):
    s1 = MEDAQLib()
    print(p)

    sensor = s1.create_sensor("SENSOR_ILD1420")
    
    s1.set_parameter_string(sensor, "IP_Interface", "RS232")
    s1.set_parameter_int(sensor, "IP_EnableLogging", 1)
    s1.set_parameter_string(sensor, "IP_Port", p)
    baud = s1.get_error_text(sensor)
    

    try: 
        s1.open_sensor(sensor)
        err= {'err':0,'txt':str(baud)}
    except Exception as Arguments:
        s1.close_sensor(sensor)
        err= {'err':-1,'txt':Arguments.args}
    return s1, sensor, err

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

def Process(sensor,step,freqLaser, ax, cx):

    print('process start')
    time.sleep(step/2)

    N = s1.data_available(sensor)

    raw_data = pd.DataFrame()

    raw_data['1'] = s1.data_transfer(sensor, N)

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
    plt.plot(df['Time [s]'],df['Distance'], "-")
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

def run_error

def run(arduino, sensor, canvas1):
    fig1 = Figure(figsize=(10,4))
    ax = fig1.add_subplot(121)
    cx = fig1.add_subplot(122)
    
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Amplitude ($\mu$m)')
    ax.grid(b=True, which='major', axis='y',alpha=0.5)
    ax.grid(b=True, which='major', axis='x',alpha=0.5)
    
    cx.set_xlabel('frequency(Hz)')
    cx.set_ylabel('Amplitude')
    cx.grid(b=True, which='major', axis='y',alpha=0.5)
    cx.grid(b=True, which='major', axis='x',alpha=0.5)
    print('drawing figure')
    
    global fig_agg3
    fig_agg3 = draw_figure(canvas1, fig1)

    start = 0
    x = ['fire','one','two']
    commands = len(x)

    while (commands > 0):
       #print('Out Bytes: ',arduino.out_waiting,' In Bytes: ',arduino.in_waiting,)
           out_bytes = arduino.write(bytes(x[commands-1], 'utf-8'))
           print('Bytes Sent: ',out_bytes)
           commands -= 1

           time.sleep(1)
    ign_t_id =[]
    ignition = 0
    step= 6
    freqLaser = 2000
    print('run start')
   
    while True:
        in_bytes = arduino.readline()
        #print(in_bytes)

        if in_bytes:
            in_bytes = in_bytes.decode().strip('\r\n')
            print('Bytes Received ', in_bytes.strip('\r\n'))

            if 'ignition' in in_bytes:
                volt = in_bytes.split(' ')[0]
                shots = in_bytes.split(' ')[2]
                volt = int(volt)
                shots = int(shots) 
                volts = volt * (50000/1024) - (50000/1024)
                print('Charge = ',volts)
                try:
                    b, bit = Process(sensor, step, freqLaser, ax, cx)
                    fig_agg3.draw()
                except:
                    bit = 0
                    
                db_write('Bit_test', 'test', bit)
        if event=='-RUN-':
            out_bytes = arduino.write(bytes('stop', 'utf-8'))
            print('Bytes Sent: ',out_bytes)
            break
            

    return   


COM_PORTS = ["COM3","COM4","COM5","COM8"]
voltages = [1500,2000]
potential_shots = [100,200,300,400,500,600,700,800,900,1000]
#Last_Image = r'C:\Users\KristianHowgate\OneDrive - omnidea.net\Documents\Work\PFT BBM\BBM Block Diagram.png'
Last_Ibit = 0.01
Last_V = 1700
shots = 137
heath = 100
step = 6
freqLaser=2000



image_elem = sg.Image(data=get_img_data('2.4.0002.JPG', first=True))



col1 = [[sg.Text('Toggle ADC24'),sg.Button(button_text ='Toggle',size=(15,1),key='-VLOG_EN-')],
        [sg.Text('Arduino COM Port'), sg.Combo(COM_PORTS,size=(15,22), key='-COM-',enable_events=True)],
        [sg.Button(button_text ='Connect',size=(15,1),key='-ARDUINO_CON-'),  LEDIndicator('-ARDUINO_STATUS-')],
        [sg.Text('ILD1420 COM Port'), sg.Combo(COM_PORTS,size=(15,22), key='-COM2-',enable_events=True)],
        [sg.Button(button_text ='Connect',size=(15,1),key='-SENS_CON-'),  LEDIndicator('-SENS_STATUS-'), sg.Button(button_text ='Test',size=(15,1),key='-DIS_TEST-')],
         [sg.Text('Voltage Selection'), sg.Combo(voltages,size=(15,22), key='-VOLTS-',enable_events=True)],
         [sg.Text('Target Shot No.'), sg.Spin(potential_shots,size=(15,22), key='-SHOOT-',enable_events=True)],
         [sg.Text('Data Logging Selection')],
         [sg.Text('Thermal',size=(10,1)),sg.Radio('OFF',1, size=(10,2), enable_events=True, key='-THERM-'),sg.Radio('ON',1, size=(10,2), enable_events=True, key='-THERM-')],
         [sg.Text('Power', size=(10,1)),sg.Radio('OFF',2, size=(10,2), enable_events=True, key='-PWR-'),sg.Radio('ON',2, size=(10,2), enable_events=True, key='-PWR-')],
         [sg.Button(button_text ='Run',size=(15,1),key='-RUN-')],
         ]

col2 = [[sg.Text('Last Image')],
        [image_elem]
    ]


col3 = [[sg.Text('Last IBit\n'+str(Last_Ibit), relief='groove',s=(20,5),auto_size_text=True),
         sg.Text('Last Voltage\n'+str(Last_V), relief='groove',s=(20,5),auto_size_text=True),
         sg.Text('Shot No.\n'+str(shots), relief='groove',s=(20,5),auto_size_text=True),
         sg.Text('Sensor Heath\n'+str(heath)+'%', relief='groove',s=(20,5),auto_size_text=True)],
        [sg.Canvas(size=(400,200),key='-GRAPH1-')],[sg.Canvas(size=(400,200),key='-GRAPH3-',visible=False)],
        [sg.Canvas(size=(400,200),key='-GRAPH2-')]]
        

col4 = [[sg.Text('Log')],
        [sg.StatusBar('', k='-LOG-', s=(200,1))]]

layout = [
        [sg.Frame('',col1),
        sg.Frame('',col2),
        sg.Frame('',col3)],
        [sg.Frame('',col4)]
    ]

window = sg.Window('Test', layout,finalize=True)




SetLED(window, '-ARDUINO_STATUS-', 'red')
SetLED(window, '-SENS_STATUS-', 'red')

#Graph 1
canvas_elem1 = window['-GRAPH1-']
canvas1 = canvas_elem1.TKCanvas

fig1 = Figure(figsize=(10,4))
fig_agg1 = draw_figure(canvas1, fig1)
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
fig_agg2 = draw_figure(canvas2, fig2)



run_vlog = True
run_dis = True
run_log = True
delay = 0
i=0
pool = ThreadPool(processes=6)

up = Updater(window)

while True:
    
    
    i += 1
    event, values = window.read()
     
    try:
          print(event, values[event])
    except:
          print(event)
    if event=='-ARDUINO_CON-':
         SetLED(window, '-ARDUINO_STATUS-', 'amber')
         arduino, err= ArduinoConnect(values['-COM-'])
         if err['err'] < 0:
             SetLED(window, '-ARDUINO_STATUS-', 'red')
         else:
             SetLED(window, '-ARDUINO_STATUS-', 'green')
         up.LogDisp('-LOG-',err)   
    if event=='-SENS_CON-':  
        SetLED(window, '-SENS_STATUS-', 'amber')
        s1, sensor, err= DispSensConnect(values['-COM2-'])
            
        if err['err'] < 0:
            SetLED(window, '-SENS_STATUS-', 'red')
        else:
            SetLED(window, '-SENS_STATUS-', 'green')
        up.LogDisp('-LOG-', err)  
        
    if event=='-DIS_TEST-':
        if run_dis:
            try:
                print('Testing')
                async_result2 = pool.apply_async(PollDis,(s1, sensor, ax, fig_agg1))
                event=''
                run_dis = False
                err = ''
            except:
                err = 'ADC Not Open'
        else:
            print('Stopping')
            time.sleep(0.5)
            run_dis = True
        up.LogDisp('-LOG-',err)
    
    if event=='-VLOG_EN-':
        if run_vlog:
            print('run')
            try:
                chandle, status = VoltCon()
                async_result1 = pool.apply_async(VoltLog, (chandle, status, bx, fig_agg2))
                err = ''
            except:
                err = 'ADC24 Connection Failed'
            event=''
            run_vlog = False
        else:
            print('Stop')
            try:
                time.sleep(0.5)
                status["closeUnit"] = hrdl.HRDLCloseUnit(chandle)
                assert_pico2000_ok(status["closeUnit"])
                err = ''
            except:
                err = 'ADC24 Unexpected Close Error'
            run_vlog = True
            
        up.LogDisp('-LOG-',err)
            
    if event=='-RUN-':
        if run_log:
            event = ''
            run_log = False
            try:
                 delete_figure_agg(fig_agg1)
                 async_result4 = pool.apply_async(run, (arduino, sensor, canvas1))
                 err = ''
            except Exception as Arguments:
                 err = Arguments
                 print(Arguments)
            
        else:
            run_log = True
            delete_figure_agg(fig_agg3)
            fig_agg1 = draw_figure(canvas1, fig1)
        up.LogDisp('-LOG-',err)     
        
        

    
    if event == "Exit" or event == sg.WIN_CLOSED:
        print('close')
        try:
            s1.close_sensor(sensor)
            print('s1 closed')
        except:
            print('no s1 to close')
            pass
        try:
            status["closeUnit"] = hrdl.HRDLCloseUnit(chandle)
            assert_pico2000_ok(status["closeUnit"])
            print('ADC Closed')
        except:
            pass
        try:
            arduino.close()
        except:
            pass
        window.Close()
        break        

         
    
        
     

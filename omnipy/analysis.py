import numpy as np
import pandas as pd
import time
from scipy.signal import find_peaks
from scipy.fft import fft, fftfreq
from scipy.optimize import curve_fit



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

def Raw_Data_Collection(disp_sensor,step,freqLaser, ax, cx):

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
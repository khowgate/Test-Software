import time
from datetime import datetime





def PSU_run(dbSync,DC,instrument ,Inital_voltage_limit, Inital_current_limit, Overcurrent_protection, controlQue, reportQue):
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

def VoltLog(dbSync,unit, ax, fig_agg2, controlQue, event):

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


def PollDis(disp_sensor, ax, fig_agg1, event):
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
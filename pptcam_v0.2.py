#0.1 first test
#0.2 pulse measure and shutter release to seperate threads

import tkinter as tk
import tkinter.font

from PIL import Image,ImageTk, ImageDraw, ImageFont

import numpy as np

import time
from datetime import datetime

import RPi.GPIO as GPIO

from multiprocessing import Process,Queue

import threading

from scipy import signal

import gphoto2 as gp
import os

ver = 0.2 #2021-10-27

#GPIO setup
PPT_EMUL = 6
CAMERA_TRIG = 12
ACT_LED = 22

pulseTime = 0

primeTime = time.time() * 2

lastInput = 0
lastPath = ""

#window config
win = tk.Tk()

messagequeueP = Queue()
messagequeueT = Queue()
messagequeueC = Queue()

dataqueue = Queue()
controlqueue = Queue()
imagequeue =Queue()

def get_camera():
    camera = gp.Camera()
    camera.init()
    return camera
    
def capture_image(foldername):
    
    file_path = camera.capture(gp.GP_CAPTURE_IMAGE)
    
    target= os.path.join('/media/pi/ESD-USB/PPTCamData/' + foldername,file_path.name)
    camera_file = camera.file_get(file_path.folder,file_path.name, gp.GP_FILE_TYPE_NORMAL)
    camera_file.save(target)
    time.sleep(1)
    imagequeue.put(target)#push filename to image queue
    

    

def kill_thread():

    if messagequeueP.empty():#pulse thread finished so set pins to zero
        win.destroy()

        GPIO.output(PPT_EMUL,GPIO.LOW)
        GPIO.output(ACT_LED,GPIO.LOW)

        GPIO.cleanup(PPT_EMUL)
        GPIO.cleanup(CAMERA_TRIG)
        GPIO.cleanup(ACT_LED)
        
    else:
        win.after(10,kill_thread)
        
def exit_program():
    messagequeueP.put("stop")
    messagequeueT.put("stop")
    messagequeueC.put("stop")
    
    kill_thread()

def update_display():

    now=time.time() 
    
    
    #set last values for next draw
    global lastInput
    global primeTime
    global triggerText
    global triggerOn
    global filefolder
    global camera
    global label
    global lastPath
    
    #populate control array
        
    controls={   "triggerText" : triggerText.get(),
                 "triggerOn":triggerOn.get(),
                 "foldername":filefolder
                 }
        
                    
    controlqueue.put(controls)
    
    
    #checki gpio inputs
    if (GPIO.input(CAMERA_TRIG)):
        triggerindicator.configure(bg='green1')
        
    else:
        triggerindicator.configure(bg='green')

    imagepath = ""
    #check for new image
    while not imagequeue.empty():
        imagepath=imagequeue.get()
    
    if imagepath !="" and imageShow.get():    
        if imagepath != lastPath:
            img = Image.open(imagepath)
            print(imagepath)
            img = img.resize((720,480))
        
            pimg = ImageTk.PhotoImage(img)
        
            label.config(image=pimg)
            label.image = pimg
            lastPath = imagepath
        

  
    win.after(1,update_display)


def triggerClick():
    #nop
    a=1

def outputPulse():
    
    while messagequeueP.empty():#loop until message received
        now=time.perf_counter()
        pulseTime=now%2
        #print(pulseTime)
        
        
        if pulseTime>1.99: #10ms
            GPIO.output(PPT_EMUL,GPIO.HIGH)
            GPIO.output(ACT_LED,GPIO.HIGH)
        else:
            GPIO.output(PPT_EMUL,GPIO.LOW)
            GPIO.output(ACT_LED,GPIO.LOW)
    
    print("Pulse thread terminated")
    result = messagequeueP.get() #clear message queue
    
    
def camThread():
    
    triggertime = [0]
    primed = 0
    
    while messagequeueC.empty():#loop until message received        
        now=time.perf_counter()   
        
        #check for new trigger time (consume all up to latest - skip queued triggers)
        if primed == 0:
            while not dataqueue.empty():
                triggertime = dataqueue.get()
                primed = 1
            
        else:
            #wait for trigger time 
            if now >= triggertime[0]:
                #trigger camera shutter
                capture_image(triggertime[1])
                
               # print("Click " + str(now))
                primed = 0 
        
    
    print("Camera thread terminated")
    result = messagequeueC.get() #clear message queue
    
    
    
def triggerMonitor():
    counter=0
    counter2=0
    
    controls={   "triggerText" : "0.0",
                 "triggerOn":0,
                 "foldername":""}
    
    while messagequeueT.empty():#loop until message received
        
        now=time.perf_counter()
        
        #check for control array changes
        while not controlqueue.empty():
            controls=controlqueue.get()
        
        tds = float(controls["triggerText"])/1000.0
        triggeron  = controls["triggerOn"]
        foldername = controls["foldername"]
       
        
        #checki gpio inputs
        newinput = GPIO.input(CAMERA_TRIG)
        
        if (newinput):   
                       
            if (lastinput == 0  and triggeron):#rising edge
                datapoint=[now + tds,foldername,camera]                
                dataqueue.put(datapoint)
                print("trigger " +  str(triggeron) + "  " +  str(now))  
                counter = counter + 1
                
        lastinput = newinput
        counter2 = counter2 + 1
    
    print("Trigger thread terminated")
    result = messagequeueT.get() #clear message queue
    
    
def validateText(P):
    try:
        float(P)
    except:
        return False
    return True
        
    
def update_data():

    #background thread
    #from LVAD - TBD for PPT control

    counter=0

    #define filter - bandpass
    nyq=100
    lowP=14.5/nyq
    highP=23.5/nyq

    bpfilter = signal.firwin(30,[lowP,highP],pass_zero=False)

    filterz = signal.lfilter_zi(bpfilter,1)

    #lastdatainfo
    lastValue=0
    thresholdCrossed=False
    lastRTime=1
    lastActuationTime=0

    numVCyclesR=0
    numVCyclesD=0
    
    rrtime=1

    controls={   "filterOn" : 0,
                    "fallingedgeOn":0,
                    "continuousOn":0,
                    "actuationOn":0,
                    "arrProtectOn":1,
                    "eThreshold":512,
                    "dischargeValve":0,
                    "rechargeValve":0,
                    "eDelay":50,
                    "eHold":0,
                    "eRepeat":400,
                    "eContinuous":800,
                    "eOpenTimeR":50,
                    "eNCycR":5,
                    "eOpenTimeD":50,
                    "eNCycD":5}
                    
    print("Data loop starting")   
        
        
    while messagequeue.empty():#loop until message received
            
        atime=time.time()
        
        #check for control array changes
        while not controlqueue.empty():
            controls=controlqueue.get()
        
        #get latest value from channel 0
        value3=mcp.read_adc(0)
        value2=mcp.read_adc(3)
        value1=mcp.read_adc(2)
        value0=mcp.read_adc(1)        


        #check for low to high, not just high
        #check for falling edge if that option checked
        threshold = int(controls["eThreshold"])

        #create filtered version
        valuetemp , filterz = signal.lfilter(bpfilter,1,[value0],zi=filterz)      
      

        if controls["filterOn"]:

            scalefactor=0.1

            diffresult=valuetemp[0]-lastValue
        
            lastValue=valuetemp[0]   
            
            value0=diffresult*diffresult*scalefactor
       
            
        if ((value0 > threshold) != controls["fallingedgeOn"]) or controls["continuousOn"]: #brackets equiv to XOR
             
            #check if this is first loop after threshold crossed
            if (not thresholdCrossed) or controls["continuousOn"]: #only act on trigger if previously wasn't high/low and were npt
               
                rrtime=int((atime-lastRTime)*1000)
                          
                #variables to get from form
                postRDelay=int(controls["eDelay"])
                holdTime=int(controls["eHold"])
                minRepeatTime=int(controls["eRepeat"])
                valveOpenTimeR=int(controls["eOpenTimeR"])
                valveCyclesR=int(controls["eNCycR"])
                valveOpenTimeD=int(controls["eOpenTimeD"])
                valveCyclesD=int(controls["eNCycD"])
                
                
                if controls["continuousOn"]:
                    minRepeatTime=int(controls["eContinuous"])
                else:
                    if rrtime >= minRepeatTime: # this is "real" r wave if 
                        lastRTime=atime
      
                                        
                if controls["actuationOn"]:
                    


                    
                    if (atime-lastActuationTime) > minRepeatTime/1000:
                        
                        
                        if controls["continuousOn"]:
                            lastRTime=atime # this is continuous r wave time
                        
                        if (GPIO.input(MOTOR_HOME)):

                            threading.Timer(postRDelay/1000,lambda: GPIO.output(MOTOR_TRIG,GPIO.HIGH)).start()

                            threading.Timer((postRDelay+holdTime)/1000,lambda: GPIO.output(MOTOR_TRIG,GPIO.LOW)).start()


                            #add valve actuation requests also if required
                            if controls["dischargeValve"]:
                                #discharge valve request matches motor trigger
                                
                                threading.Timer(postRDelay/1000,lambda: GPIO.output(RECHARGE_VALVE,GPIO.HIGH)).start()

                                threading.Timer((postRDelay+valveOpenTimeD)/1000,lambda: GPIO.output(RECHARGE_VALVE,GPIO.LOW)).start()
                                
                              #  numVCyclesD+=1

                              #  if numVCyclesD>valveCyclesD-1:
                              #      rechargeValveButton.deselect()
                              #      numVCyclesD=0
                                    

                              #  labelCCycR.config(text=int(numVCyclesD))

                            if controls["rechargeValve"]:
                                #recharge valve  open on motor withdrwa                                
                                print("r")
                                threading.Timer((postRDelay+holdTime)/1000,lambda: GPIO.output(RECHARGE_VALVE,GPIO.HIGH)).start()

                                threading.Timer((postRDelay+holdTime+valveOpenTimeR)/1000,lambda: GPIO.output(RECHARGE_VALVE,GPIO.LOW)).start()
                                
                              #  numVCyclesR+=1

                              #  if numVCyclesR>valveCyclesR-1:
                              #      rechargeValveButton.deselect()
                              #      numVCycles=0
                                    

                              #  labelCCycR.config(text=int(numVCyclesR))
                  
                            
                            lastActuationTime=atime+postRDelay/1000
                    elif controls["arrProtectOn"]:#in case of arrhythmia protection, reset last actuation on every detection
                        lastActuationTime=atime+postRDelay/1000
                        
                    
            thresholdCrossed = True
            
        else:
            thresholdCrossed = False

        #print(rrtime)

        drive= GPIO.input(MOTOR_TRIG)            
        datapoint=[atime,counter,value0,value1,value2,drive,value3,rrtime]
        counter= (counter + 1) % 4096
        dataqueue.put(datapoint)

        #sync to 200Hz
        time.sleep(0.005-(time.time()%0.005))
        
   
    print("Thread terminated")
    result = messagequeue.get() #clear message queue

        
if __name__=='__main__':
    #main program start

    now = datetime.now()

    filefolder = now.strftime("%Y%m%d_%H%M%S")
    
    os.mkdir('/media/pi/ESD-USB/PPTCamData/' + filefolder)

    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    GPIO.setup(ACT_LED,GPIO.OUT)
    GPIO.setup(PPT_EMUL,GPIO.OUT)
    GPIO.setup(CAMERA_TRIG,GPIO.IN)
    
    try:
        camera = get_camera()
    except:
        print("camera not found")
        camera = 0

    #win.attributes("-fullscreen",True)

    win.title("PPT Cam Controller v%3.1f"%ver)
    myFont=tkinter.font.Font(family = 'Helvetica', size=12, weight='bold')



    #trigger control section

    triggerFrame = tk.LabelFrame(win, text="Trigger Control")
    
    valCommand = triggerFrame.register(validateText)

    triggerOn= tk.IntVar()
    triggerOnButton= tk.Checkbutton(triggerFrame,text="Trigger on Pulse",command = triggerClick,variable=triggerOn)

    triggerindicator=tk.Button(triggerFrame, bg='red1',text="", state="disabled", height=1, width=1)

    triggerText = tk.StringVar()

    triggerDelay=tk.Entry(triggerFrame, textvariable = triggerText, validate = "all", validatecommand= (valCommand, "%P"),width=8)
    
    triggerInc= tk.IntVar()
    triggerIncButton= tk.Checkbutton(triggerFrame,text="Auto Increment",variable=triggerInc, state="disabled")
    
    imageShow= tk.IntVar()
    imageShowButton= tk.Checkbutton(triggerFrame,text="Show Last Image",variable=imageShow)
    

    triggerOnButton.grid(row=0,column=0, sticky="W")

    tk.Label(triggerFrame, text="Trigger Delay (ms):").grid(row=1,column=0, sticky="E")
    
    triggerDelay.grid(row=1,column=1)
    
    triggerText.set("0.0")
    
    triggerindicator.grid(row=0,column=1)
    
    triggerIncButton.grid(row=2,column=1, sticky="W")
    
    imageShowButton.grid(row=3,column=0, sticky="W")
    
    #image display
    imageFrame = tk.LabelFrame(win, text="Recent Image")


    imX=720
    imY=480

    im = Image.new('RGB',(imX,imY),"black")
    img = ImageTk.PhotoImage(image=im)
    
    label=tk.Label(imageFrame,image = img)
    
    label.grid()


    #software control section
    softwareFrame = tk.LabelFrame(win, text="Software Control")
    exitButton=tk.Button(softwareFrame, text='Exit',command= lambda: exit_program())#, font=myFont, height=1, width=6)
    exitButton.grid(sticky="W", row=0)


    triggerFrame.grid(row=0,column=0,sticky="NSEW")
    imageFrame.grid(row=0,column=1,sticky="NSEW")

    softwareFrame.grid(row=5, columnspan=3,sticky="NSEW")


    #start pulse thread
    dataprocess=Process(target=outputPulse)
    dataprocess.start()
        
    #start trigger thread
    
    controls={   "triggerText" : triggerText.get(),
                 "triggerOn": triggerOn.get(),
                 "foldername":filefolder}
    
    controlqueue.put(controls)
    triggerprocess=Process(target=triggerMonitor)
    triggerprocess.start()
    
    #start camera thread
    cameraprocess=Process(target=camThread)
    cameraprocess.start()
    
   

    win.after(1,update_display)

    win.mainloop()

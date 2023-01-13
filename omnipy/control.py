

import ctypes
from picosdk.picohrdl import picohrdl as hrdl
from picosdk.functions import assert_pico2000_ok
import pyvisa
from datetime import datetime

from RazorBill.instruments.micro_epsilon import MEDAQLib
import serial
from pyfirmata import Arduino, util
from pyfirmata.util import Iterator

global event

        
class ADC24:
    
    def __init__(self):
        self.chandle = ctypes.c_int16()
        self.status = {}
        # Open unit
        self.status["openUnit"] = hrdl.HRDLOpenUnit()
        assert_pico2000_ok(self.status["openUnit"])
        self.chandle=self.status["openUnit"]

        # Set mains noise rejection
        # Reject 50 Hz mains noise
        self.status["mainsRejection"] = hrdl.HRDLSetMains(self.chandle, 0)
        assert_pico2000_ok(self.status["mainsRejection"])
        
        self.range = [0]*16
        self.conversion_time = [0]*16

    def close(self):
        self.status["closeUnit"] = hrdl.HRDLCloseUnit(self.chandle)
        assert_pico2000_ok(self.status["closeUnit"])

    def setup_channels(self, channels, channel_range, channel_conversion_time):
        self.channels = channels
        x = 0
        while x < len(channels):
            try:
                print(channels[x])
                self.range[x] = hrdl.HRDL_VOLTAGERANGE[channel_range[x]]
                self.Vmax = 2500/(2**self.range[x])
                min_count = ctypes.c_int32()
                max_count = ctypes.c_int32()
                self.status['ADCCounts'] = hrdl.HRDLGetMinMaxAdcCounts(self.chandle, ctypes.byref(min_count), ctypes.byref(max_count), channels[x])
                self.max_count = max_count.value
                self.conversion_time[x] = hrdl.HRDL_CONVERSIONTIME[channel_conversion_time[x]]
                x += 1
                print(self.max_count)
            except Exception as Arguments:
                return Arguments

    def getV(self):
        data = []
        x = 0
        while x < len(self.channels):
            overflow = ctypes.c_int16(0)
            value = ctypes.c_int32()
            self.status["getSingleValue"] = hrdl.HRDLGetSingleValue(self.chandle, self.channels[x], self.range[x], self.conversion_time[x], 0, ctypes.byref(overflow), ctypes.byref(value))
            data.append((value.value/self.max_count)*self.Vmax)
            x +=1
        return data

class DC_PSU:
    
    def __init__(self):
        self.rm = pyvisa.ResourceManager()
        self.state = {b'S\n':'On',b's\n':'On', b'\x12\n':'Off'
                      , b'2\n':'Off'}
        self.OUT = True
    
    def Iget(self, instrument):
        connection = self.rm.open_resource(instrument)
        DC_IOUT = (float(connection.query('IOUT1?')))
        connection.close()
        return DC_IOUT
    
    def Vget(self, instrument):
        connection = self.rm.open_resource(instrument)
        DC_VOUT = (float(connection.query('VOUT1?')))
        connection.close()
        return DC_VOUT
        
    def Iset(self, value, instrument):
        connection = self.rm.open_resource(instrument)
        command = 'ISET1:'+str(value)
        # print(command)
        connection.write(command)
        connection.close()
        return
    
    def Vset(self, value, instrument):
        connection = self.rm.open_resource(instrument)
        command = 'VSET1:'+str(value)
        # print(command)
        connection.write(command)
        connection.close()
        return
    
    def SetOutputState(self, instrument, **kwags:"state"):
        connection = self.rm.open_resource(instrument)
        # print(kwags)
        if kwags == {'state':'On'}:
            connection.write('OUT1')
            self.OUT = False
            print('supply Turned on')
        elif kwags == {'state':'Off'}:
            connection.write('OUT0')
            self.OUT = True
        else:
            print('supply toggling')
            if self.OUT:
                self.OUT = False
                connection.write('OUT0')
            else:
                self.OUT = True
                connection.write('OUT1')
        
        return self.OUT
    
    def SetOverCurrentProtection(self, instrument, state):
        connection = self.rm.open_resource(instrument)
        connection.write('OCP'+str(state))
        connection.close()
        
    
    def GetOutputState(self, instrument):
        connection = self.rm.open_resource(instrument)
        connection.write('STATUS?')
        responce = connection.read_raw()
        # print(self.state[responce])
        try:
            return self.state[responce]
        except:
            return responce
    
    def identify(self, instrument):
        connection = self.rm.open_resource(instrument)
        connection.write('*IDN?')
        responce = connection.read_raw()
        return responce
    
    def list_available(self):
        return self.rm.list_resources()
    
    
    def close(self):
        self.rm.close()
        
class ILD:
    
    
    def __init__(self, port):
        self.s1 = MEDAQLib()

        self.sensor = self.s1.create_sensor("SENSOR_ILD1420")
        
        self.s1.set_parameter_string(self.sensor, "IP_Interface", "RS232")
        self.s1.set_parameter_int(self.sensor, "IP_EnableLogging", 1)
        self.s1.set_parameter_string(self.sensor, "IP_Port", port)
        baud = self.s1.get_error_text(self.sensor)
        self.s1.open_sensor(self.sensor)

        #return err
    
    def poll(self):
        now = datetime.now()
        t = now.strftime("%H:%M:%S:%f")
        print(t)
        
        value = self.s1.poll(self.sensor,1)      
        if value[0] > 50 or value[0] < 0:
            value = 0
        else:
            value = value[0]
        return value, t
           
    def block_data(self):
        N = self.s1.data_available(self.sensor)
        return self.s1.data_transfer(self.sensor, N)

    def close(self):
        self.s1.close_sensor(self.sensor)
        
class Arduino:
    
    def __init__(self, Port):
        self.shortState = {'HIGH':'H','LOW':'L','TOGGLE':'T'}
        self.openPins = [13]
        self.arduino = serial.Serial(port=Port, baudrate=115200, timeout=.1)
        self.arduino.reset_input_buffer()

    def Pins(self,pin, state):
        if pin != self.openPins:
            return
        return str(pin)+self.shortState[state]

    def PinControl(self, command):
        try:
            out_bytes = self.arduino.write(bytes(command), 'utf-8')
        except:
            return 'Arduino unavailable'
    
    def close (self):
        self.arduino.close()
        
def arduinoBuiltIn(board):
    it = util.Iterator(board)
    it.start()
    cam = board.get_pin('d:12:o')
    ign = board.get_pin('d:13:o')
    volt = board.get_pin('a:0:i')
    # volt.enable_reporting()

    return cam, ign, volt

        
        

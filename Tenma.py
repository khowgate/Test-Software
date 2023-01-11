# -*- coding: utf-8 -*-
"""
Created on Tue Dec  6 09:25:37 2022

@author: KristianHowgate
"""

import pyvisa

class DC_PSU:
    
    def __init__(self):
        self.rm = pyvisa.ResourceManager()
        self.state = {b'S\n':'On', b'\x12\n':'Off'}
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
        print(command)
        connection.write(command)
        connection.close()
        return
    
    def Vset(self, value, instrument):
        connection = self.rm.open_resource(instrument)
        command = 'VSET1:'+str(value)
        print(command)
        connection.write(command)
        connection.close()
        return
    
    def SetOutputState(self, instrument, **kwags):
        connection = self.rm.open_resource(instrument)
        print(kwags)
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
    
    def GetOutputState(self, instrument):
        connection = self.rm.open_resource(instrument)
        connection.write('STATUS?')
        responce = connection.read_raw()
        print(self.state[responce])
        return self.state[responce]
    
    def list_available(self):
        return self.rm.list_resources()
    
    def close(self):
        self.rm.close()



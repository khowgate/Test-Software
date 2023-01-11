
from pyfirmata import Arduino, util
from pyfirmata.util import Iterator
import time

board  = Arduino('COM3')
builtIn = board.get_pin('d:13:o')
while True:
    builtIn.write(1)
    time.sleep(0.5)
    builtIn.write(0)
    time.sleep(0.5)



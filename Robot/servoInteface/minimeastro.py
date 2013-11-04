import serial
import time

__all__ = ['Maestro12', ]

class Maestro12(object):
    
    HOME = 0xA2
    MOVE = 0x84
    SPEED = 0x87
    ACCELERATION = 0x98
    POSITION = 0x90
    MOVING_STATE = 0x93
    ERRORS = 0xA1
    
    def __init__(self, portstring, portspeed):
        self._conn = serial.Serial(portstring, portspeed)

    def write(self, buf):
        self._conn.write(buf)

    def go_home(self):
        self.write([Maestro12.HOME])

    def setPosition(self, servo, value):
        highbits, lowbits = divmod(value, 32)
        self.write([Maestro12.MOVE, servo, lowbits << 2, highbits])

    def setSpeed(self, servo, speed):
        highbits, lowbits = divmod(speed, 32)
        self.write([Maestro12.SPEED, servo, lowbits << 2, highbits])
  
    def setAcceleration(self, servo, acceleration):
        highbits, lowbits = divmod(acceleration, 32)
        self.write([Maestro12.ACCELERATION, servo, lowbits << 2, highbits])

    def getPosition(self, servo):
        self.write([Maestro12.POSITION, servo])
        data = self.ser.read(2)
        if data:
            return (ord(data[0]) + (ord(data[1]) << 8))
        else:
            return None

    def getMovingState(self):
        self.write([Maestro12.MOVING_STATE])
        data = self.ser.read(1)
        if data:
            return ord(data[0])
        else:
            return None

    def get_errors(self):
        self.write([Maestro12.ERRORS])
        data = self.ser.read(2)
        if data:
            return ord(data[0]) + (ord(data[1]) << 8)
        else:
            return None

    def waitUntilAtTarget(self):
        while (self.getMovingState()):
            time.sleep(0.01)

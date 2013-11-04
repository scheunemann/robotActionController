from dynamixel import ServoController as AX12Controller
from herkulex import HerkuleX
from threading import RLock
import serial

__all__ = ['Connection', ]

class Connection(object):

    _globalLock = RLock()
    _connections = {}
    _locks = {}
    
    @staticmethod
    def getLock(connection):
        if not Connection._locks.has_key(connection):
            Connection._locks[connection] = RLock()

        return Connection._locks[connection]
    
    @staticmethod
    def getConnection(connectionType, port, speed):        
        with Connection._globalLock:
            #TODO: Check for closed connections
            if not Connection._connections.has_key(port):
                if connectionType == "AX12":
                    Connection._connections[port] = AX12Controller(port, speed)
                elif connectionType == "HERKULEX":
                    Connection._connections[port] = HerkuleX(port, speed) 
                else:
                    Connection._connections[port] = serial.Serial(port=port, baudrate=speed, timeout=5)
            
            return Connection._connections[port]

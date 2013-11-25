from Robot.ServoInterface.dynamixel import ServoController as AX12Controller
from Robot.ServoInterface.herkulex import HerkuleX
from threading import RLock
import serial

__all__ = ['Connection', ]


class Connection(object):

    _globalLock = RLock()
    _connections = {}
    _locks = {}

    @staticmethod
    def getLock(connection):
        if connection not in Connection._locks:
            Connection._locks[connection] = RLock()

        return Connection._locks[connection]

    @staticmethod
    def getConnection(connectionType, port, speed):
        with Connection._globalLock:
            # TODO: Check for closed connections
            if port not in Connection._connections:
                if connectionType == "AX12":
                    try:
                        Connection._connections[port] = AX12Controller(port, speed)
                    except serial.serialutil.SerialException as e:
                        return None
                elif connectionType == "HERKULEX":
                    Connection._connections[port] = HerkuleX(port, speed)
                else:
                    Connection._connections[port] = serial.Serial(port=port, baudrate=speed, timeout=5)

            return Connection._connections[port]

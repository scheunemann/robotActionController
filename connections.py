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
            key = "%s:%s" % (connectionType, port)
            # TODO: Check for closed connections
            if key not in Connection._connections:
                if connectionType == "AX12":
                    from Robot.ServoInterface.dynamixel import ServoController as AX12Controller
                    Connection._connections[key] = AX12Controller(port, speed)
                elif connectionType == "HERKULEX":
                    from Robot.ServoInterface.herkulex import HerkuleX
                    Connection._connections[key] = HerkuleX(port, speed)
                elif connectionType == "minimaestro":
                    from Robot.ServoInterface.minimaestro import minimaestro
                    Connection._connections[key] = minimaestro(port, speed)
                else:
                    try:
                        Connection._connections[key] = serial.Serial(port=port, baudrate=speed, timeout=5)
                    except serial.serialutil.SerialException as e:
                        raise e

            return Connection._connections[key]

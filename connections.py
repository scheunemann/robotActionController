from threading import RLock
import serial
import logging

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
    def getConnection(connectionType, port, speed, **kwargs):
        log = logging.getLogger(__name__)
        with Connection._globalLock:
            key = "%s:%s" % (connectionType, port)
            # TODO: Check for closed connections
            if key not in Connection._connections:
                logging.info('Creating connection: %s (%s)' % (connectionType, port))
                if connectionType == "AX12":
                    from Robot.ServoInterface.dynamixel import ServoController as AX12Controller
                    Connection._connections[key] = AX12Controller(port, speed, **kwargs)
                elif connectionType == "HERKULEX":
                    from Robot.ServoInterface.herkulex import HerkuleX
                    Connection._connections[key] = HerkuleX(port, speed, **kwargs)
                elif connectionType == "minimaestro":
                    from Robot.ServoInterface.minimaestro import minimaestro
                    Connection._connections[key] = minimaestro(port, speed, **kwargs)
                else:
                    try:
                        kwargs.setdefault('timeout', 5)
                        Connection._connections[key] = serial.Serial(port=port, baudrate=speed, **kwargs)
                    except serial.serialutil.SerialException as e:
                        raise e

            return Connection._connections[key]

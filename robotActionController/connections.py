from threading import RLock
import serial
import logging
import platform

__all__ = ['Connection', ]


if platform.system() == 'Linux':
    import fcntl
    class SerialLock(object):

        def __init__(self, serial):
            self._serial = serial
            # file descriptor locks are not recursive, so keep a recursive lock
            # in order to make this class recursible
            self._rlock = RLock()

        def __enter__(self):
            if self._rlock._is_owned():
                self._rlock.acquire()
                return
            else:
                self._rlock.acquire()
                fcntl.flock(self._serial.fileno(), fcntl.LOCK_EX)

        def __exit__(self, type, value, tb):
            self._rlock.release()
            if not self._rlock._is_owned():
                fcntl.flock(self._serial.fileno(), fcntl.LOCK_UN)
else:
    SerialLock = lambda x: RLock()


class Connection(object):

    _globalLock = RLock()
    _connections = {}
    _locks = {}

    @staticmethod
    def getLock(connection):
        if connection not in Connection._locks:
            if type(connection) == serial.Serial:
                Connection._locks[connection] = SerialLock(connection)
            else:
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

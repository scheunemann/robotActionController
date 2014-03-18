import connections


class minimaestro(object):
    GO_HOME = 0xA2
    SET_TARGET = 0x84
    SET_SPEED = 0x87
    SET_ACCEL = 0x89
    GET_POS = 0x90
    GET_MOVING = 0x93
    GET_ERRORS = 0xA1

    def __init__(self, ser_port, ser_speed):
        self._conn = connections.Connection.getConnection('serial', ser_port, ser_speed)

    def goHome(self):
        self._conn.write(minimaestro.GO_HOME)

    def setTarget(self, id_, target):
        """
        ...if channel 2 is configured as a servo and you want to set its target to 1500 us (1500x4 = 6000 =
        01011101110000 in binary), you could send the following...
        """
        target = target * 4

        cmd = minimaestro.SET_TARGET
        lowByte = target & 0x7F
        highByte = (target >> 7) & 0x7F
        data = chr(cmd) + chr(id_) + chr(lowByte) + chr(highByte)
        self._conn.write(data)

    def setSpeed(self, id_, speed):
        cmd = minimaestro.SET_SPEED
        lowByte = speed & 0x7F
        highByte = (speed >> 7) & 0x7F
        data = chr(cmd) + chr(id_) + chr(lowByte) + chr(highByte)
        self._conn.write(data)

    def setAcceleration(self, id_, accel):
        cmd = minimaestro.SET_ACCEL
        lowByte = accel & 0x7F
        highByte = (accel >> 7) & 0x7F
        data = chr(cmd) + chr(id_) + chr(lowByte) + chr(highByte)
        self._conn.write(data)

    def getPosition(self, id_):
        cmd = minimaestro.GET_POS
        data = chr(cmd) + chr(id_)
        self._conn.write(data)
        lowByte = self._conn.read()
        highByte = self._conn.read()

        rawVal = (ord(highByte) << 8) + ord(lowByte)

        """
        Note that the position value returned by this command is equal to four times the number displayed in the Position box
        in the Status tab of the Maestro Control Center
        """
        return rawVal / 4

    def getMovingState(self):
        cmd = minimaestro.GET_MOVING
        data = chr(cmd)
        self._conn.write(data)
        return ord(self._conn.read())

    def getErrors(self):
        cmd = minimaestro.GET_ERRORS
        data = chr(cmd)
        self._conn.write(data)
        lowByte = self._conn.read()
        highByte = self._conn.read()

        error = (ord(highByte) << 8) + ord(lowByte)
        return error

if __name__ == '__main__':
    import time
    m = minimaestro("COM14", 115200)
    while True:
        try:
            m.setTarget(8, 1000)
            print m.getPosition(8)
            time.sleep(1)
            m.setTarget(8, 2000)
            print m.getPosition(8)
            time.sleep(1)
        except KeyboardInterrupt:
            break

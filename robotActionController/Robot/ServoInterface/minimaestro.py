from robotActionController import connections


class minimaestro(object):
    # From pololu-usb-sdk\Maestro\protocol.h
    class uscCommand(object):
        COMMAND_SET_TARGET = 0x84  # 3 data bytes
        COMMAND_SET_SPEED = 0x87  # 3 data bytes
        COMMAND_SET_ACCELERATION = 0x89  # 3 data bytes
        COMMAND_GET_POSITION = 0x90  # 0 data
        COMMAND_GET_MOVING_STATE = 0x93  # 0 data
        COMMAND_GET_ERRORS = 0xA1  # 0 data
        COMMAND_GO_HOME = 0xA2  # 0 data
        COMMAND_STOP_SCRIPT = 0xA4  # 0 data
        COMMAND_RESTART_SCRIPT_AT_SUBROUTINE = 0xA7  # 1 data bytes
        COMMAND_RESTART_SCRIPT_AT_SUBROUTINE_WITH_PARAMETER = 0xA8  # 3 data bytes
        COMMAND_GET_SCRIPT_STATUS = 0xAE  # 0 data
        COMMAND_MINI_SSC = 0xFF  # (2 data bytes)

    class uscRequest(object):
        REQUEST_GET_PARAMETER = 0x81
        REQUEST_SET_PARAMETER = 0x82
        REQUEST_GET_VARIABLES = 0x83
        REQUEST_SET_SERVO_VARIABLE = 0x84  # (also clears the serial timeout timer)
        REQUEST_SET_TARGET = 0x85  # (also clears the serial timeout timer)
        REQUEST_CLEAR_ERRORS = 0x86  # (also clears the serial timeout timer)
        REQUEST_REINITIALIZE = 0x90
        REQUEST_ERASE_SCRIPT = 0xA0
        REQUEST_WRITE_SCRIPT = 0xA1
        REQUEST_SET_SCRIPT_DONE = 0xA2  # value.low.b is 0 for go 1 for stop 2 for single-step
        REQUEST_RESTART_SCRIPT_AT_SUBROUTINE = 0xA3
        REQUEST_RESTART_SCRIPT_AT_SUBROUTINE_WITH_PARAMETER = 0xA4
        REQUEST_RESTART_SCRIPT = 0xA5
        REQUEST_START_BOOTLOADER = 0xFF

    # These are the bytes used to refer to the different parameters
    # in REQUEST_GET_PARAMETER and REQUEST_SET_PARAMETER.  After changing
    # any parameter marked as an "Init parameter" you must do REQUEST_REINITIALIZE
    # before the new value will be used.
    class uscParameter(object):
        PARAMETER_SERVOS_AVAILABLE = 1  # 1 byte - 0-5.  Init parameter.
        PARAMETER_SERVO_PERIOD = 2  # 1 byte - instruction cycles allocated to each servo/256 (units of 21.3333 us).  Init parameter.
        PARAMETER_SERIAL_MODE = 3  # 1 byte unsigned value.  Valid values are SERIAL_MODE_*.  Init parameter.
        PARAMETER_SERIAL_FIXED_BAUD_RATE = 4  # 2-byte unsigned value; 0 means autodetect.  Init parameter.
        PARAMETER_SERIAL_TIMEOUT = 6  # 2-byte unsigned value (units of 10ms)
        PARAMETER_SERIAL_ENABLE_CRC = 8  # 1 byte boolean value
        PARAMETER_SERIAL_NEVER_SUSPEND = 9  # 1 byte boolean value
        PARAMETER_SERIAL_DEVICE_NUMBER = 10  # 1 byte unsigned value 0-127
        PARAMETER_SERIAL_BAUD_DETECT_TYPE = 11  # 1 byte - reserved

        PARAMETER_IO_MASK_A = 12  # 1 byte - reserved init parameter
        PARAMETER_OUTPUT_MASK_A = 13  # 1 byte - reserved init parameter
        PARAMETER_IO_MASK_B = 14  # 1 byte - reserved init parameter
        PARAMETER_OUTPUT_MASK_B = 15  # 1 byte - reserved init parameter
        PARAMETER_IO_MASK_C = 16  # 1 byte - pins used for I/O instead of servo init parameter
        PARAMETER_OUTPUT_MASK_C = 17  # 1 byte - outputs that are enabled init parameter
        PARAMETER_IO_MASK_D = 18  # 1 byte - reserved init parameter
        PARAMETER_OUTPUT_MASK_D = 19  # 1 byte - reserved init parameter
        PARAMETER_IO_MASK_E = 20  # 1 byte - reserved init parameter
        PARAMETER_OUTPUT_MASK_E = 21  # 1 byte - reserved init parameter

        PARAMETER_SCRIPT_CRC = 22  # 2 byte CRC of script
        PARAMETER_SCRIPT_DONE = 24  # 1 byte - if 0 run the bytecode on restart if 1 stop

        PARAMETER_SERIAL_MINI_SSC_OFFSET = 25  # 1 byte (0-254)

        PARAMETER_SERVO0_HOME = 30  # 2 byte home position (0=off; 1=ignore)
        PARAMETER_SERVO0_MIN = 32  # 1 byte min allowed value (x2^6)
        PARAMETER_SERVO0_MAX = 33  # 1 byte max allowed value (x2^6)
        PARAMETER_SERVO0_NEUTRAL = 34  # 2 byte neutral position
        PARAMETER_SERVO0_RANGE = 36  # 1 byte range
        PARAMETER_SERVO0_SPEED = 37  # 1 byte (5 mantissa3 exponent) us per 10ms.  Init parameter.
        PARAMETER_SERVO0_ACCELERATION = 38  # 1 byte (speed changes that much every 10ms). Init parameter.

        PARAMETER_SERVO1_HOME = 39
        # The pattern continues.  Each servo takes 9 bytes of configuration space.

    def __init__(self, ser_port, ser_speed):
        self._conn = connections.Connection.getConnection('serial', ser_port, ser_speed)
        self._lock = connections.Connection.getLock(self._conn)

    def goHome(self):
        with self._lock:
            self._conn.write(minimaestro.uscCommand.COMMAND_GO_HOME)

    def setTarget(self, id_, target):
        """
        ...if channel 2 is configured as a servo and you want to set its target to 1500 us (1500x4 = 6000 =
        01011101110000 in binary), you could send the following...
        """
        target = target * 4

        cmd = minimaestro.uscCommand.COMMAND_SET_TARGET
        lowByte = target & 0x7F
        highByte = (target >> 7) & 0x7F
        data = chr(cmd) + chr(id_) + chr(lowByte) + chr(highByte)
        with self._lock:
            self._conn.write(data)

    def setSpeed(self, id_, speed):
        cmd = minimaestro.uscCommand.COMMAND_SET_SPEED
        lowByte = speed & 0x7F
        highByte = (speed >> 7) & 0x7F
        data = chr(cmd) + chr(id_) + chr(lowByte) + chr(highByte)
        with self._lock:
            self._conn.write(data)

    def setAcceleration(self, id_, accel):
        cmd = minimaestro.uscCommand.COMMAND_SET_ACCELERATION
        lowByte = accel & 0x7F
        highByte = (accel >> 7) & 0x7F
        data = chr(cmd) + chr(id_) + chr(lowByte) + chr(highByte)
        with self._lock:
            self._conn.write(data)

    def getDeviceId(self):
        cmd = minimaestro.uscRequest.REQUEST_GET_PARAMETER
        param = minimaestro.uscParameter.PARAMETER_SERIAL_DEVICE_NUMBER
        data = chr(cmd) + chr(param)
        with self._lock:
            self._conn.write(data)
            return ord(self._conn.read())

    def getPosition(self, id_):
        cmd = minimaestro.uscCommand.COMMAND_GET_POSITION
        data = chr(cmd) + chr(id_)
        with self._lock:
            self._conn.write(data)
            lowByte = self._conn.read()
            highByte = self._conn.read()

        if len(highByte) == 0 or len(lowByte) == 0:
            return -1

        rawVal = (ord(highByte) << 8) + ord(lowByte)

        """
        Note that the position value returned by this command is equal to four times the number displayed in the Position box
        in the Status tab of the Maestro Control Center
        """
        return rawVal / 4

    def getMovingState(self):
        cmd = minimaestro.uscCommand.COMMAND_GET_MOVING_STATE
        data = chr(cmd)
        with self._lock:
            self._conn.write(data)
            return ord(self._conn.read())

    def getErrors(self):
        cmd = minimaestro.uscCommand.COMMAND_GET_ERRORS
        data = chr(cmd)
        with self._lock:
            self._conn.write(data)
            lowByte = self._conn.read()
            highByte = self._conn.read()

        error = (ord(highByte) << 8) + ord(lowByte)
        return error

if __name__ == '__main__':
    m = minimaestro("COM16", 115200)
    print m.getDeviceId()
#     while True:
#         try:
#             m.setTarget(8, 1000)
#             print m.getPosition(8)
#             time.sleep(1)
#             m.setTarget(8, 2000)
#             print m.getPosition(8)
#             time.sleep(1)
#         except KeyboardInterrupt:
#             break

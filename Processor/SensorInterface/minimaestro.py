import serial


class minimaestro(object):
    def __init__(self, con_port, ser_port, timeout=1):
        self.con = None
        self.ser = None
        self.isInitialized = False
        try:
            self.con = serial.Serial(con_port, timeout=timeout)
            self._logger.info("Link to Command Port -%s- successful", con_port)
        except serial.serialutil.SerialException, e:
            self._logger.debug(e)
            self._logger.info("Link to Command Port -%s- failed", con_port)
        else:
            #####################
            # If your Maestro's serial mode is "UART, detect baud rate", you must first send it the baud rate indication byte 0xAA on
            # the RX line before sending any commands. The 0xAA baud rate indication byte can be the first byte of a Pololu protocol
            # command.
            # http://www.pololu.com/docs/pdf/0J40/maestro.pdf - page 35
            self.con.write(chr(0xAA))
            self._logger.info("Baud rate indication byte 0xAA sent!")

        try:
            self.ser = serial.Serial(ser_port, timeout=timeout)
            self._logger.info("Link to TTL Port -%s- successful", ser_port)
        except serial.serialutil.SerialException, e:
            self._logger.debug(e)
            self._logger.info("Link to TTL Port -%s- failed", ser_port)

        self.isInitialized = (self.con != None and self.ser != None)
        self._logger.info("Device initialized:", self.isInitialized)

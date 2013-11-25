import serial
from threading import Thread, RLock
import logging


class FSR(object):

    def __init__(self, port, speed):
        self._logger = logging.getLogger(self.__class__.__name__)
        self._port = serial.Serial(port, speed)
        self._filterLength = 10
        self._dataLock = RLock()
        self._data = []
        self._packetLength = self._getPacketLength()
        (self._offsets, self._postscalers) = self._getFilter()
        self._sensorPoller = Thread(target=self._pollSensors)
        self._run = True
        self._sensorPoller.start()

    def __del__(self):
        self._run = False
        self._sensorPoller.join()

    def _getPacketLength(self):
        while ord(self._port.read()) & 0xFF != 0xAB:
            pass

        c = 0
        while ord(self._port.read()) & 0xFF != 0xAB:
            c += 1
        return c

    def _getNextPacket(self):
        # Discard data to the start of the packet
        byte = ord(self._port.read()) & 0xFF
        c = 0
        while byte != 0xAB:
            byte = ord(self._port.read()) & 0xFF
            c += 1

        if c > 0:
            print "Skipped %s bytes to start, packet length = %s" % (c, self._packetLength)

        packetRaw = self._port.read(self._packetLength)
        packet = [1023 - (ord(packetRaw[i]) * 256) - ord(packetRaw[i + 1]) for i in range(0, len(packetRaw), 2)]
        return packet

    def _getFilter(self):
        data_values = []

        for _ in range(0, self._filterLength):
            data_values.append(self._getNextPacket())

        offsets = self._calculateOffset(data_values)
        postscalars = self._calculatePostScaler(offsets)
        return (offsets, postscalars)

    # Below the functions used to filter the signal
    """ Calculate the postScaler providing the offset """
    def _calculatePostScaler(self, offsets):
        postscaler = []
        for offset in offsets:
            postscaler.append(1023 / (1023 - min(offset, 1022)))
        return postscaler

    """ calculate the offset once we have the data on the data """
    def _calculateOffset(self, sensorSamples):
        count = min([len(s) for s in sensorSamples])
        offsets = [0] * count
        for sample in sensorSamples:
            if len(sample) != count:
                self._logger.warn("Incorrect sample length, expected: %s got: %s", count, len(sample))

            for i in range(0, count):
                offsets[i] = max(offsets[i], sample[i])

        return offsets

    def getValue(self, id_):
        with self._dataLock:
            if id_ < len(self._data):
                data = self._data[id_]
            else:
                self._logger.debug("FSR id %s out of range", id_)
                return None

        return self._postscalers[id_] * (data - self._offsets[id_])

    def _pollSensors(self):
        while self._run:
            data = self._getNextPacket()
            with self._dataLock:
                self._data = data

if __name__ == '__main__':
    s = FSR("COM10", 19200)
    while True:
        print [s.getValue(i) for i in range(0, 16)]

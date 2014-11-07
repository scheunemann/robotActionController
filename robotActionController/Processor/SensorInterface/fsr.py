from robotActionController import connections
from robotActionController.Processor.SensorInterface import SensorPoller
import logging
from gevent import spawn
from gevent.lock import RLock

__all__ = ['FSR_Arduino', ]


class FSR_Arduino(object):
    sensorType = 'FSR_Arduino'

    def __init__(self, port, speed):
        self._logger = logging.getLogger(self.__class__.__name__)
        self._port = connections.Connection.getConnection('arduino', port, speed)
        self._portLock = connections.Connection.getLock(self._port)
        self._filterLength = 10
        self._dataLock = RLock()
        self._data = []
        self._packetLength = self._getPacketLength()
        (self._offsets, self._postscalers) = self._getFilter()
        self._run = True
        self._sensorPoller = spawn(self._pollSensors)
        self._sensorPoller.start()

    def __del__(self):
        self._run = False
        self._sensorPoller.join()

    def _getPacketLength(self):
        with self._portLock:
            while ord(self._port.read()) & 0xFF != 0xAB:
                pass

            c = 0
            while ord(self._port.read()) & 0xFF != 0xAB:
                c += 1
        return c

    def _getNextPacket(self):
        # Discard data to the start of the packet
        with self._portLock:
            byte = ord(self._port.read()) & 0xFF
            c = 0
            while byte != 0xAB:
                byte = ord(self._port.read()) & 0xFF
                c += 1

            if c > 0:
                self._logger.info("Skipped %s bytes to start, packet length = %s" % (c, self._packetLength))

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


class FSR_MiniMaestro(object):
    sensorType = 'FSR_MiniMaestro'

    def __init__(self, sensor, config):
        port = config.port
        self._port = port
        speed = config.portSpeed
        self._externalId = sensor.extraData.get('externalId', None)
        if self._externalId == None:
            self._logger.critical("%s sensor %s is missing its external Id!", (sensor.model.name, sensor.name))
            raise ValueError()
        self._externalId = int(self._externalId)

        self._numSamples = sensor.extraData.get('numSamples', 10)
        conn = connections.Connection.getConnection('minimaestro', port, speed)
        self._poller = SensorPoller.getPoller(conn)


    def getCurrentValue(self):
        hist = self._poller.getValues(self._externalId)

        if hist:
            samples = hist[-1 * min(len(hist), self._numSamples):]
            return float(sum(samples)) / len(samples)
        else:
            return None

#TODO: Temporary hack until I can modify the robot.xml to support multiple sensors of the same type
# on different ports
class FSR_MiniMaestro2(FSR_MiniMaestro):
    sensorType = 'FSR_MiniMaestro2'


if __name__ == '__main__':
    class S(object):
        port = "COM14"
        speed = 115200
        extraData = {'externalId': 0}

    import time
    m = FSR_MiniMaestro(S(), S())
    while True:
        try:
            print m.getCurrentValue()
            time.sleep(1 / 50.0)
        except KeyboardInterrupt:
            break

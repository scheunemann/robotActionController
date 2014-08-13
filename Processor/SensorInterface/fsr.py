import connections
from collections import namedtuple, deque
from threading import Thread, RLock
import time

import logging

__all__ = ['FSR_Arduino', ]


class FSR_Arduino(object):
    sensorType = 'FSR_Arduino'

    def __init__(self, port, speed):
        self._logger = logging.getLogger(self.__class__.__name__)
        self._port = connections.Connection.getConnection('arduino', port, speed)
#         self._port = serial.Serial(port, speed)
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


class Sensor_Poller(Thread):

    HistItem = namedtuple('SensorHist', ['hist', 'sensor_id', 'lastValue'])

    def __init__(self, connection, rate=60, maxHistory=60, ids=[]):
        """
        @param connection: connection object to use, must support getPosition(id)
        @param rate: rate of the polling loop
        @param maxHistory: size of the history for each sensor
        @param ids: the initial id set to poll
        """
        super(Sensor_Poller, self).__init__()
        self.daemon = True
        self._conn = connection
        self._rate = rate
        self._rateMS = 1.0 / rate
        self._maxHistory = maxHistory
        self._sensors = {}
        self._threadLock = RLock()
        map(self.addId, ids)

    def addId(self, sid):
        with self._threadLock:
            if id not in self._sensors:
                self._sensors[sid] = deque(maxlen=self._maxHistory)

    def cancel(self):
        self._run = False
        self.join()

    def getValues(self, sid, default=None):
        with self._threadLock:
            if id in self._sensors:
                return self._sensors[sid].hist
            else:
                return default

    def run(self):
        self._run = True
        while self._run:
            with self._threadLock:
                sensors = self._sensors.items()
            if not sensors:
                time.sleep(1)
                continue
            sTime = self._rateMS / len(sensors)
            for (sid, hist) in sensors:
                if not self._run:
                    break
                startTime = time.time()
                try:
                    val = self._conn.getPosition(sid)
                except Exception as e:
                    self._logger.warning(e, exc_info=True)
                    continue

                if val < 0:
                    # maestro/herkulex specific, might need to look into a general 'error_value' param
                    continue

                hist.hist.append(val)
                # hist.lastValue = sum(hist.hist) / len(hist.hist)
                sTime = time.time() - startTime
                if sTime > 0:
                    time.sleep(sTime)


class FSR_MiniMaestro(object):
    sensorType = 'FSR_MiniMaestro'
    _pollers = {}
    _pollerLock = RLock()

    def __init__(self, sensor, config):
        port = config.port
        speed = config.portSpeed
        self._externalId = sensor.extraData.get('externalId', None)
        if self._externalId == None:
            self._logger.critical("%s sensor %s is missing its external Id!", (sensor.model.name, sensor.name))
            raise ValueError()
        self._externalId = int(self._externalId)

        self._numSamples = sensor.extraData.get('numSamples', 10)
        with FSR_MiniMaestro._pollerLock:
            if port not in FSR_MiniMaestro._pollers:
                FSR_MiniMaestro._pollers[port] = Sensor_Poller(port, speed)
                FSR_MiniMaestro._pollers[port].start()

        self._port = port
        # self._conn = connections.Connection.getConnection('minimaestro', port, speed)

    def getCurrentValue(self):
        with FSR_MiniMaestro._pollerLock:
            hist = FSR_MiniMaestro._pollerLock[self._port].getValues(self._externalId)

        samples = hist[-1 * min(len(hist), self._numSamples):]
        return float(sum(samples)) / len(samples)


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

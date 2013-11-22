from threading import Thread
from multiprocessing.pool import ThreadPool
from datetime import datetime, timedelta
from collections import namedtuple
from SensorInterface.sensorInterface import SensorInterface
import time
import event


__all__ = ['SensorProcessor', ]

SensorDataEventArg = namedtuple('SensorDataEvent', ['sensor_id', 'value'])


class SensorProcessor(object):

    newSensorData = event.Event('Sensor update event')

    def __init__(self, sensors, maxUpdateInterval=None):
        self._handlers = []
        for sensor in sensors:
            handler = _SensorHandler(sensor, self.newSensorData, maxUpdateInterval, timedelta(seconds=maxUpdateInterval.seconds / 10.0))
            handler.start()
            self._handlers.append(handler)

    def __del__(self):
        pool = ThreadPool()
        pool.map(lambda h: h.stop(), self._handlers)


class _SensorHandler(Thread):

    def __init__(self, sensor, updateEvent, maxUpdateInterval=None, maxPollRate=None):
        super(_SensorHandler, self).__init__()
        self._sensorId = sensor.id
        self._sensorInt = SensorInterface.getSensorInterface(sensor)
        self._maxUpdateInterval = maxUpdateInterval
        self._maxPollRate = maxPollRate or timedelta(milliseconds=100)
        self._updateEvent = updateEvent
        self._cancel = False

    def stop(self):
        self._cancel = True
        self.join()

    def run(self):
        last_update = datetime.now()
        last_value = None
        while not self._cancel:
            value = self._sensorInt.getCurrentValue()
            if value != last_value and datetime.now() - last_update >= self._maxUpdateInterval:
                last_update = datetime.now()
                last_value = value
                self._updateEvent(SensorDataEventArg(self._sensorId, value))

            sleepTime = max(self._maxUpdateInterval - (datetime.now() - last_update), self._maxPollRate).total_seconds()
            time.sleep(sleepTime)

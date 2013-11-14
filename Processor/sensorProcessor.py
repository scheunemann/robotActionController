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

    def __init__(self, sensors, maxUpdateFrequency=None):
        self._handlers = []
        for sensor in sensors:
            handler = _SensorHandler(sensor)
            handler.start()
            self._handlers.append(handler)

    def __del__(self):
        pool = ThreadPool()
        pool.map(lambda h: h.stop(), self._handlers)


class _SensorHandler(Thread):

    def __init__(self, sensor, updateEvent, maxUpdateFrequency=None, maxPollRate=None):
        self._sensor = sensor
        self._sensorInt = SensorInterface.getSensorInterface(sensor)
        self._maxUpdateFrequency = maxUpdateFrequency
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
            if value != last_value and datetime.now() - last_update <= self._maxUpdateFrequency:
                last_update = datetime.now()
                self._updateEvent(SensorDataEventArg(self._sensor.id, value))

            time.sleep(max(self._maxUpdateFrequency - (datetime.now() - last_update), self._maxPollRate))

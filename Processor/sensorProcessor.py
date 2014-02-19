from threading import Thread
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
            config = [c for c in sensor.robot.sensorConfigs if c.model == sensor.model]
            if config and config[0].type == 'active':
                handler = _SensorHandler(sensor, self.newSensorData, maxUpdateInterval, timedelta(seconds=maxUpdateInterval.seconds / 10.0))
                self._handlers.append(handler)

    def start(self):
        map(lambda h: h.start(), self._handlers)

    def stop(self):
        map(lambda h: h.stop(), self._handlers)

    def __del__(self):
        self.stop()


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
        if self.isAlive():
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

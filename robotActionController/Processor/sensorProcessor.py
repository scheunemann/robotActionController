import logging
from datetime import datetime, timedelta
from collections import namedtuple
from SensorInterface.sensorInterface import SensorInterface
from gevent import sleep
import gevent
from gevent.greenlet import Greenlet
from robotActionController.Processor.event import Event


__all__ = ['SensorProcessor', ]

SensorDataEventArg = namedtuple('SensorDataEvent', ['sensor_id', 'value'])


class SensorProcessor(object):

    newSensorData = Event('Sensor update event')

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
        gevent.killall(self._handlers)

    def __del__(self):
        self.stop()


class _SensorHandler(Greenlet):

    def __init__(self, sensor, updateEvent, maxUpdateInterval=None, maxPollRate=None):
        super(_SensorHandler, self).__init__()
        self._logger = logging.getLogger(self.__class__.__name__)
        self._sensorId = sensor.id
        self._sensorIndex = sensor.extraData.get('arrayIndex', None)
        self._minValue = sensor.value_type.minValue if sensor.value_type.type == 'Continuous' else None
        self._maxValue = sensor.value_type.maxValue if sensor.value_type.type == 'Continuous' else None
        self._sensorInt = SensorInterface.getSensorInterface(sensor)
        self._maxUpdateInterval = maxUpdateInterval
        self._maxPollRate = maxPollRate or timedelta(milliseconds=100)
        self._updateEvent = updateEvent

    def run(self):
        last_update = datetime.utcnow()
        last_value = None
        while not self._cancel:
            value = self._sensorInt.getCurrentValue()
            if self._sensorIndex != None:
                if self._sensorIndex > len(value) - 1:
                    self._logger.warn("Sensor %s expected to be at index %s.  Actual data length %s.  Data: %s" % (self._sensorId, self._sensorIndex, len(value), value))
                    value = None
                else:
                    value = value[self._sensorIndex]

            if value != None:
                if self._minValue != None and value < self._minValue:
                    self._logger.debug("Sensor %s returned %s.  Value less than min value, changing to %s" % (self._sensorId, value, self._minValue))
                    value = self._minValue
                if self._maxValue != None and value > self._maxValue:
                    self._logger.debug("Sensor %s returned %s.  Value more than max value, changing to %s" % (self._sensorId, value, self._maxValue))
                    value = self._maxValue

                if value != last_value and datetime.utcnow() - last_update >= self._maxUpdateInterval:
                    last_update = datetime.utcnow()
                    last_value = value
                    self._updateEvent(SensorDataEventArg(self._sensorId, value))

            sleepTime = max(self._maxUpdateInterval - (datetime.utcnow() - last_update), self._maxPollRate).total_seconds()
            sleep(sleepTime)

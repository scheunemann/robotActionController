import logging
from datetime import datetime, timedelta
from collections import namedtuple
from SensorInterface.sensorInterface import SensorInterface
import gevent
from gevent import sleep, spawn
from gevent.greenlet import Greenlet
from robotActionController.Processor.event import Event


__all__ = ['SensorProcessor', ]

SensorDataEventArg = namedtuple('SensorDataEvent', ['sensor_id', 'sensor_name', 'value'])


class SensorProcessor(object):

    newSensorData = Event('Sensor update event')

    def __init__(self, sensors, maxUpdateInterval=None, maxPollRate=None):
        self._handlers = []
        for sensor in sensors:
            config = [c for c in sensor.robot.sensorConfigs if c.model == sensor.model]
            if config and config[0].type == 'active':
                handler = _SensorHandler(sensor, self.newSensorData, maxUpdateInterval, maxPollRate)
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
        self._sensorName = sensor.name
        self._sensorResolution = sensor.extraData.get('resolution', 3)
        self._minValue = sensor.value_type.minValue if sensor.value_type.type == 'Continuous' else None
        self._maxValue = sensor.value_type.maxValue if sensor.value_type.type == 'Continuous' else None
        self._sensorInt = SensorInterface.getSensorInterface(sensor)
        self._maxUpdateInterval = maxUpdateInterval
        self._maxPollRate = maxPollRate or timedelta(milliseconds=100)
        self._updateEvent = updateEvent

    def _run(self):
        last_update = datetime.utcnow()
        last_value = None
        sensorIndex = None
        if ':' in self._sensorName:
            sensorIndex = self._sensorName[self._sensorName.rindex(':'):]
            if sensorIndex.isdigit():
                sensorIndex = int(sensorIndex)

        while True:
            value = self._sensorInt.getCurrentValue()
            if sensorIndex != None:
                if sensorIndex > len(value) - 1:
                    self._logger.warn("Sensor %s expected to be at index %s.  Actual data length %s.  Data: %s" % (self._sensorName, 
                                                                                                                   sensorIndex, 
                                                                                                                   len(value), value))
                    value = None
                else:
                    value = value[sensorIndex]

            if value != None:
                if self._minValue != None and value < self._minValue:
                    self._logger.debug("Sensor %s returned %s.  Value less than min value, changing to %s" % (self._sensorName, value, self._minValue))
                    value = self._minValue
                if self._maxValue != None and value > self._maxValue:
                    self._logger.debug("Sensor %s returned %s.  Value more than max value, changing to %s" % (self._sensorName, value, self._maxValue))
                    value = self._maxValue

                value = round(value, self._sensorResolution)
                if value != last_value and (self._maxUpdateInterval == None or datetime.utcnow() - last_update >= self._maxUpdateInterval):
                    last_update = datetime.utcnow()
                    last_value = value
                    spawn(self._updateEvent, SensorDataEventArg(self._sensorId, self._sensorName, value))

            if self._maxUpdateInterval and self._maxPollRate:
                sleepTime = max(self._maxUpdateInterval - (datetime.utcnow() - last_update), self._maxPollRate).total_seconds()
            elif self._maxUpdateInterval:
                sleepTime = self._maxUpdateInterval - (datetime.utcnow() - last_update)
            elif self._maxPollRate:
                sleepTime = 1.0 / self._maxPollRate
            else:
                sleepTime = 0
            sleep(sleepTime)

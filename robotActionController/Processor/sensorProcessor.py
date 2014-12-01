import logging
from datetime import datetime, timedelta
from collections import namedtuple
from SensorInterface.sensorInterface import SensorInterface

from gevent import Greenlet, sleep
from gevent.queue import Queue
from threading import Thread
from robotActionController.Processor.event import Event


__all__ = ['SensorProcessor', ]

SensorDataEventArg = namedtuple('SensorDataEvent', ['sensor_id', 'sensor_name', 'value'])


class SensorProcessor(Thread):

    newSensorData = Event('Sensor update event')

    def __init__(self, sensors, maxUpdateInterval=None, maxPollRate=None):
        super(SensorProcessor, self).__init__(name=self.__class__.__name__)
        self._handlers = []
        self._updateInterval = maxUpdateInterval
        self._pollRate = maxPollRate
        self._sensors = set()
        for sensor in sensors:
            config = [c for c in sensor.robot.sensorConfigs if c.model == sensor.model]
            if config and config[0].type == 'active':
                self._sensors.add(_SensorHandler.getRunableSensor(sensor))
        self._stop = True

    def run(self):
        self._queue = Queue()
        
        for sensor in self._sensors:
            handler = _SensorHandler(sensor, self._queue.put_nowait, self._updateInterval, self._pollRate)
            self._handlers.append(handler)

        map(lambda h: h.start(), self._handlers)

        self._stop = False
        while not self._stop:
            try:
                sensorData = self._queue.get(timeout=0.5)
            except:
                continue
            if sensorData == StopIteration:
                break
            self.newSensorData(sensorData)
            
        map(lambda h: h.kill(), self._handlers)

    def stop(self):
        self._stop = True

    def __del__(self):
        self.stop()


class _SensorHandler(Greenlet):
    Sensor = namedtuple("Sensor", ['id', 'name', 'resolution', 'minValue', 'maxValue', 'interface'])

    def __init__(self, sensor, updateEvent, maxUpdateInterval=None, maxPollRate=None):
        super(_SensorHandler, self).__init__()
        self._logger = logging.getLogger(self.__class__.__name__)
        if not isinstance(sensor, _SensorHandler.Sensor):
            sensor = _SensorHandler.getRunable(sensor)
        self._sensor = sensor
        self._maxUpdateInterval = maxUpdateInterval
        self._maxPollRate = maxPollRate or timedelta(milliseconds=100)
        self._updateEvent = updateEvent
        self._stop = False

    @staticmethod
    def getRunableSensor(sensor):
        sensorId = sensor.id
        sensorName = sensor.name
        sensorResolution = sensor.extraData.get('resolution', 3)
        minValue = sensor.value_type.minValue if sensor.value_type.type == 'Continuous' else None
        maxValue = sensor.value_type.maxValue if sensor.value_type.type == 'Continuous' else None
        sensorInt = SensorInterface.getSensorInterface(sensor)
        return _SensorHandler.Sensor(
                                     id=sensorId, 
                                     name=sensorName, 
                                     resolution=sensorResolution, 
                                     minValue=minValue, 
                                     maxValue=maxValue, 
                                     interface=sensorInt)

    def _run(self):
        last_update = datetime.utcnow()
        last_value = None
        sensorIndex = None
        if ':' in self._sensor.name:
            sensorIndex = self._sensor.name[self._sensor.name.rindex(':'):]
            if sensorIndex.isdigit():
                sensorIndex = int(sensorIndex)

        while not self._stop:
            value = self._sensor.interface.getCurrentValue()
            if sensorIndex != None:
                if sensorIndex > len(value) - 1:
                    self._logger.warn("Sensor %s expected to be at index %s.  Actual data length %s.  Data: %s" % (self._sensor.name, 
                                                                                                                   sensorIndex, 
                                                                                                                   len(value), value))
                    value = None
                else:
                    value = value[sensorIndex]

            if value != None:
                if self._sensor.minValue != None and value < self._sensor.minValue:
                    self._logger.debug("Sensor %s returned %s.  Value less than min value, changing to %s" % (self._sensor.name, 
                                                                                                              value, 
                                                                                                              self._sensor.minValue))
                    value = self._sensor.minValue
                if self._sensor.maxValue != None and value > self._sensor.maxValue:
                    self._logger.debug("Sensor %s returned %s.  Value more than max value, changing to %s" % (self._sensor.name, 
                                                                                                              value, 
                                                                                                              self._sensor.maxValue))
                    value = self._sensor.maxValue

                value = round(value, self._sensor.resolution)
                if value != last_value and (self._maxUpdateInterval == None or datetime.utcnow() - last_update >= self._maxUpdateInterval):
                    last_update = datetime.utcnow()
                    last_value = value
                    self._updateEvent(SensorDataEventArg(self._sensor.id, self._sensor.name, value))

            if self._maxUpdateInterval and self._maxPollRate:
                sleepTime = max(self._maxUpdateInterval - (datetime.utcnow() - last_update), self._maxPollRate).total_seconds()
            elif self._maxUpdateInterval:
                sleepTime = self._maxUpdateInterval - (datetime.utcnow() - last_update)
            elif self._maxPollRate:
                sleepTime = 1.0 / self._maxPollRate
            else:
                sleepTime = 0
            sleep(sleepTime)

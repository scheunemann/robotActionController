import re
import os
import sys
import inspect
import logging
import random
from gevent.lock import RLock

__all__ = ['SensorInterface', ]


_modulesCache = {}


def loadModules(path=None):
    """loads all modules from the specified path or the location of this file if none"""
    """returns a dictionary of loaded modules {name: type}"""
    if path == None:
        path = __file__

    path = os.path.realpath(path)
    logger = logging.getLogger(__name__)
    if path not in _modulesCache:
        modules = []

        find = re.compile(".*\.py$", re.IGNORECASE)
        if os.path.isdir(path):
            toLoad = map(lambda f: os.path.splitext(f)[0], filter(find.search, os.listdir(path)))
        else:
            toLoad = [os.path.splitext(os.path.basename(path))[0]]
        sys.path.append(os.path.dirname(path))

        for module in toLoad:
            if module == os.path.splitext(os.path.basename(__file__))[0] or module == '__init__':
                continue
            try:
                modules.append(__import__(module, globals(), locals()))
            except Exception:
                logger.error("Unable to import module %s" % module, exc_info=True)

        ret = {}
        for module in modules:
            for name, type_ in inspect.getmembers(module, inspect.isclass):
                if hasattr(type_, "sensorType"):
                    if type_.sensorType:
                        ret[name] = type_
                        logger.debug("Registering sensor interface module %s" % name)

        _modulesCache[path] = ret

    return _modulesCache[path]


class SensorInterface(object):

    _interfaceClasses = None
    _servoInterfaces = {}
    _globalLock = RLock()
    _interfaces = {}
    disconnected = False

    """have to do it this way to get around circular referencing in the parser"""
    @staticmethod
    def _getInterfaceClasses():
        if SensorInterface._interfaceClasses == None:
            SensorInterface._interfaceClasses = {
                                 'ExternalSensor': External,
                                 'RobotSensor': Robot,
                                 'DummySensor': Dummy,
                                 }

        return SensorInterface._interfaceClasses

    @staticmethod
    def getSensorInterface(sensor):
        with SensorInterface._globalLock:
            if sensor not in SensorInterface._interfaces:
                if not SensorInterface.disconnected:
                    try:
                        servoInt = SensorInterface._getInterfaceClasses()[sensor.type]
                    except:
                        logging.getLogger(__name__).critical("No known interface for sensor type: %s", sensor.type)
                        raise ValueError("No known interface for sensor type: %s" % sensor.type)
                    else:
                        servoInt = servoInt(sensor)
                else:
                    servoInt = Dummy(sensor)

                SensorInterface._interfaces[sensor] = servoInt

            return SensorInterface._interfaces[sensor]

    def __init__(self, sensor):
        # sensor properties
        self._sensorName = sensor.name

        if sensor.onStateComparison == None or sensor.onStateValue == None:
            self._onState = None
        else:
            self._onState = sensor.onStateComparison + sensor.onStateValue

        self._logger = logging.getLogger(self.__class__.__name__)

    @property
    def sensorName(self):
        return self._sensorName

    @property
    def onState(self):
        return self._onState

    def getCurrentValue(self):
        return None


class Dummy(SensorInterface):

    sensor_values = {}

    def __init__(self, sensor):
        from multiprocessing import Value
        import ctypes
        super(Dummy, self).__init__(sensor)
        self._sensorId = sensor.id

        basePath = os.path.dirname(os.path.abspath(__file__))
        basePath = os.path.join(basePath, 'sensorData')
        if not os.path.exists(basePath):
            os.makedirs(basePath)
        fileName = 'dummySensorData_%s' % self._sensorId
        self._fileName = os.path.join(basePath, fileName)

        if sensor.id not in Dummy.sensor_values:
            Dummy.sensor_values[sensor.id] = Value(ctypes.c_float)

        value = self._readData()
        if value != None:
            self.setCurrentValue(value)

    def __del__(self):
        self.writeData(Dummy.sensor_values[self._sensorId].value)

    def setCurrentValue(self, value):
        self._writeData(value)
        self._logger.debug("%s Set value to: %s", self._sensorId, value)

    def getCurrentValue(self):
        val = self._readData()
        if val == None:
            return random.random()
        self._logger.log(1, "%s Got value: %s", self._sensorId, val)
        return val

    def _readData(self):
        import pickle
        try:
            f = open(self._fileName, 'r')
            data = pickle.load(f)
            return data['value']
        except Exception:
            pass

    def _writeData(self, value):
        import pickle
        try:
            data = {'value': value, 'name': self._sensor.name}
            f = open(self._fileName, 'w')
            pickle.dump(data, f)
        except Exception:
            pass


class Robot(SensorInterface):

    _interfaceMap = None

    def __init__(self, sensor):
        super(Robot, self).__init__(sensor)
        # servo type properties
        configs = filter(lambda c: c.model.name == sensor.model.name, sensor.robot.sensorConfigs)
        if not configs:
            raise ValueError('Config could not be found for model %s on robot %s' % (sensor.model, sensor.robot))
        else:
            config = configs[0]

        self._externalId = sensor.extraData.get('externalId', None)
        if self._externalId == None:
            self._logger.critical("%s sensor %s is missing its external Id!", (sensor.model.name, sensor.name))
            raise ValueError()

        if not Robot._interfaceMap:
            Robot._interfaceMap = dict([(c.sensorType.lower(), c) for c in loadModules(os.path.dirname(os.path.realpath(__file__))).itervalues()])

        if sensor.model.name.lower() not in Robot._interfaceMap:
            raise ValueError("Unknown sensor type: %s" % sensor.model.name)

        self._sensorInt = Robot._interfaceMap[sensor.model.name.lower()](sensor, config)

    def getCurrentValue(self):
        return self._sensorInt.getCurrentValue()


def External(SensorInterface):

    _interfaceMap = None

    def __init__(self, sensor):
        super(External, self).__init__(sensor)
        # TODO: External Sensors
        config = None
        self._externalId = sensor.extraData.get('externalId', None)
        if self._externalId == None:
            self._logger.critical("%s sensor %s is missing its external Id!", (sensor.model.name, sensor.name))

        if not External._interfaceMap:
            External._interfaceMap = dict([(c.sensorType.lower(), c) for c in loadModules(os.path.dirname(os.path.realpath(__file__))).itervalues()])

        if sensor.model.name.lower() not in External._interfaceMap:
            raise ValueError("Unknown sensor type: %s" % sensor.model.name)

        self._sensorInt = External._interfaceMap[sensor.model.name.lower()](sensor, config)

    def getCurrentValue(self):
        return self._sensorInt.getCurrentValue()


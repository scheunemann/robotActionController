import logging
from threading import RLock
from Data.Model import RobotSensor, ExternalSensor
from Robot.ServoInteface import ServoInterface

__all__ = ['SensorInterface', ]


class SensorInterface(object):

    _interfaceClasses = None
    _servoInterfaces = {}
    _globalLock = RLock()
    _interfaces = {}

    """have to do it this way to get around circular referencing in the parser"""
    @staticmethod
    def _getInterfaceClasses():
        if SensorInterface._interfaceClasses == None:
            SensorInterface._interfaceClasses = {
                                 'ExternalSensor': External,
                                 'RobotSensor': Robot,
                                 }

        return SensorInterface._interfaceClasses

    @staticmethod
    def getSensorInterface(sensor):
        with SensorInterface._globalLock:
            if sensor not in SensorInterface._interfaces:
                if 'disconnected' not in globals() or not disconnected:  # Global flag
                    try:
                        servoInt = SensorInterface._getInterfaceClasses()[sensor.type]
                    except:
                        logging.getLogger(__name__).critical("No known interface for sensor type: %s", sensor.type)
                        raise ValueError("No known interface for sensor type: %s" % sensor.type)
                    else:
                        servoInt = servoInt(sensor)
                else:
                    servoInt = Robot(sensor)

                SensorInterface._interfaces[sensor] = servoInt

            return SensorInterface._interfaces[sensor]

    def __init__(self, sensor):

        # servo type properties
        if type(sensor) == RobotSensor:
            #TODO: Stop using the servoConfig for sensor configs
            configs = filter(lambda c: c.model.name == sensor.model.name, sensor.robot.servoConfigs)
            if not configs:
                raise ValueError('Config could not be found for model %s on robot %s' % (sensor.model, sensor.robot))
            else:
                config = configs[0]
            self._port = config.port
            self._portSpeed = config.portSpeed
        elif type(sensor) == ExternalSensor:
            # TODO: External Sensors
            config = None

        # sensor properties
        self._sensor = sensor
        self._logger = logging.getLogger(self.__class__.__name__)

    def getCurrentValue(self):
        return None


class Robot(SensorInterface):

    def __init__(self, sensor):
        super(Robot, self).__init__(sensor)
        self._externalId = sensor.extraData.get('externalId', None)
        if self._externalId == None:
            self._logger.critical("%s sensor %s is missing its external Id!", (sensor.model.name, sensor.name))

        servos = [s for s in sensor.robot.servos if s.jointName == sensor.name] 
        self._sensorInt = ServoInterface.getServoInterface(servos[0])

    def getCurrentValue(self):
        return self._sensorInt.getPosition()


def External(ServoInterface):

    def __init__(self, sensor):
        super(External, self).__init__(sensor)

    def getCurrentValue(self):
        return None

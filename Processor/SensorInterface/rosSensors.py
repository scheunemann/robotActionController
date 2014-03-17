import logging
from Robot.RosInterface import rosHelper, robotFactory


__all__ = ['RosSensor', 'MessageSensor', 'SonarSensor']


class RosSensor(object):
    sensorType = 'ROS'

    def __init__(self, sensor, config, dataProcessor=None):
        super(RosSensor, self).__init__()
        self._logger = logging.getLogger(self.__class__.__name__)
        self._dataProcessor = dataProcessor
        topic = sensor.extraData.get('externalId', None)
        if topic == None:
            self._logger.critical("ROS Sensor %s is missing its topic!", sensor.name)
            raise ValueError("Sensor incorrectly configured")

        self._topic = topic
        self._ros = rosHelper.ROS()

    def getCurrentValue(self):
        rawValue = self._ros.getSingleMessage(self._topic)
        if self._dataProcessor:
            value = self._dataProcessor(rawValue)
        else:
            value = rawValue
        return value


class RobotLocationSensor(object):
    sensorType = 'RobotLocation'

    def __init__(self, sensor, config):
        super(RobotLocationSensor, self).__init__(sensor)
        self._robot = robotFactory.Factory.getRobotInterface(sensor.robot)
        self._locPart = sensor.extraData.get('externalId', None)

    def getCurrentValue(self, allVals=False):
        _, rawValue = self._robot.getLocation()

        pos = [round(rawValue[0], 3), round(rawValue[1], 3), round(rawValue[2], 3)]
        if allVals:
            return pos
        elif self._locPart and self._locPart.lower() == 'x':
            return pos[0]
        elif self._locPart and self._locPart.lower() == 'y':
            return pos[1]
        elif self._locPart and self._locPart.lower() == 'theta':
            return pos[2]
        else:
            return None


class MessageSensor(RosSensor):
    sensorType = 'RosMessage'

    def __init__(self, sensor, config):
        super(SonarSensor, self).__init__(sensor)


class SonarSensor(RosSensor):
    sensorType = 'Sonar'

    def __init__(self, sensor, config):
        super(SonarSensor, self).__init__(sensor, self._sensorProcessor)
        index = sensor.extraData.get('index', None)
        if index == None:
            self._logger.critical("Sonar Sensor %s is missing its array index!", sensor.name)
            raise ValueError("Sensor incorrectly configured")

        self._index = int(index)

    def _sensorProcessor(self, sonarMessage):
        if sonarMessage:
            return sonarMessage.ranges[self._index]
        else:
            return None
#         data = []
#         for sonIndex in range(0, 16):
#             data[sonIndex] = sonarMessage.ranges[sonIndex]

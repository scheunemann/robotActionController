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

    def getCurrentValue(self):
        _, rawValue = self._robot.getLocation()
        if self._locPart and self._locPart.lower() == 'x':
            return rawValue[0]
        elif self._locPart and self._locPart.lower() == 'y':
            return rawValue[1]
        elif self._locPart and self._locPart.lower() == 'theta':
            return rawValue[2]
        else:
            return None


class HumanLocationSensor(object):
    sensorType = 'HumanLocation'

    def __init__(self, sensor, config):
        super(HumanLocationSensor, self).__init__(sensor)
        self._robot = robotFactory.Factory.getRobotInterface(sensor.robot)
        self._locPart = sensor.extraData.get('externalId', None)
        self._topic = '/trackedHumans'
        self._transform = rosHelper.Transform(toTopic='/map', fromTopic='/camera_frame')

    def getCurrentValue(self):
        locs = self._ros.getSingleMessage(self._topic)
        if locs == None:
            print "No message received from %s" % self._topic
            return ('', (None, None, None))

        loc = None
        for human in locs.trackedHumans:
            if human.specialFlag == 1:
                loc = human
                break
        if loc == None:
            print "No human returned from location tracker"
            return None

        # loc.header.frame_id is 'usually' /camera_frame
        (x, y, _) = self._transform.transformPoint(loc.location, toTopic='/map', fromTopic=loc.location.header.frame_id)
        if x == None or y == None:
            print "Error getting transform"
            return None

        pos = [round(x, 3), round(y, 3), 0]
        if self._locPart and self._locPart.lower() == 'x':
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

import math
from Data.Model import User
from Data.storage import StorageFactory
from Robot.RosInterface import robotFactory, rosHelper
from rosSensors import RobotLocationSensor


class HumanLocationSensor(object):
    sensorType = 'HumanLocation'

    def __init__(self, sensor, config):
        super(HumanLocationSensor, self).__init__(sensor)
        # TODO: Don't hard code this
        self._userName = sensor.extraData.get('userName', None)
        self._locPart = sensor.extraData.get('externalId', None)

    def getCurrentValue(self, allVals=False):
        user = StorageFactory.getNewSession().query(User).filter(User.name == self._userName).first()
        if user == None:
            print "User '%s' not found" % self._userName
            return None

        pos = [round(user.locX, 3), round(user.locY, 3), round(user.locTheta, 3)]
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


class TrackedHumanLocationSensor(object):
    sensorType = 'TrackedHumanLocation'

    def __init__(self, sensor, config):
        super(HumanLocationSensor, self).__init__(sensor)
        self._locPart = sensor.extraData.get('externalId', None)
        self._topic = '/trackedHumans'
        self._transform = rosHelper.Transform(toTopic='/map', fromTopic='/camera_frame')

    def getCurrentValue(self, allVals=False):
        locs = self._ros.getSingleMessage(self._topic)
        if locs == None:
            print "No message received from %s" % self._topic
            return None

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


class HumanDirectionSensor(object):
    sensorType = 'HumanDirection'

    def __init__(self, sensor, config):
        self._robot = robotFactory.Factory.getRobotInterface(sensor.robot)
        self._rl = RobotLocationSensor(sensor)
        self._hl = HumanLocationSensor(sensor)
        self._locPart = sensor.extraData.get('externalId', None)

    def getCurrentValue(self, allVals=False):
        hl = self._hl.getCurrentValue(True)
        rl = self._rl.getCurrentValue(True)

        if hl and rl:
            x = hl[0] - rl[0]
            y = hl[1] - rl[1]

            if allVals:
                return (math.degrees(math.atan2(y, x)) + rl[2], math.sqrt(pow(x, 2), pow(y, 2)))
            elif self._locPart == 'angle':
                return math.degrees(math.atan2(y, x)) + rl[2]
            elif self._locPart == 'distance':
                return math.sqrt(pow(x, 2), pow(y, 2))
            else:
                return None

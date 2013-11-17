import os
import sys
import math
from xml.etree import ElementTree as et

from Data.Model import Robot, RobotModel, Servo, ServoGroup, ServoModel, \
    ServoConfig, Pose, JointPosition, SensorTrigger, ButtonTrigger, ButtonHotKey


class RobotImporter(object):

    _types = {}
    _models = {}
    _configs = {
                # SSC32 and MINISSC limits are inconsistent between the config files and the old java interface
                'SSC32': {
                            'MAX_POS': 5000,
                            'MIN_POS': 500,
                            'MAX_SPEED': 10000,
                            'MIN_SPEED': 5,
                            'POSEABLE': False,
                            'SCALE_SPEED': 100.0 / 5000.0,
                            'SCALE_POS': 360.0 / 5000.0,
                            },
                'MINISSC': {
                            'MAX_POS': 254,
                            'MIN_POS': 0,
                            'MAX_SPEED': None,  # Unsupported
                            'MIN_SPEED': None,  # Unsupported
                            'POSEABLE': False,
                            'SCALE_SPEED': None,
                            'SCALE_POS': 360.0 / 254.0,
                            },
                'HERKULEX': {
                            'MAX_POS': 1023,
                            'MIN_POS': 0,
                            'MAX_SPEED': 2048,
                            'MIN_SPEED': 10,
                            'POSEABLE': True,
                            'SCALE_SPEED': 100.0 / 1023.0,
                            'SCALE_POS': 360.0 / 1023.0,
                            },
                'DUMMY': {
                            'MAX_POS': 360,
                            'MIN_POS': 0,
                            'MAX_SPEED': 300,
                            'MIN_SPEED': 1,
                            'POSEABLE': False,
                            'SCALE_SPEED': 1,
                            'SCALE_POS': 1,
                          },
                'ROS': {
                        'MAX_POS': math.pi,
                        'MIN_POS': math.pi * -1,
                        'MAX_SPEED': 100,
                        'MIN_SPEED': 1,
                        'POSEABLE': False,
                        'SCALE_SPEED': 1,
                        'SCALE_POS': math.pi / 180,
                        }
                }

    def __init__(self):
        pass

    def getRobot(self, robotConfig):
        if os.path.exists(robotConfig) and os.path.isfile(robotConfig):
            config = et.parse(robotConfig).getroot()
        else:
            raise Exception('Cannot locate robot config (path: %s)' % (robotConfig))

        r = Robot(name=config.get('name'), version=config.get('version'))
        r.model = self._getModel(config.get('type'))
        r.servoGroups = self._getServoGroups(config)
        r.servos = self._getServos(config, r.servoGroups)
        r.servoConfigs = self._getServoConfigs(config)

        return r

    def _getModel(self, modelName):
        if modelName == None:
            return None

        if modelName not in RobotImporter._models:
            RobotImporter._models[modelName] = RobotModel(modelName)

        return self._models[modelName]

    def _getServos(self, node, servoGroups):
        servos = []
        for servo in self._get("SERVOLIST/SERVO", node):
            s = Servo()
            s.jointName = self._getText("NAME", servo)
            s.model = self._getServoModel(servo.get('type', None))
            s.minPosition = self._realToScalePos(self._getText("LIMITS[@type='pos']/MIN", servo), s.model.positionOffset, s.model.positionScale)
            s.maxPosition = self._realToScalePos(self._getText("LIMITS[@type='pos']/MAX", servo), s.model.positionOffset, s.model.positionScale)
            s.defaultPosition = self._realToScalePos(self._getText("DEFAULT/POS", servo), s.model.positionOffset, s.model.positionScale)
            s.minSpeed = self._realToScaleSpeed(self._getText("LIMITS[@type='speed']/MIN", servo), s.model.speedScale)
            s.maxSpeed = self._realToScaleSpeed(self._getText("LIMITS[@type='speed']/MAX", servo), s.model.speedScale)
            s.extraData = {'externalId': int(servo.get('id', -1))}
            if s.minSpeed > s.maxSpeed:
                temp = s.minSpeed
                s.minSpeed = s.maxSpeed
                s.maxSpeed = temp

            s.defaultSpeed = self._realToScaleSpeed(self._getText("DEFAULT/SPEED", servo), s.model.speedScale)
            if s.defaultSpeed < s.minSpeed:
                s.defaultSpeed = s.minSpeed
            if s.defaultSpeed > s.maxSpeed:
                s.defaultSpeed = s.maxSpeed

            s.groups = self._getGroupsForServo(s, servoGroups)
            servos.append(s)

        return servos

    def _getGroupsForServo(self, servo, groupList):
        groups = []
        for node in self._get("SERVOLIST/SERVOGROUP"):
            for member in self._get("MEMBER", node):
                if member.text == servo.jointName:
                    for group in groupList:
                        if group.name == self._getText("NAME", node):
                            groups.append(group)
                            break
                    break

        return groups

    def _getServoGroups(self, node):
        groups = []
        for group in self._get("SERVOLIST/SERVOGROUP", node):
            s = ServoGroup(name=self._getText("NAME", group))
            groups.append(s)

        return groups

    def _realToScalePos(self, value, offset, scaleValue):
        if value == None:
            return None

        value = float(value)
        scaled = (value - offset) * scaleValue
        return round(scaled, 2)

    def _realToScaleSpeed(self, value, scaleValue):
        if value == None:
            return None

        value = float(value)
        scaled = value * scaleValue
        return round(scaled, 2)

    def _getServoModel(self, modelName):
        if modelName == None:
            return

        if modelName.lower() not in RobotImporter._types:
            config = RobotImporter._configs[modelName.upper()] if modelName.upper() in RobotImporter._configs else RobotImporter._configs['DEFAULT']
            s = ServoModel(name=modelName)
            s.minSpeed = self._realToScaleSpeed(config['MIN_SPEED'], config['SCALE_SPEED'])
            s.maxSpeed = self._realToScaleSpeed(config['MAX_SPEED'], config['SCALE_SPEED'])
            s.positionOffset = round((config['MAX_POS'] + config['MIN_POS']) / 2, 2)
            s.minPosition = self._realToScalePos(config['MIN_POS'], s.positionOffset, config['SCALE_POS'])
            s.maxPosition = self._realToScalePos(config['MAX_POS'], s.positionOffset, config['SCALE_POS'])
            s.defaultSpeed = 100
            s.defaultPosition = 0
            s.poseable = config['POSEABLE']
            s.positionScale = config['SCALE_POS']
            s.speedScale = config['SCALE_SPEED']
            RobotImporter._types[modelName.lower()] = s

        return RobotImporter._types[modelName.lower()]

    def _getServoConfigs(self, node):
        configs = []
        for name in self._configs.keys():
            config = self._getServoConfig(name, node)
            if config != None:
                configs.append(config)

        return configs

    def _getServoConfig(self, servoName, node):
        config = self._getSingle(servoName, node)
        if config == None:
            return None

        c = ServoConfig()
        c.port = self._getText("PORT", config, "")
        c.portSpeed = self._getText("SPEED", config, 115200)
        c.rotationOffset = 0
        c.model = self._getServoModel(servoName)
        return c

    def _getText(self, xpath, node, default=None):
        val = self._getSingle(xpath, node, None)
        if val != None:
            return val.text

        return default

    def _getSingle(self, xpath, node, default=None):
        val = self._get(xpath, node, default)
        if val != None and len(val) != 0:
            return val[0]

        return default

    def _get(self, xpath, node, default=None):
        try:
            nodes = node.findall(xpath)
        except Exception as e:
            print >> sys.stderr, e
            return default

        if len(nodes) == 0 and default != None:
            return default

        return nodes


class ActionImporter(object):

    def __init__(self):
        pass

    def getPose(self, poseFile):
        """
            r_down
            JOINT_NAME, position, speed
            HEAD_ROT,515,100
            HEAD_VERT,436,100
            HEAD_TLT,545,80
            ARM_L_1,554,140
            ARM_L_2,733,140
            ARM_L_3,683,140
            ARM_L_4,693,140
            ARM_R_1,634,140
            ARM_R_2,426,140
            ARM_R_3,149,140
            ARM_R_4,168,140
            EYES_LR,600,330
            EYES_UD,450,330
            MOUTH_OPEN,520,330
            MOUTH_SMILE,740,330
            EYELIDS,614,330
        """

        if os.path.exists(poseFile) and os.path.isfile(poseFile):
            poseLines = open(poseFile).readlines()

        else:
            raise Exception('Cannot locate pose file (path: %s)' % (poseFile))

        name = poseLines[0].strip()
        pose = Pose(name=name)

        for line in poseLines[1:]:
            (jointName, pos, spd) = line.strip().split(',')
            speed = int(spd.strip())
            position = float(pos.strip())

            jp = JointPosition(jointName=jointName)
            jp.position = position
            jp.speed = speed
            pose.jointPositions.append(jp)

        return pose


class TriggerImporter(object):

    def __init__(self):
        pass

    def getTriggers(self, triggerFile, actions):
        """
            Title:actionName,hotkey/sensor
            Happy:Happy,8
            tickle,5
            Drum Ready,-
            L_arm_up,lefthand_top
            cheecks,cheeks
            belly,3
            head_left,right_arm
            LarmUP,0
            Hide,1
            Wave
            Res
            Sad,6
            hurts,+
            nod,leftfoot
            tickR,rightfoot
            Blink,2
            Secret,9
            RarmUP,.
            head_right,left_arm
        """

        if os.path.exists(triggerFile) and os.path.isfile(triggerFile):
            triggerLines = open(triggerFile).readlines()
        else:
            raise Exception('Cannot locate trigger file (path: %s)' % (triggerFile))

        triggers = []
        for line in triggerLines:
            vals = line.split(',')
            actionName = vals[0].strip()
            if actionName.count(':'):
                (title, actionName) = actionName.split(',')
            else:
                title = actionName

            try:
                action = filter(lambda x: x.name == actionName, actions)[0]
            except:
                print >> sys.stderr, "Action %s not found, skipping" % actionName
                continue

            if len(vals) == 1:
                t = ButtonTrigger(name=title)
                t.action = action
                triggers.append(t)
            elif len(vals) == 2:
                key = vals[1].strip()
                if len(key) > 1:
                    t = SensorTrigger(name=title)
                    t.sensorName = key
                    t.sensorValue = 'eval::on'
                    t.action = action
                    triggers.append(t)
                else:
                    t = ButtonTrigger(name=title)
                    t.action = action
                    hk = ButtonHotKey()
                    hk.keyName = key
                    t.hotKeys.append(hk)
                    triggers.append(t)
            else:
                print >> sys.stderr, "Unknown trigger line?? %s" % line
                continue

        return triggers

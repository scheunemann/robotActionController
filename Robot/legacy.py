import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../')))
from xml.etree import ElementTree as et

from Data.Model import Robot, RobotModel, Servo, ServoGroup, ServoModel, \
    ServoConfig, PoseAction, JointPosition, SensorTrigger, ButtonTrigger, ButtonHotkey, SequenceAction, SoundAction


def _realToScalePos(value, offset, scaleValue):
    if value == None:
        return None
    scaled = (float(value) - offset) * scaleValue
    return round(scaled, 2)


def _legacyUnscaleValue(minPos, maxPos, value):
    minPos = int(minPos)
    maxPos = int(maxPos)
    value = int(value)
    if minPos <= maxPos:
        return int(round(minPos + (maxPos - minPos) * value / 1000))
    else:
        return int(round(minPos - (minPos - maxPos) * value / 1000))


def _realToScaleSpeed(value, scaleValue):
    if value == None:
        return None

    value = float(value)
    scaled = value * (scaleValue or 1)
    return round(scaled, 2)


def _scaleToRealPos(offset, scale, value):
    real = (value / float(scale)) + offset
    return round(real, 2)


class KasparImporter(object):

    _types = {}
    _models = {}
    _configs = {
                # SSC32 and MINISSC limits are inconsistent between the config files and the old java interface
                'SSC32': {
                            'MAX_POS': 10000,
                            'MIN_POS': 500,
                            'MAX_SPEED': 5000,
                            'MIN_SPEED': 5,
                            'POSEABLE': False,
                            'SCALE_SPEED': 100.0 / 1000.0,
                            'SCALE_POS': 360.0 / 10000.0,
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
                'DUMMY': {
                            'MAX_POS': 360,
                            'MIN_POS': 0,
                            'MAX_SPEED': 300,
                            'MIN_SPEED': 1,
                            'POSEABLE': False,
                            'SCALE_SPEED': 1,
                            'SCALE_POS': 1,
                          },
                'AX12': {
                            'MAX_POS': 1023,
                            'MIN_POS': 0,
                            'MAX_SPEED': 1023,
                            'MIN_SPEED': 1,
                            'POSEABLE': True,
                            'SCALE_SPEED': 1,
                            'SCALE_POS': 360.0 / 1024.0,
                            },
                'DEFAULT': {
                            'MAX_POS': 1023,
                            'MIN_POS': 0,
                            'MAX_SPEED': 2048,
                            'MIN_SPEED': 10,
                            'POSEABLE': True,
                            'SCALE_SPEED': 100.0 / 1023.0,
                            'SCALE_POS': 360.0 / 1023.0,
                            }
                }

    # Calibration offsets (scaled values)
    # From Calibration.pose
    _offsets = {
        'Kaspar_1c': {
                    'ARM_L_1': 420,
                    'ARM_L_2': 200,
                    'ARM_L_3': 640,
                    'ARM_L_4': 37,
                    'ARM_R_1': 580,
                    'ARM_R_2': 790,
                    'ARM_R_3': 450,
                    'ARM_R_4': 840,
                    'HEAD_ROT': 570,
                    'HEAD_TLT': 720,
                    'HEAD_VERT': 430,
                    'EYES_LR': 350,
                    'EYES_UD': 210,
                    'EYELIDS': 800,
                    'MOUTH_OPEN': 520,
                    'MOUTH_SMILE': 520,
                    'TORSO': 370,
                    }
        }

    _nameMap = {
                    'HEAD_ROT': 'HEAD_YAW',
                    'HEAD_PITCH': 'HEAD_PITCH',
                    'HEAD_TLT': 'HEAD_ROLL',
                    'EYES_LR': 'EYES_YAW',
                    'EYES_UD': 'EYES_PITCH',
                    'EYELIDS': 'EYELIDS',
                    'MOUTH_OPEN': 'MOUTH_OPEN',
                    'MOUTH_SMILE': 'MOUTH_SMILE',
                    'ARM_L_1': 'L_SHOULDER_ROLL_UPPER',
                    'ARM_L_2': 'L_SHOULDER_PITCH',
                    'ARM_L_3': 'L_SHOULDER_ROLL_LOWER',
                    'ARM_L_4': 'L_ELBOW',
                    'ARM_R_1': 'R_SHOULDER_ROLL_UPPER',
                    'ARM_R_2': 'R_SHOULDER_PITCH',
                    'ARM_R_3': 'R_SHOULDER_ROLL_LOWER',
                    'ARM_R_4': 'R_ELBOW',
                    'TORSO': 'TORSO',
                    }

    def __init__(self, configDir):
        robotConfig = os.path.join(configDir, 'robot.xml')
        if os.path.exists(robotConfig) and os.path.isfile(robotConfig):
            self._config = et.parse(robotConfig).getroot()
        else:
            raise Exception('Cannot locate robot.xml in path: %s' % (configDir))

        self._version = self._config.get('version')

    def getRobot(self):
        r = Robot(name=self._getText('NAME', None, 'KASPAR'), version=self._version)
        r.servoGroups = self._getServoGroups()
        r.servos = self._getServos(r.servoGroups, KasparImporter._offsets.get(r.name, {}))
        r.servoConfigs = self._getServoConfigs()
        r.model = self._getModel('KASPAR')

        return r

    def _getModel(self, modelName):
        if modelName == None:
            return None

        if modelName not in KasparImporter._models:
            KasparImporter._models[modelName] = RobotModel(modelName)

        return self._models[modelName]

    def _getServos(self, servoGroups, offsets):
        servos = []
        for servo in self._get("SERVOLIST/SERVO"):
            s = Servo()
            legacyName = self._getText("NAME", servo)
            if legacyName in KasparImporter._nameMap:
                jointName = KasparImporter._nameMap[legacyName]
            else:
                jointName = legacyName
            s.jointName = jointName
            s.legacyName = legacyName
            s.model = self._getServoModel(servo.get('type', None))
            s.defaultPosition = 0

            p1 = int(self._getText("LIMITS[@type='pos']/MIN", servo))
            p2 = int(self._getText("LIMITS[@type='pos']/MAX", servo))
            s.legacyInverted = p1 > p2
            minPos = min(p1, p2)
            maxPos = max(p1, p2)
            if offsets and legacyName in offsets:
                # calibrated offsets
                offset = _legacyUnscaleValue(minPos, maxPos, offsets.get(legacyName))
            else:
                offset = int(self._getText("DEFAULT/POS", servo) or 0)
                defaults = self._get("DEFAULT", servo)
                if defaults and defaults[0].get("type") == 'scaled':
                    offset = _legacyUnscaleValue(minPos, maxPos, offset)

            s.positionOffset = offset
            s.minPosition = _realToScalePos(minPos, s.positionOffset, s.model.positionScale)
            s.maxPosition = _realToScalePos(maxPos, s.positionOffset, s.model.positionScale)
            s.minSpeed = _realToScaleSpeed(self._getText("LIMITS[@type='speed']/MIN", servo), s.model.speedScale)
            s.maxSpeed = _realToScaleSpeed(self._getText("LIMITS[@type='speed']/MAX", servo), s.model.speedScale)
            s.extraData = {'externalId': int(servo.get('id', -1))}
            if s.minPosition > s.maxPosition:
                temp = s.minPosition
                s.minPosition = s.maxPosition
                s.maxPosition = temp

            if s.minSpeed > s.maxSpeed:
                temp = s.minSpeed
                s.minSpeed = s.maxSpeed
                s.maxSpeed = temp

            s.defaultSpeed = _realToScaleSpeed(self._getText("DEFAULT/SPEED", servo), s.model.speedScale)
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

    def _getServoGroups(self):
        groups = []
        for group in self._get("SERVOLIST/SERVOGROUP"):
            s = ServoGroup(name=self._getText("NAME", group))
            groups.append(s)

        return groups

    def _getServoModel(self, modelName):
        if modelName == None:
            return

        if modelName.lower() not in KasparImporter._types:
            config = KasparImporter._configs[modelName.upper()] if modelName.upper() in KasparImporter._configs else KasparImporter._configs['DEFAULT']
            s = ServoModel(name=modelName)
            s.minSpeed = _realToScaleSpeed(config['MIN_SPEED'], config['SCALE_SPEED'])
            s.maxSpeed = _realToScaleSpeed(config['MAX_SPEED'], config['SCALE_SPEED'])
            s.positionOffset = round((config['MAX_POS'] + config['MIN_POS']) / 2, 2)
            s.minPosition = _realToScalePos(config['MIN_POS'], s.positionOffset, config['SCALE_POS'])
            s.maxPosition = _realToScalePos(config['MAX_POS'], s.positionOffset, config['SCALE_POS'])
            s.defaultSpeed = 100
            s.defaultPosition = 0
            s.poseable = config['POSEABLE']
            s.positionScale = config['SCALE_POS']
            s.speedScale = config['SCALE_SPEED']
            KasparImporter._types[modelName.lower()] = s

        return KasparImporter._types[modelName.lower()]

    def _getServoConfigs(self):
        configs = []
        names = ['AX12', 'SSC32', 'MINISSC', 'HERKULEX', 'DUMMY']
        for name in names:
            config = self._getServoConfig(name)
            if config != None:
                configs.append(config)

        return configs

    def _getServoConfig(self, servoName):
        config = self._getSingle("%s" % servoName)
        if config == None:
            return None

        c = ServoConfig()
        c.port = self._getText("PORT", config, "")
        c.portSpeed = self._getText("SPEED", config, 115200)
        c.rotationOffset = 0
        c.model = self._getServoModel(servoName)
        return c

    def _getText(self, xpath, node=None, default=None):
        val = self._getSingle(xpath, node, None)
        if val != None:
            return val.text

        return default

    def _getSingle(self, xpath, node=None, default=None):
        val = self._get(xpath, node, default)
        if val != None and len(val) != 0:
            return val[0]

        return default

    def _get(self, xpath, node=None, default=None):
        if node == None:
            node = self._config

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
        self.defaultPosition = 300.0 / 1024.0
        self.defaultSpeed = 1 / 1024.0

    def getSequence(self, legacyData, actions, soundDir=None):
        if type(legacyData) == str:
            lines = legacyData.split('\n')
        else:
            lines = legacyData

        lines = [l.strip() for l in lines]
        name = lines.pop(0)
        sequence = SequenceAction(name=name)

        expectedActions = int(lines.pop(0))
        if expectedActions == 1 and not lines[-1].endswith('.wav'):
            print >> sys.stderr, "Skipping sequence with only one action: %s" % name
            return None

        for i in range(0, len(lines)):
            line = lines[i].split(',')
            if len(line) == 3:
                (dispName, actionName, postDelay) = line
                postDelay = int(postDelay)
                possibleActions = [a for a in actions if a.name == actionName or a.name == dispName]
                if len(possibleActions) == 0:
                    print >> sys.stderr, "Action with name %s not found, skipping to next item in sequence" % actionName
                    continue
                else:
                    action = possibleActions[0]
            elif len(line) == 1 and soundDir != None:
                soundFile = line[0]
                fullPath = os.path.join(soundDir, soundFile)
                if not os.path.isdir(soundDir) or not os.path.isfile(fullPath):
                    print >> sys.stderr, "Could not locate sound file %s, skipping to next item in sequence" % soundFile
                    continue

                action = SoundAction(name=os.path.splitext(soundFile)[0])
                with open(fullPath, 'rb') as f:
                    action.data = f.read()

            sequence.actions.append(action)
        return sequence

    def getPose(self, legacyData, legacyRobot=None):
        if type(legacyData) == str:
            lines = legacyData.split('\n')
        else:
            lines = legacyData

        name = lines[0].strip()
        pose = PoseAction(name=name)

        expectedJoints = int(lines[1])
        for i in range(2, expectedJoints + 2):
            (jointName, pos, spd, _) = lines[i].strip().split(',')
            speed = int(spd)
            position = int(pos)

            if legacyRobot:
                try:
                    servos = filter(lambda x: x.jointName == jointName, legacyRobot.servos) or filter(lambda x: x.legacyName == jointName, legacyRobot.servos)
                    if not servos:
                        raise ValueError('Could not located servo for joint %s' % jointName)

                    servo = servos[0]
                    jointName = servo.jointName
                    offset = servo.positionOffset if servo.positionOffset != None else servo.model.positionOffset
                    minPos = _scaleToRealPos(offset, servo.model.positionScale, servo.minPosition)
                    maxPos = _scaleToRealPos(offset, servo.model.positionScale, servo.maxPosition)
#                     if servo.legacyInverted:
#                         positionReal = _legacyUnscaleValue(maxPos, minPos, position)
#                     else:
                    positionReal = _legacyUnscaleValue(minPos, maxPos, position)
                    position = _realToScalePos(positionReal, offset, servo.model.positionScale)
                    if servo.model.speedScale != None:
                        speed = _realToScaleSpeed(speed, servo.model.speedScale)
                    else:
                        speed = None
                    if name == 'Calibration':
                        print "%s: %s @ %s" % (jointName, positionReal, speed)
                except Exception:
                    print >> sys.stderr, "Servo with name %s not attached to robot %s, using default conversion" % (jointName, legacyRobot.name)
                    position = position * self.defaultPosition
                    speed = speed * self.defaultSpeed
            else:
                position = position * self.defaultPosition
                speed = speed * self.defaultSpeed

            jp = JointPosition(jointName=jointName)
            jp.position = position
            jp.speed = speed
            pose.jointPositions.append(jp)

        return pose


class TriggerImporter(object):

    def __init__(self):
        pass

    def getTriggers(self, legacyData, actions, skipNames=[]):
        if type(legacyData) == str:
            lines = legacyData.split('\n')
        else:
            lines = legacyData

        triggers = {}
        for line in lines:
            vals = line.split(',')
            if len(vals) >= 1:
                name = vals[0].strip()
                if name in skipNames:
                    continue
                try:
                    action = filter(lambda x: x.name == name, actions)[0]
                except:
                    print "PoseAction %s not found, skipping" % name
                    continue
                keys = [k.strip() for k in vals[1:]]
                t = ButtonTrigger(name=name)
                t.action = action
                for key in keys:
                    hk = ButtonHotkey()
                    hk.keyString = key.lower()
                    t.hotKeys.append(hk)
                triggers[name] = t

            else:
                print >> sys.stderr, "Unknown key sequence?? %s" % line
                continue

        return triggers.values()


def loadDirectory(actions, triggers, robots, subDir, loadActions=True, loadTriggers=True, loadRobots=True):

    if loadRobots or loadActions:
        k = KasparImporter(subDir)
        r = k.getRobot()
    if loadRobots:
        robots.append(r)

    if loadActions:
        a = ActionImporter()
        searchDir = os.path.join(subDir, 'pos')
        if os.path.exists(searchDir):
            files = [os.path.join(searchDir, o) for o in os.listdir(searchDir) if os.path.isfile(os.path.join(searchDir, o))]
            for fileName in filter(lambda f: f.endswith(".pose"), files):
                f = open(fileName)
                lines = f.readlines()
                pose = a.getPose(lines, r)
                if pose != None and pose.name not in actions:
                    actions[pose.name] = pose
                else:
                    print "Skipping pose %s, another by the same name already exists" % pose.name

        searchDir = os.path.join(subDir, 'seq')
        if os.path.exists(searchDir):
            files = [os.path.join(searchDir, o) for o in os.listdir(searchDir) if os.path.isfile(os.path.join(searchDir, o))]
            for fileName in filter(lambda f: f.endswith(".seq"), files):
                f = open(fileName)
                lines = f.readlines()
                sequence = a.getSequence(lines, actions.values(), os.path.join(subDir, 'sounds'))
                if sequence != None and sequence.name not in actions:
                    actions[sequence.name] = sequence
                else:
                    print "Skipping sequence %s, another by the same name already exists" % pose.name

    if loadTriggers:
        t = TriggerImporter()
        searchDir = os.path.join(subDir, 'keyMaps')
        if os.path.exists(searchDir):
            files = [os.path.join(searchDir, o) for o in os.listdir(searchDir) if os.path.isfile(os.path.join(searchDir, o))]
            for fileName in filter(lambda f: f.endswith(".skm"), files):
                f = open(fileName)
                lines = f.readlines()
                for trigger in t.getTriggers(lines, actions.values(), triggers.keys()):
                    if trigger.name in triggers:
                        print "Trigger named %s already imported, skipping" % trigger.name
                    else:
                        triggers[trigger.name] = trigger

    return (robots, actions.values(), triggers.values())


def loadAllConfigs(rootDir, loadActions=True, loadTriggers=True, loadRobots=True):
    dirs = [os.path.join(rootDir, o) for o in os.listdir(rootDir) if os.path.isdir(os.path.join(rootDir, o))]

    loadedActions = {}
    loadedTriggers = {}
    loadedRobots = []

    for subDir in dirs:
        loadDirectory(loadedActions, loadedTriggers, loadedRobots, subDir, loadActions, loadTriggers)

    return (loadedRobots, loadedActions.values(), loadedTriggers.values())

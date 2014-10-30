import os
from xml.etree import ElementTree as et
import logging

from robotActionController.Data.Model import Robot, RobotModel, Servo, ServoGroup, ServoModel, \
    ServoConfig, RobotSensor, SensorModel, SensorConfig, DiscreteValueType, ContinuousValueType, PoseAction, SequenceAction, SequenceOrder, JointPosition, SensorTrigger, ButtonTrigger, ButtonHotkey
from robotActionController.Data.Model.sensor import DiscreteSensorValue

logger = logging.getLogger('importer')


def loadAllDirectories(rootDir, loadActions=True, loadTriggers=True, loadRobots=True):
    loadedActions = {}
    loadedTriggers = {}
    loadedRobots = []

    dirs = [os.path.join(rootDir, o) for o in os.listdir(rootDir) if os.path.isdir(os.path.join(rootDir, o))]
    for subDir in dirs:
        loadDirectory(loadedActions, loadedTriggers, loadedRobots, subDir, 'robot.xml', loadActions, loadTriggers, loadRobots)

    return (loadedRobots, loadedActions.values(), loadedTriggers.values())


def loadDirectory(actions, triggers, robots, subDir, robotConfig, loadActions=True, loadTriggers=True, loadRobots=True):

    if loadActions:
        a = ActionImporter()
        searchDir = os.path.join(subDir, 'pos')
        if os.path.exists(searchDir):
            files = [os.path.join(searchDir, o) for o in os.listdir(searchDir) if os.path.isfile(os.path.join(searchDir, o))]
            for fileName in files:
                f = open(fileName)
                lines = f.readlines()
                pose = a.getPose(lines)
                if pose.name not in actions:
                    actions[pose.name] = pose
                else:
                    logger.info("Skipping pose %s, another by the same name already exists" % pose.name)

        searchDir = os.path.join(subDir, 'seq')
        recheck = []
        if os.path.exists(searchDir):
            files = [os.path.join(searchDir, o) for o in os.listdir(searchDir) if os.path.isfile(os.path.join(searchDir, o))]
            for fileName in files:
                f = open(fileName)
                lines = f.readlines()
                seq = a.getSequence(lines, actions)
                if seq == None:
                    recheck.append(lines)
                    continue
                if seq.name not in actions:
                    actions[seq.name] = seq
                else:
                    logger.info("Skipping sequence %s, another by the same name already exists" % seq.name)
        progress = True
        while recheck and progress:
            progress = False
            for lines in recheck:
                seq = a.getSequence(lines, actions)
                if seq == None:
                    continue
                else:
                    recheck.remove(lines)
                    progress = True
                if seq.name not in actions:
                    actions[seq.name] = seq
                else:
                    logger.info("Skipping sequence %s, another by the same name already exists" % seq.name)
        if recheck:
            logger.error("Unable to import all sequences, missing reference actions", exc_info=True)

    if loadTriggers:
        t = TriggerImporter()
        searchDir = os.path.join(subDir, 'keyMaps')
        if os.path.exists(searchDir):
            files = [os.path.join(searchDir, o) for o in os.listdir(searchDir) if os.path.isfile(os.path.join(searchDir, o))]
            for fileName in files:
                f = open(fileName)
                lines = f.readlines()
                for trigger in t.getTriggers(lines, actions.values(), triggers.keys()):
                    if trigger.name in triggers:
                        logger.info("Trigger named %s already imported, skipping" % trigger.name)
                        continue
                    else:
                        triggers[trigger.name] = trigger
    if loadRobots:
        if type(robotConfig) == 'str':
            robotConfig = os.path.join(subDir, 'robot.xml')
            if not os.path.isfile(robotConfig):
                return None
            robotConfig = et.parse(robotConfig).getroot()
        elif type(robotConfig) != et.Element:
            return None

        if robotConfig.tag != 'ROBOT':
            return None

        r = RobotImporter().getRobot(robotConfig, actions)
        robots.append(r)

    return (robots, actions.values(), triggers.values())


class RobotImporter(object):

    _valueTypes = {
                   'continuous': ContinuousValueType,
                   'discrete': DiscreteValueType,
                   }
    _sensorModels = {}
    _types = {}
    _models = {}
    _configs = {}

    def __init__(self):
        self._logger = logging.getLogger(self.__class__.__name__)

    def getRobot(self, robotConfig, poseDict):
        if type(robotConfig) == 'str':
            if not os.path.exists(robotConfig) or not os.path.isfile(robotConfig):
                raise Exception('Cannot locate robot config (path: %s)' % (robotConfig))
            config = et.parse(robotConfig).getroot()
        elif type(robotConfig) != et.Element:
            raise Exception('Invalid config type: %s' % type(robotConfig))
        else:
            config = robotConfig

        r = Robot(name=config.get('name'), version=config.get('version'))
        r.model = self._getModel(config.get('type'), config.get('extraData'))
        r.servoGroups = self._getServoGroups(config)
        r.servoConfigs = self._getServoConfigs(config)
        r.servos = self._getServos(config, r.servoGroups)
        r.sensorGroups = self._getSensorGroups(config)
        configs = []
        configs.extend(self._getRobotSensorConfigs(config))
        configs.extend(self._getExternalSensorConfigs(config))
        r.sensorConfigs = configs
        sensors = []
        sensors.extend(self._getRobotSensors(config, r.sensorGroups))
        sensors.extend(self._getExternalSensors(config, r.sensorGroups))
        # sensors.extend(self._getServoSensors(config, r.sensorGroups))
        r.sensors = sensors
        defaultAction = config.get('defaultAction', None)
        if defaultAction:
            if defaultAction in poseDict:
                r.defaultAction = poseDict[defaultAction]
            else:
                self._logger.info("Warning: Could not locate action named %s.  Robot will have no default" % defaultAction)

        return r

    def _getModel(self, modelName, extraData):
        if modelName == None:
            return None

        if modelName not in RobotImporter._models:
            robot = RobotModel(modelName)
            if extraData:
                ed = {}
                for kvp in extraData.split(','):
                    [k, v] = kvp.split(':', 2)
                    ed[k] = v
                robot.extraData = ed
            RobotImporter._models[modelName] = robot

        return self._models[modelName]

    def _getValueType(self, typeName):
        if typeName in RobotImporter._valueTypes:
            return RobotImporter._valueTypes[typeName]()
        else:
            return None

    def _getSensorModel(self, modelName):
        if modelName == None:
            return None

        if modelName not in RobotImporter._sensorModels:
            s = SensorModel(modelName)
            RobotImporter._sensorModels[modelName] = s

        return self._sensorModels[modelName]

    def _getServoSensors(self, node, sensorGroups):
        sensors = []
        # Add a robotSensor for each readable servo
        for servoConfig in [c for c in self._get("SERVOCONFIGS", node) if c.find("**/IS_UPDATED") is not None]:
            for servoType in [c for c in servoConfig if c.find('DEFAULT/IS_UPDATED') is not None and c.find('DEFAULT/IS_UPDATED').text.lower() == 'true']:
                for servo in self._get("SERVOLIST/SERVO[@type='%s']" % servoType.tag, node):
                    s = RobotSensor()
                    s.name = self._getText("NAME", servo).upper()
                    s.model = self._getSensorModel(servo.get('type', None))
                    s.value_type = self._getValueType('continuous')
                    s.value_type.minValue = self._getText("LIMITS/POS/MIN", servo, None)
                    s.value_type.maxValue = self._getText("LIMITS/POS/MAX", servo, None)
                    s.value_type.precision = 3
                    extId = servo.get('id', None)
                    if extId != None:
                        s.extraData = {'externalId': extId}
                    else:
                        s.extraData = {}
                    extra = servo.get('extraData', '')
                    for line in extra.split(','):
                        if line:
                            (key, value) = line.split(':')
                            s.extraData[key] = value
                    s.groups = self._getGroupsForSensor(s, sensorGroups, node)
                    sensors.append(s)
        return sensors

    def _getRobotSensors(self, node, sensorGroups):
        sensors = []
        for sensor in self._get("SENSORLIST/ROBOT/SENSOR", node):
            multiple = int(self._getText("ISMULTIPLE", node, 1))

            for i in range(0, multiple):
                s = RobotSensor()
                s.name = self._getText("NAME", sensor).upper()
                if multiple > 1:
                    s.name += '_' + str(i)
                s.model = self._getSensorModel(sensor.get('type', None))
                s.onStateComparison = self._getText("ONSTATE/COMPARISON", sensor, ">")
                s.onStateValue = self._getText("ONSTATE/VALUE", sensor, "0")
                s.value_type = self._getValueType(sensor.get('datatype', 'continuous'))
                if isinstance(s.value_type, ContinuousValueType):
                    s.value_type.minValue = self._getText("LIMITS/MIN", sensor)
                    s.value_type.maxValue = self._getText("LIMITS/MAX", sensor)
                    s.value_type.precision = self._getText("LIMITS/PRECISION", sensor)
                elif isinstance(s.value_type, DiscreteValueType):
                    # TODO Discrete values
                    for value in self._get("VALUES/VALUE", sensor):
                        dsv = DiscreteSensorValue()
                        dsv.value = value.text
                        s.value_type.values.append(dsv)
                else:
                    # TODO Error handling
                    pass
                extId = sensor.get('id', None)
                if extId != None:
                    s.extraData = {'externalId': extId}
                else:
                    s.extraData = {}
                extra = sensor.get('extraData', '')
                for line in extra.split(','):
                    if line:
                        (key, value) = line.split(':')
                        s.extraData[key] = value
                if multiple > 1:
                    s.extraData.setDefault('arrayIndex', i)
                s.groups = self._getGroupsForSensor(s, sensorGroups, node)
                sensors.append(s)

        return sensors

    def _getExternalSensors(self, node, sensorGroups):
        sensors = []
        for sensor in self._get("SENSORLIST/EXTERNAL/SENSOR", node):
            # TODO: Properly handle external sensors
            s = RobotSensor()
            s.name = self._getText("NAME", sensor).upper()
            s.model = self._getSensorModel(sensor.get('type', None))
            s.onState = self._getText("ONSTATE", node, None)
            s.value_type = self._getValueType(sensor.get('datatype', 'continuous'))
            if isinstance(s.value_type, ContinuousValueType):
                s.value_type.minValue = self._getText("LIMITS/MIN", sensor)
                s.value_type.maxValue = self._getText("LIMITS/MAX", sensor)
                s.value_type.precision = self._getText("LIMITS/PRECISION", sensor)
            elif isinstance(s.value_type, DiscreteValueType):
                # TODO Discrete values
                for value in self._get("VALUES/VALUE", sensor):
                    dsv = DiscreteSensorValue()
                    dsv.value = value.text
                    s.value_type.values.append(dsv)
            else:
                # TODO Error handling
                pass
            extId = sensor.get('id', None)
            if extId != None:
                s.extraData = {'externalId': extId}
            else:
                s.extraData = {}
            extra = sensor.get('extraData', '')
            for line in extra.split(','):
                if line:
                    (key, value) = line.split(':')
                    s.extraData[key] = value
            s.groups = self._getGroupsForSensor(s, sensorGroups, node)
            sensors.append(s)

        return sensors

    def _getServos(self, node, servoGroups):
        servos = []
        for servo in self._get("SERVOLIST/SERVO", node):
            s = Servo()
            s.positionOffset = self._getText("CENTER", servo, None)
            s.jointName = self._getText("NAME", servo).upper()
            modelName = servo.get('type', None)
            if modelName.lower() in RobotImporter._types:
                s.model = RobotImporter._types[modelName.lower()]
            else:
                self._logger.info("Unknown servo model: %s" % modelName)
                pass
            s.minPosition = self._getText("LIMITS/POS/MIN", servo, None)
            s.maxPosition = self._getText("LIMITS/POS/MAX", servo, None)
            pos = self._getText("DEFAULT/POS", servo)
            if pos and '[' in pos and ']' in pos:
                s.defaultPosition = None
                try:
                    posList = eval(pos)
                except Exception:
                    self._logger.error("Invalid multi-position specified for servo %s: %s" % (s.jointName, pos), exc_info=True)
                    continue
                s.defaultPositions = str(posList)
            else:
                s.defaultPosition = pos
                s.defaultPositions = None
            s.minSpeed = self._getText("LIMITS/SPEED/MIN", servo, None)
            s.maxSpeed = self._getText("LIMITS/SPEED/MAX", servo, None)
            extId = servo.get('id', None)
            if extId != None:
                s.extraData = {'externalId': extId}
            else:
                s.extraData = {}
            for eData in self._get('EXTRADATA/*', servo):
                s.extraData[eData.tag] = eData.text

            s.defaultSpeed = self._getText("DEFAULT/SPEED", servo, None)
            if s.defaultSpeed != None:
                if s.defaultSpeed < (s.minSpeed or s.model.minSpeed):
                    s.defaultSpeed = (s.minSpeed or s.model.minSpeed)
                if s.defaultSpeed > (s.maxSpeed or s.model.maxSpeed):
                    s.defaultSpeed = (s.maxSpeed or s.model.maxSpeed)

            s.groups = self._getGroupsForServo(s, servoGroups, node)
            servos.append(s)

        return servos

    def _getGroupsForServo(self, servo, groupList, rootnode):
        groups = []
        for node in self._get("SERVOGROUPS/SERVOGROUP", rootnode):
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
        for group in self._get("SERVOGROUPS/SERVOGROUP", node):
            s = ServoGroup(name=self._getText("NAME", group))
            groups.append(s)

        return groups

    def _getGroupsForSensor(self, sensor, groupList, rootnode):
        groups = []
        for node in self._get("SENSORGROUPS/SENSORGROUP", rootnode):
            for member in self._get("MEMBER", node):
                if member.text == sensor.name:
                    for group in groupList:
                        if group.name == self._getText("NAME", node):
                            groups.append(group)
                            break
                    break

        return groups

    def _getSensorGroups(self, node):
        groups = []
        for group in self._get("SENSORGROUPS/SENSORGROUP", node):
            s = ServoGroup(name=self._getText("NAME", group))
            groups.append(s)

        return groups

    def _getServoModel(self, node):
        modelName = node.tag
        if modelName == None:
            return

        if modelName.lower() not in RobotImporter._types:
            s = ServoModel(name=modelName)
            s.minSpeed = self._getText('LIMITS/SPEED/MIN', node, 1)
            s.maxSpeed = self._getText('LIMITS/SPEED/MAX', node, 100)
            s.minPosition = self._getText('LIMITS/POS/MIN', node, 0)
            s.maxPosition = self._getText('LIMITS/POS/MAX', node, 359)
            s.defaultSpeed = self._getText('DEFAULT/SPEED', node, 100)
            s.defaultPosition = self._getText('DEFAULT/POS', node, 0)
            s.poseable = self._getText('DEFAULT/MANUAL_POSITIONING', node, 'False').upper() == 'TRUE'
            s.readable = self._getText('DEFAULT/IS_UPDATED', node, 'False').upper() == 'TRUE'
            s.positionScale = self._getText('SCALING/POS', node, 1)
            s.positionOffset = self._getText('SCALING/POS_OFFSET', node, 0)
            s.speedScale = self._getText('SCALING/SPEED', node, 1)
            RobotImporter._types[modelName.lower()] = s

        return RobotImporter._types[modelName.lower()]

    def _getRobotSensorConfigs(self, node):
        configs = []
        for configGroup in self._get('SENSORCONFIGS/ROBOT', node):
            for configNode in configGroup.getchildren():
                config = self._getSensorConfig(configNode)
                if config != None:
                    configs.append(config)

        return configs

    def _getExternalSensorConfigs(self, node):
        configs = []
        for configGroup in self._get('SENSORCONFIGS/EXTERNAL', node):
            for configNode in configGroup.getchildren():
                config = self._getSensorConfig(configNode)
                if config != None:
                    configs.append(config)

        return configs

    def _getSensorConfig(self, config):
        c = SensorConfig()
        c.model = self._getSensorModel(config.tag)
        c.type = config.get('type', 'active')
        c.datatype = config.get('datatype', 'continuous')
        c.port = self._getText("PORT", config, None)
        c.portSpeed = self._getText("SPEED", config, None)

        c.extraData = {}
        for eData in self._get('EXTRADATA/*', config):
            c.extraData[eData.tag] = eData.text

        return c

    def _getServoConfigs(self, node):
        configs = []
        for configGroup in self._get('SERVOCONFIGS', node):
            for configNode in configGroup.getchildren():
                config = self._getServoConfig(configNode)
                if config != None:
                    configs.append(config)

        return configs

    def _getServoConfig(self, config):
        c = ServoConfig()
        c.port = self._getText("PORT", config, "")
        c.portSpeed = self._getText("SPEED", config, None)
        c.model = self._getServoModel(config)
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
        except Exception:
            self._logger.error("Error parsing node", exc_info=True)
            return default

        if len(nodes) == 0 and default != None:
            return default

        return nodes


class ActionImporter(object):

    def __init__(self):
        self._logger = logging.getLogger(self.__class__.__name__)

    def getSequence(self, sequenceLines, actions):
        """
            Blink
            ActionName
            ActionName, forcedLength
            Eyes Shut
            Eyes Open
        """
        name = sequenceLines[0].strip()
        seq = SequenceAction(name=name)

        for i in range(1, len(sequenceLines)):
            parts = sequenceLines[i].strip().split(',', 1)
            name = parts[0].strip()
            length = parts[1].strip() if len(parts) > 1 else None
            if name in actions:
                seq.actions.append(SequenceOrder(actions[name], forcedLength=length))
            else:
                self._logger.error("Unable to find action named %s for sequence %s, skipping step" % (sequenceLines[i], name))
                return None

        return seq

    def getPose(self, poseLines):
        """
            r_down
            JOINT_NAME, position, speed
            JOINT_NAME, [position0, position1, ], speed
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

        name = poseLines[0].strip()
        pose = PoseAction(name=name)

        for line in poseLines[1:]:
            if not line.strip():
                continue
            idx1 = line.find(',')
            idx2 = line.rfind(',')
            jointName = line[0:idx1].strip()
            pos = line[idx1 + 1:idx2].strip()
            spd = line[idx2 + 1:].strip()

            speed = int(spd.strip())
            if '[' in pos and ']' in pos:
                positions = [float(p.strip()) for p in pos[1:-1].split(',') if p.strip() != '']
                position = None
            else:
                positions = None
                position = float(pos.strip())

            jp = JointPosition(jointName=jointName.upper())
            jp.position = position
            jp.positions = str(positions)
            jp.speed = speed
            pose.jointPositions.append(jp)

        return pose


class TriggerImporter(object):

    def __init__(self):
        self._logger = logging.getLogger(self.__class__.__name__)

    def getTriggers(self, triggerLines, actions):
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
                self._logger.error("Action %s not found, skipping" % actionName, exc_info=True)
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
                    hk = ButtonHotkey()
                    hk.keyString = key
                    t.hotKeys.append(hk)
                    triggers.append(t)
            else:
                self._logger.error("Unknown trigger line?? %s" % line, exc_info=True)
                continue

        return triggers

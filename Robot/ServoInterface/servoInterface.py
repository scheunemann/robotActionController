import logging
import time
from threading import RLock
from connections import Connection

__all__ = ['ServoInterface', ]


class ServoInterface(object):

    _servoInterfaces = {}
    _globalLock = RLock()
    _interfaces = {}
    disconnected = False

    """have to do it this way to get around circular referencing in the parser"""
    @staticmethod
    def _getInterfaceClasses():
        return {
                "AX12": AX12,
                "MINISSC": MINISSC,
                "SSC32": SSC32,
                "HERKULEX": HerkuleX,
                "ROBOT": Robot,
                "DUMMY": Dummy
               }

    @staticmethod
    def getServoInterface(servo):
        with ServoInterface._globalLock:
            if servo.id not in ServoInterface._interfaces:
                if not ServoInterface.disconnected:
                    try:
                        servoIntClass = ServoInterface._getInterfaceClasses()[servo.model.name]
                    except:
                        logging.getLogger(__name__).critical("No known interface for servo model: %s", servo.model.name)
                        raise ValueError("No known interface for servo type: %s" % servo.model.name)
                    else:
                        servoInt = servoIntClass(servo)
                else:
                    servoInt = Dummy(servo)

                ServoInterface._interfaces[servo.id] = servoInt

            return ServoInterface._interfaces[servo.id]

    def __init__(self, servo):

        # servo type properties
        configs = filter(lambda c: c.model_id == servo.model_id, servo.robot.servoConfigs)
        if not configs:
            raise ValueError('Config could not be found for model %s on robot %s' % (servo.model, servo.robot))
        else:
            config = configs[0]
        self._port = config.port
        self._portSpeed = config.portSpeed

        # servo properties
        self._moving = False
        self._servo = servo
        self._minPos = servo.minPosition
        self._maxPos = servo.maxPosition
        self._defaultPos = servo.defaultPosition
        self._minSpeed = servo.minSpeed
        self._maxSpeed = servo.maxSpeed
        self._defaultSpeed = servo.defaultSpeed
        self._posOffset = servo.positionOffset
        self._speedScaleValue = servo.model.speedScale
        self._posScaleValue = servo.model.positionScale

        self._logger = logging.getLogger(self.__class__.__name__)

    @property
    def servo(self):
        return self._servo

    def isMoving(self):
        return self._moving

    def setPositioning(self, enablePositioning):
        raise ValueError('Manual positioning not supported on servo %s', self._servo)

    def getPositioning(self):
        raise ValueError('Manual positioning not supported on servo %s', self._servo)

    def setPosition(self, position, speed):
        raise ValueError('Setting position not supported on servo %s', self._servo)

    def getPosition(self):
        raise ValueError('Getting position not supported on servo %s', self._servo)

    def _scaleToRealPos(self, value):
        try:
            real = (value + self._posOffset) / self._posScaleValue
            return round(real, 2)
        except:
            if type(value) == list:
                return [round((v + self._posOffset) / self._posScaleValue, 2) for v in value]
            return value

    def _realToScalePos(self, value):
        try:
            scaled = (value * self._posScaleValue) - self._posOffset
            return round(scaled, 2)
        except:
            if type(value) == list:
                return [round((v * self._posScaleValue) - self._posOffset, 2) for v in value]
            return value

    def _scaleToRealSpeed(self, value):
        try:
            real = value / self._speedScaleValue
            return round(real, 2)
        except:
            if type(value) == list:
                return [round(v / self._speedScaleValue, 2) for v in value]
            return value

    def _realToScaleSpeed(self, value):
        try:
            scaled = value * self._speedScaleValue
            return round(scaled, 2)
        except:
            if type(value) == list:
                return [round(v * self._speedScaleValue, 2) for v in value]
            return value

    def _getInRangeVal(self, val, minVal, maxVal):
        try:
            val = max(minVal, val)
            val = min(maxVal, val)
            return val
        except:
            if type(val) == list:
                return [max(maxVal, min(minVal, v)) for v in val]
            else:
                return val


class AX12(ServoInterface):

    def __init__(self, servo):
        super(AX12, self).__init__(servo)
        self._externalId = servo.extraData.get('externalId', None)
        if self._externalId == None:
            self._logger.critical("AX12 servo %s is missing its external Id!", servo.name)

        self._conn = Connection.getConnection("AX12", self._port, self._portSpeed)
        if self._conn == None:
            raise ValueError("Error creating servo connection")
        self._checkMinMaxValues()
        self._positioning = False
        self._nextPosition = None
        self._nextSpeed = None

    def getPosition(self):
        with Connection.getLock(self._conn):
            posSteps = self._conn.GetPosition(self._externalId)

        return self._realToScalePos(posSteps)

    def setPosition(self, position, speed):
        realSpeed = int(round(self._scaleToRealSpeed(float(speed))))
        realPosition = int(round(self._scaleToRealPos(float(position))))
#         with Connection.getLock(self._conn):
        self._conn.SetMovingSpeed(self._externalId, realSpeed)
        self._conn.SetPosition(self._externalId, realPosition)

    def isMoving(self):
        with Connection.getLock(self._conn):
            return self._conn.Moving(self._externalId)

    def getPositioning(self):
        return self._positioning

    def setPositioning(self, enablePositioning):
        with Connection.getLock(self._conn):
            self._conn.SetTorqueEnable(self._externalId, int(not bool(enablePositioning)))
            self._positioning = enablePositioning

    def _checkMinMaxValues(self):
        # We can check the hardware limits set in the servos
        with Connection.getLock(self._conn):
            readMinPos = self._conn.GetCWAngleLimit(self._externalId)
            readMaxPos = self._conn.GetCCWAngleLimit(self._externalId)
        minPos = round(self._scaleToRealPos(self._minPos))
        maxPos = round(self._scaleToRealPos(self._maxPos))

        if readMinPos > minPos:
            # The motor doesn't allow for the minimum defined so far!
            self._logger.warning("Requested minimum value of %s lower than hardware limits (%s) for servo %s", minPos, readMinPos, self._externalId)
            self._minPos = self._realToScalePos(readMinPos)
        if readMaxPos < maxPos:
            # The motor doesn't allow for the maximum defined so far!
            self._logger.warning("Requested maximum value of %s higher than hardware limits (%s) for servo %s", maxPos, readMaxPos, self._externalId)
            self._maxPos = self._realToScalePos(readMaxPos)
        if self._defaultPos < self._minPos or self._defaultPos > self._maxPos:
            # The motor doesn't allow for this d!
            self._logger.warning("Requested default value of %s outside allowed interval [%s,%s] for servo %s", self._defaultPos, self._minPos, self._maxPos, self._externalId)
            self._defaultPos = self._posScaleValue / 2


class MINISSC(ServoInterface):

    def __init__(self, servo):
        super(MINISSC, self).__init__(servo)
        self._externalId = servo.extraData.get('externalId', None)
        if self._externalId == None:
            self._logger.critical("MINISSC servo %s is missing its external Id!", servo.name)

        self._conn = Connection.getConnection("SERIAL", self._port, self._portSpeed)
        self._checkMinMaxValues()

    def getPosition(self):
        return self._lastPosition

    def setPosition(self, position, speed):
        validTarget = self._getInRangeVal(position, self._minPos, self._maxPos)
        if position != validTarget:
            self._logger.warning("Target position has to be between %s and %s, got %s", self._minPos, self._maxPos, position)
            # Force target to be within range
            position = validTarget

        pos = self._scaleToRealPos(position)
        self._lastPosition = pos
        send = [0xFF, self._externalId, position]
        with Connection.getLock(self._conn):
            self._moving = True
            self._conn.write(send)
            self._moving = False


class HerkuleX(ServoInterface):

    def __init__(self, servo):
        super(HerkuleX, self).__init__(servo)
        self._externalId = servo.extraData.get('externalId', None)
        if self._externalId == None:
            self._logger.critical("HerkuleX servo %s is missing its external Id!", servo.name)

        self._conn = Connection.getConnection("HERKULEX", self._port, self._portSpeed)
        self._positioning = False

    def getPosition(self):
        with Connection.getLock(self._conn):
            posSteps = self._conn.getPosition(self._externalId)
            return self._realToScalePos(posSteps)

    def setPosition(self, position, speed):
        realPosition = int(round(self._scaleToRealPos(position)))
        realSpeed = self._scaleToRealSpeed(speed)  # steps per second
        totalSteps = abs(realPosition - self._conn.getPosition(self._externalId))
        realSpeed = (totalSteps / realSpeed) * 1000
        realSpeed = int(round(realSpeed))
        realSpeed = max(realSpeed, 0)
        realSpeed = min(realSpeed, 2856)

        with Connection.getLock(self._conn):
            self._moving = True
            self._conn.moveOne(self._externalId, realPosition, realSpeed)
            self._moving = False

    def getPositioning(self):
        return self._positioning

    def setPositioning(self, enablePositioning):
        with Connection.getLock(self._conn):
            if enablePositioning:
                self._conn.torqueOFF(self._externalId)
            else:
                self._conn.torqueON(self._externalId)
            self._positioning = enablePositioning


class SSC32(ServoInterface):

    def __init__(self, servo):
        super(SSC32, self).__init__(servo)
        self._externalId = servo.extraData.get('externalId', None)
        if self._externalId == None:
            self._logger.critical("MINISSC servo %s is missing its external Id!", servo.name)

        self._conn = Connection.getConnection("SERIAL", self._port, self._portSpeed)
        self._checkMinMaxValues()

    def getPosition(self):
        send = "QP %s\r" % self._externalId
        with Connection.getLock(self._conn):
            self._conn.write(send)
            lastChar = ""
            response = ""
            while lastChar != '\r':
                lastChar = self._conn.read(1)
                response += lastChar

        response = response.strip(['\r', ])
        p = int(response)
        return self._realToScalePos(p * 10)

    def setPosition(self, position, speed):
        validTarget = self._getInRangeVal(position, self._minPos, self._maxPos)
        if position != validTarget:
            self._logger.warning("Target position has to be between %s and %s, got %s", self._minPos, self._maxPos, position)
            # Force target to be within range
            position = validTarget

        pos = self._scaleToRealPos(position)
        spd = self._scaleToRealSpeed(speed)

        send = "#%sP%s T%s\r" % (self._externalId, pos, spd)
        self._logger.info("Sending SSC32 String: %s", send)
        with Connection.getLock(self._conn):
            self._moving = True
            self._conn.write(send)
            self._moving = False


class Dummy(ServoInterface):

    def __init__(self, servo):
        super(Dummy, self).__init__(servo)
        self._position = 0
        self._posable = False
        self._logger = logging.getLogger(self.__class__.__name__)
        import os
        basePath = os.path.dirname(os.path.abspath(__file__))
        basePath = os.path.join(basePath, 'servoData')
        if not os.path.exists(basePath):
            os.makedirs(basePath)
        fileName = 'dummyServoData_%s' % self._servo.id
        self._fileName = os.path.join(basePath, fileName)

    def setPositioning(self, enablePositioning):
        self._posable = enablePositioning
        self._logger.log(1, "%s Set positioning to: %s", self._servo, enablePositioning)
        self._writeData()

    def getPositioning(self):
        self._readData()
        return self._posable

    def setPosition(self, position, speed):
        self._position = position
        self._moving = True
        self._logger.log(1, "%s Seting position to: %s, speed: %s", self._servo, position, speed)
        time.sleep(1.0 / (speed / 100.0))
        self._writeData()
        self._logger.debug("%s Set position to: %s", self._servo, position)
        self._moving = False

    def getPosition(self):
        self._readData()
        self._logger.log(1, "%s Got position: %s", self._servo, self._position)
        return self._position

    def _readData(self):
        import pickle
        try:
            data = pickle.load(self._fileName, 'r')
            self._position = data['position']
            self._posable = data['posable']
        except:
            pass

    def _writeData(self):
        import pickle
        try:
            data = {'position': self._position, 'posable': self._posable}
            pickle.dump(data, self._fileName, 'w')
        except:
            pass


class Robot(ServoInterface):

    def __init__(self, servo):
        super(Robot, self).__init__(servo)
        self._componentName = servo.extraData.get('externalId', None)
        if self._componentName == None:
            self._logger.critical("Servo %s is missing its component name (externalId)!", servo.name)

        #         self._checkMinMaxValues()
        from Robot.RosInterface.robotFactory import Factory
        self._robot = Factory.getRobotInterface(servo.robot)
        if not self._robot:
            raise ValueError("Robot attached to servo could not be resolved")

    def getPosition(self):
        if self._componentName == 'base':
            (_, (x, y, theta)) = self._robot.getLocation()
            posRaw = [x, y, theta]
        elif self._componentName == 'base_linear':
            pass
        elif self._componentName == 'base_rot':
            pass
        else:
            (_, posDict) = self._robot.getComponentState(self._componentName)
            if posDict['positions']:
                posRaw = posDict['positions'][0]
            else:
                posRaw = 0
        return self._realToScalePos(posRaw)

    def setPosition(self, position, speed):
        scaledPosition = self._scaleToRealPos(position)
        return self._robot.setComponentState(self._componentName, scaledPosition) == 'SUCCEEDED'

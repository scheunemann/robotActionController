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
            if servo not in ServoInterface._interfaces:
                if not ServoInterface.disconnected:
                    try:
                        servoInt = ServoInterface._getInterfaceClasses()[servo.model.name]
                    except:
                        logging.getLogger(__name__).critical("No known interface for servo model: %s", servo.model.name)
                        raise ValueError("No known interface for servo type: %s" % servo.model.name)
                    else:
                        servoInt = servoInt(servo)
                else:
                    servoInt = Dummy(servo)

                ServoInterface._interfaces[servo] = servoInt

            return ServoInterface._interfaces[servo]

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
        self._minPos = servo.minPosition or servo.model.minPosition
        self._maxPos = servo.maxPosition or servo.model.maxPosition
        self._defaultPos = servo.defaultPosition or servo.model.defaultPosition
        self._minSpeed = servo.minSpeed or servo.model.minSpeed
        self._maxSpeed = servo.maxSpeed or servo.model.maxSpeed
        self._defaultSpeed = servo.defaultSpeed or servo.model.defaultSpeed
        self._posOffset = servo.positionOffset or servo.model.positionOffset
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
        real = (value / self._posScaleValue) + self._posOffset
        return round(real, 2)

    def _realToScalePos(self, value):
        scaled = (value - self._posOffset) * self._posScaleValue
        return round(scaled, 2)

    def _scaleToRealSpeed(self, value):
        real = value / self._speedScaleValue
        return round(real, 2)

    def _realToScaleSpeed(self, value):
        scaled = value * self._speedScaleValue
        return round(scaled, 2)

    def _getInRangeVal(self, val, minVal, maxVal):
        val = max(minVal, val)
        val = min(maxVal, val)
        return val


class AX12(ServoInterface):

    def __init__(self, servo):
        super(AX12, self).__init__(servo)
        self._externalId = servo.extraData.get('externalId', None)
        if self._externalId == None:
            self._logger.critical("AX12 servo %s is missing its external Id!", servo.name)

        self._conn = Connection.getConnection("AX12", self._port, self._portSpeed)
        self._checkMinMaxValues()
        self._positioning = False

    def getPosition(self):
        with Connection.getLock(self._conn):
            posSteps = self._conn.GetPosition(self._externalId)
            return self._realToScalePos(posSteps)

    def setPosition(self, position, speed):
        scaledSpeed = self._scaleToRealSpeed(speed)
        scaledPosition = self._scaleToRealPos(position)
        with Connection.getLock(self._conn):
            self._moving = True
            self._conn.SetMovingSpeed(self._externalId, scaledSpeed)
            self._conn.SetPosition(self._externalId, scaledPosition)
            self._moving = False

    def getPositioning(self):
        return self._positioning

    def setPositioning(self, enablePositioning):
        with Connection.getLock(self._conn):
            self._conn.SetTorqueEnable(self._externalId, int(not enablePositioning))
            self._positioning = enablePositioning

    def _checkMinMaxValues(self):
        # We can check the hardware limits set in the servos
        with Connection.getLock(self._conn):
            readMinPos = self._conn.GetCWAngleLimit(self._externalId)
            readMaxPos = self._conn.GetCCWAngleLimit(self._externalId)

        if readMinPos > self._minPos:
            # The motor doesn't allow for the minimum defined so far!
            self._logger.warning("Requested minimum value of %s lower than hardware limits (%s) for servo %s", self._minPos, readMinPos, self._externalId)
            self._minPos = readMinPos
        if readMaxPos < self._maxPos:
            # The motor doesn't allow for the maximum defined so far!
            self._logger.warning("Requested maximum value of %s higher than hardware limits (%s) for servo %s", self._maxPos, readMaxPos, self._externalId)
            self._maxPos = readMaxPos
        # TODO: posScaleValue isn't used like this anymore???
        if self._defaultPos < 0 or self._defaultPos > self._posScaleValue:
            # The motor doesn't allow for this d!
            self._logger.warning("Requested default value of %s outside allowed interval [0,%s] for servo %s", self._defaultPos, self._posScaleValue, self._externalId)
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


def Robot(ServoInterface):

    def __init__(self, servo):
        super(Robot, self).__init__(servo)
        self._componentName = servo.extraData.get('componentName', None)
        if self._componentName == None:
            self._logger.critical("Servo %s is missing its component name!", servo.name)

        self._checkMinMaxValues()
        from Robot.RosInterface.robotFactory import Factory
        self._robot = Factory.getRobotInterface(servo.robot)

    def getPosition(self):
        if self._componentName == 'base':
            (_, posRaw) = self._robot.getLocation()
        else:
            (_, posRaw) = self._robot.getComponentState(self._componentName)
        return self._realToScalePos(posRaw)

    def setPosition(self, position, speed):
        scaledPosition = self._scaleToRealPos(position)
        self._robot.setComponentState(self._componentName, scaledPosition)

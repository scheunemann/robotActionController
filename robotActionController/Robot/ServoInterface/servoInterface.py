import logging
import datetime
import time
from gevent.lock import RLock
from gevent import spawn_later, sleep
from robotActionController.connections import Connection

__all__ = ['ServoInterface', ]


class ServoInterface(object):
    _servoCache = {}
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
                "HS82MG": HS82MG,
                "DUMMY": Dummy,
                "VIRTUAL": Virtual,
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
        self._servoId = servo.id
        self._jointName = servo.jointName
        self._minPos = float(servo.minPosition if servo.minPosition != None else servo.model.minPosition)
        self._maxPos = float(servo.maxPosition if servo.maxPosition != None else servo.model.maxPosition)
        self._defaultPosition = float(servo.defaultPosition if servo.defaultPosition != None else servo.model.defaultPosition)
        self._minSpeed = float(servo.minSpeed if servo.minSpeed != None else servo.model.minSpeed)
        self._maxSpeed = float(servo.maxSpeed if servo.maxSpeed != None else servo.model.maxSpeed)
        self._defaultSpeed = float(servo.defaultSpeed if servo.defaultSpeed != None else servo.model.defaultSpeed)
        self._posOffset = float(servo.positionOffset if servo.positionOffset != None else servo.model.positionOffset)
        self._speedScaleValue = float(servo.model.speedScale)
        self._posScaleValue = float(servo.model.positionScale)
        self._tolerance = 10  # Max diff to be considered the same position

        self._logger = logging.getLogger(self.__class__.__name__)

    @property
    def servoId(self):
        return self._servoId

    @property
    def jointName(self):
        return self._jointName

    def isMoving(self):
        return self._moving

    def setPositioning(self, enablePositioning):
        pass

    def getPositioning(self):
        return False

    def setPosition(self, position, speed, blocking=False):
        raise ValueError('Setting position not supported on servo %s' % self._servoId)

    def getPosition(self):
        raise ValueError('Getting position not supported on servo %s' % self._servoId)

    def _isInPosition(self, position):
        return abs(self._tolerance - self.getPosition()) >= self._tolerance

    def _scaleToRealPos(self, value):
        try:
            real = (float(value) / self._posScaleValue) + self._posOffset
            return round(real, 2)
        except:
            if type(value) == list:
                return [round((float(v) / self._posScaleValue) + self._posOffset, 2) for v in value]
            return value

    def _realToScalePos(self, value):
        try:
            scaled = (float(value) - self._posOffset) * self._posScaleValue
            return round(scaled, 2)
        except:
            if type(value) == list:
                return [round((float(v) - self._posOffset) * self._posScaleValue, 2) for v in value]
            return value

    def _scaleToRealSpeed(self, value):
        try:
            real = float(value) / self._speedScaleValue
            return round(real, 2)
        except:
            if type(value) == list:
                return [round(float(v) / self._speedScaleValue, 2) for v in value]
            return value

    def _realToScaleSpeed(self, value):
        try:
            scaled = float(value) * self._speedScaleValue
            return round(scaled, 2)
        except:
            if type(value) == list:
                return [round(float(v) * self._speedScaleValue, 2) for v in value]
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
            raise ValueError()
        self._externalId = int(self._externalId)

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

    def setPosition(self, position=None, speed=None, blocking=False):
        if position == None:
            position = self._defaultPosition
        if speed == None:
            speed = self._defaultSpeed

        realSpeed = int(round(self._scaleToRealSpeed(float(speed))))
        realPosition = int(round(self._scaleToRealPos(float(position))))
        # print "%s: %s @ %s" % (self._jointName, realPosition, realSpeed)
        with Connection.getLock(self._conn):
            try:
                self._conn.SetMovingSpeed(self._externalId, realSpeed)
                self._conn.SetPosition(self._externalId, realPosition)
            except:
                self._logger.error("Error occurred while setting servo position.", exc_info=True)
                return False

        if blocking:
            while self.isMoving():
                time.sleep(0.001)

        try:
            return self._isInPosition(position)
        except:
            self._logger.error("Error occurred while setting servo position.", exc_info=True)
            return False

    def isMoving(self):
        with Connection.getLock(self._conn):
            try:
                return self._conn.Moving(self._externalId)
            except:
                self._logger.error("Error occurred while checking moving state.", exc_info=True)
                return False

    def getPositioning(self):
        return self._positioning

    def setPositioning(self, enablePositioning):
        with Connection.getLock(self._conn):
            self._conn.SetTorqueEnable(self._externalId, int(not bool(enablePositioning)))
            self._positioning = enablePositioning

    def _checkMinMaxValues(self):
        try:
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
            if self._defaultPosition < self._minPos or self._defaultPosition > self._maxPos:
                # The motor doesn't allow for this d!
                self._logger.warning("Requested default value of %s outside allowed interval [%s,%s] for servo %s", self._defaultPosition, self._minPos, self._maxPos, self._externalId)
                self._defaultPosition = self._posScaleValue / 2
        except Exception:
            self._logger.warning("Error reading angle limits", exc_info=True)


class MINISSC(ServoInterface):

    def __init__(self, servo):
        super(MINISSC, self).__init__(servo)
        self._externalId = servo.extraData.get('externalId', None)
        if self._externalId == None:
            self._logger.critical("MINISSC servo %s is missing its external Id!", servo.name)
            raise ValueError()
        self._externalId = int(self._externalId)

        self._conn = Connection.getConnection("SERIAL", self._port, self._portSpeed)
        self._checkMinMaxValues()

    def getPosition(self):
        return self._lastPosition

    def setPosition(self, position=None, speed=None, blocking=False):
        if position == None:
            position = self._defaultPosition
        if speed == None:
            speed = self._defaultSpeed

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

        if blocking:
            time.sleep(1)

        return True


class HerkuleX(ServoInterface):

    def __init__(self, servo):
        super(HerkuleX, self).__init__(servo)
        self._externalId = servo.extraData.get('externalId', None)
        if self._externalId == None:
            self._logger.critical("HerkuleX servo %s is missing its external Id!", servo.name)
            raise ValueError()
        self._externalId = int(self._externalId)

        self._conn = Connection.getConnection("HERKULEX", self._port, self._portSpeed)
        self._conn.initialize(self._externalId)
        self._positioning = False
        self._lastSetPosition = self.getPosition()

    def isMoving(self):
        with Connection.getLock(self._conn):
            _, detailCode = self._conn.stat(self._externalId, True)

        return detailCode & self._conn.H_DETAIL_MOVING

    def getPosition(self):
        with Connection.getLock(self._conn):
            posSteps = self._conn.getPosition(self._externalId)
            return self._realToScalePos(posSteps)

    def setPosition(self, position=None, speed=None, blocking=False):
        if position == None:
            position = self._defaultPosition
        if speed == None:
            speed = self._defaultSpeed

        with Connection.getLock(self._conn):
            currentPosition = int(self._conn.getPosition(self._externalId))

        currentPosition = currentPosition if currentPosition >= 0 else self._lastSetPosition
        self._lastSetPosition = position

        realPosition = int(round(float(self._scaleToRealPos(position))))
        if currentPosition == -1:
            self._logger.debug("Could not get position from servo %s, defaulting to slow movement", self._externalId)
            steps = [(realPosition, self._conn.MAX_PLAY_TIME),]
        else:
            stepsPerSec = self._scaleToRealSpeed(speed)
            totalSteps = abs(realPosition - currentPosition)
            stepsPerMove = self._conn.MAX_PLAY_TIME * (stepsPerSec / 1000.0) - 10
            steps = []
            stepsRemaining = totalSteps
            endPosition = currentPosition
            direction = 1 if realPosition > currentPosition else -1
            while stepsRemaining:
                thisSteps = min(stepsRemaining, stepsPerMove)
                endPosition = int(endPosition + (thisSteps * direction))
                runTime = int((thisSteps / stepsPerSec) * 1000)
                steps.append((endPosition, runTime))
                stepsRemaining = max(0, stepsRemaining - thisSteps)

        self.__temperatureHackDONOTUSEINRELEASE()
        self._logger.log(1, "Moving Servo %s to from %s to %s in %ss using steps: %s" % (self._externalId,
                                                                                           currentPosition,
                                                                                           realPosition,
                                                                                           round(totalSteps / stepsPerSec, 3),
                                                                                           steps))
        if blocking:
            for step in steps:
                with Connection.getLock(self._conn):
                    self._conn.moveOne(self._externalId, step[0], step[1])
                time.sleep(max(0, step[1] - 30) / 1000)
        else:
            def callback(steps, currentStep):
                if currentStep < len(steps):
                    step = steps[currentStep]
                    with Connection.getLock(self._conn):
                        self._conn.moveOne(self._externalId, step[0], step[1])
                    spawn_later((step[1] - 30) / 1000, callback, steps, currentStep + 1)
            callback(steps, 0)

        #return self._conn.stat(self._externalId) == 0
        return True

    def getPositioning(self):
        return self._positioning

    def setPositioning(self, enablePositioning):
        with Connection.getLock(self._conn):
            if enablePositioning:
                self._conn.torqueOFF(self._externalId)
            else:
                self._conn.torqueON(self._externalId)
            self._positioning = enablePositioning

    def __temperatureHackDONOTUSEINRELEASE(self):
        with Connection.getLock(self._conn):
            errors = self._conn.stat(self._externalId)
            if errors:
                if errors & self._conn.H_ERROR_TEMPERATURE_LIMIT:
                    if self._conn.getTemperature(self._externalId) < 60:
                        self._logger.warning("AUTOCLEARING TEMPERATURE ERROR ON SERVO %s", self._externalId)
                        self._conn.clearError(self._externalId)
                        self._conn.torqueON(self._externalId)
                    else:
                        self._logger.warning("SERVO %s STILL IN OVERHEAT, CANNOT CLEAR ERROR", self._externalId)
                        return
                if errors & self._conn.H_ERROR_OVERLOAD:
                    self._logger.warning("AUTOCLEARING TORQUE ERROR ON SERVO %s", self._externalId)
                    self._conn.clearError(self._externalId)
                    self._conn.torqueON(self._externalId)
                self._conn.clearError(self._externalId)
                self._conn.torqueON(self._externalId)


class SSC32(ServoInterface):

    def __init__(self, servo):
        super(SSC32, self).__init__(servo)
        self._externalId = servo.extraData.get('externalId', None)
        if self._externalId == None:
            self._logger.critical("MINISSC servo %s is missing its external Id!", servo.name)
            raise ValueError()
        self._externalId = int(self._externalId)

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

    def setPosition(self, position=None, speed=None, blocking=False):
        if position == None:
            position = self._defaultPosition
        if speed == None:
            speed = self._defaultSpeed

        validTarget = self._getInRangeVal(position, self._minPos, self._maxPos)
        if position != validTarget:
            self._logger.warning("Target position has to be between %s and %s, got %s", self._minPos, self._maxPos, position)
            # Force target to be within range
            position = validTarget

        pos = self._scaleToRealPos(position)
        spd = self._scaleToRealSpeed(speed)

        send = "#%sP%s T%s\r" % (self._externalId, pos, spd)
        self._logger.log(1, "Sending SSC32 String: %s", send)
        with Connection.getLock(self._conn):
            self._moving = True
            self._conn.write(send)
            self._moving = False

        if blocking:
            time.sleep(1)

        return self._isInPosition(position)


class HS82MG(ServoInterface):

    def __init__(self, servo):
        super(HS82MG, self).__init__(servo)
        self._externalId = servo.extraData.get('externalId', None)
        if self._externalId == None:
            self._logger.critical("MINISSC servo %s is missing its external Id!", servo.name)
            raise ValueError()
        self._externalId = int(self._externalId)

        self._conn = Connection.getConnection("minimaestro", self._port, self._portSpeed)
        self._lastPosition = (datetime.datetime.utcnow(), 0, 0)

    def isMoving(self):
        # drivers getMovingState is rather inacturate
        # compute the estimated time in ms to complete moving and pad by 20%
        return (datetime.datetime.utcnow() - self._lastPosition[0]).total_seconds() * 1500 > self._lastPosition[2]
        # with Connection.getLock(self._conn):
        #    return self._conn.getMovingState()

    def getPosition(self):
        with Connection.getLock(self._conn):
            posSteps = self._conn.getPosition(self._externalId)
            return self._realToScalePos(posSteps)

    def setPosition(self, position=None, speed=None, blocking=False):
        self._logger.log(1, "%s Got scaled Position: %s, Speed: %s", self._externalId, position, speed)
        if position == None:
            position = self._defaultPosition
        if speed == None:
            speed = self._defaultSpeed

        validTarget = self._getInRangeVal(position, self._minPos, self._maxPos)
        if position != validTarget:
            self._logger.warning("%s Target position has to be between %s and %s, got %s", self._externalId, self._minPos, self._maxPos, position)
            # Force target to be within range
            position = validTarget

        pos = self._scaleToRealPos(position)
        spd = self._scaleToRealSpeed(speed)

        with Connection.getLock(self._conn):
            self._conn.setSpeed(self._externalId, int(spd))
            self._conn.setTarget(self._externalId, int(pos))

        self._lastPosition = (datetime.datetime.utcnow(), pos, spd * 0.025 * abs(self._lastPosition[1] - pos))
        self._logger.log(1, "%s Setting real pos: %s spd: %s time: %s", self._externalId, pos, spd, self._lastPosition[2])

        if blocking:
            while self.isMoving():
                sleep(0.01)

        return True

    def setPositioning(self, enablePositioning):
        with Connection.getLock(self._conn):
            if enablePositioning:
                self._conn.setTarget(self._externalId, 0)
            else:
                self.setPosition(self.getPosition())
            self._positioning = enablePositioning

    def getPositioning(self):
        return self._conn.getPosition(self._externalId) != 0


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
        fileName = 'dummyServoData_%s' % self._servoId
        self._fileName = os.path.join(basePath, fileName)

    def setPositioning(self, enablePositioning):
        self._posable = enablePositioning
        self._logger.log(1, "%s Set positioning to: %s", self._servoId, enablePositioning)
        self._writeData()

    def getPositioning(self):
        self._readData()
        return self._posable

    def setPosition(self, position=None, speed=None, blocking=False):
        if position == None:
            position = self._defaultPosition
        if speed == None:
            speed = self._defaultSpeed

        diff = abs(self._position - position)
        secs = 1.0 / 1024 * diff
        self._position = position
        self._moving = True
        self._logger.log(1, "%s Seting position to: %s, speed: %s", self._servoId, position, speed)
        time.sleep(secs / (speed / 100.0))
        self._writeData()
        self._logger.log(1, "%s Set position to: %s", self._servoId, position)
        if blocking:
            time.sleep(0.5)

        self._moving = False
        return True

    def getPosition(self):
        self._readData()
        self._logger.log(1, "%s Got position: %s", self._servoId, self._position)
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


class Virtual(ServoInterface):

    def __init__(self, servo):
        super(Virtual, self).__init__(servo)
        masterServoName = servo.extraData.get('MASTER', None)
        slaveServoName = servo.extraData.get('SLAVE', None)
        masterServo = filter(lambda s: s.jointName == masterServoName, servo.robot.servos)
        slaveServo = filter(lambda s: s.jointName == slaveServoName, servo.robot.servos)
        self._ratio = int(servo.extraData.get('RATIO', 1))
        self._absolute = servo.extraData.get('absolute', True)
        self._jointName = servo.jointName
        if not masterServo:
            self._logger.critical("Could not locate physical servo %s for virtual servo %s!" % (masterServoName, servo.jointName))
            raise ValueError("Could not locate physical servo %s for virtual servo %s!" % (masterServoName, servo.jointName))
        if not slaveServo:
            self._logger.critical("Could not locate physical servo %s for virtual servo %s!" % (slaveServoName, servo.jointName))
            raise ValueError("Could not locate physical servo %s for virtual servo %s!" % (slaveServoName, servo.jointName))

        self._master = ServoInterface.getServoInterface(masterServo[0])
        self._slave = ServoInterface.getServoInterface(slaveServo[0])

    def getPosition(self):
        return self._master.getPosition()

    def setPosition(self, position=None, speed=None, blocking=False):
        if position == None:
            position = self._defaultPosition
        if speed == None:
            speed = self._defaultSpeed

        if self._absolute:
            slavePosition = position * self._ratio
        else:
            curMaster = self._master.getPosition()
            curSlave = self._slave.getPosition()
            diff = position - curMaster
            slavePosition = curSlave + (diff * self._ratio)

        self._logger.log(1, "%s Master Pos: %s, Slave Pos: %s", self._jointName, position, slavePosition)
        masterSuccess = self._master.setPosition(position, speed, blocking)
        slaveSuccess = self._slave.setPosition(slavePosition, speed, blocking)
        return masterSuccess & slaveSuccess

    def setPositioning(self, enablePositioning):
        self._master.setPositioning(enablePositioning)
        self._slave.setPositioning(enablePositioning)

    def getPositioning(self):
        return self.getPosition() != 0


class Robot(ServoInterface):

    def __init__(self, servo):
        super(Robot, self).__init__(servo)
        self._componentName = servo.extraData.get('externalId', None)
        if self._componentName == None:
            self._logger.critical("Servo %s is missing its component name (externalId)!", servo.name)
            raise ValueError()

        #         self._checkMinMaxValues()
        from robotActionController.Robot.RosInterface.robotFactory import Factory
        self._robot = Factory.getRobotInterface(servo.robot)
        if not self._robot:
            raise ValueError("Robot attached to servo could not be resolved")

    def getPosition(self):
        if self._componentName == 'base':
            (_, (x, y, theta)) = self._robot.getLocation()
            posRaw = [x, y, theta]
        elif self._componentName == 'base_direct':
            # TODO: ???
            return None
        else:
            (_, posDict) = self._robot.getComponentState(self._componentName)
            if posDict['positions']:
                posRaw = posDict['positions'][0]
            else:
                posRaw = 0
        return self._realToScalePos(posRaw)

    def setPosition(self, position=None, speed=None, blocking=False):
        if position == None:
            position = self._defaultPosition
        if speed == None:
            speed = self._defaultSpeed

        scaledPosition = self._scaleToRealPos(position)
        return self._robot.setComponentState(self._componentName, scaledPosition, blocking) == 'SUCCEEDED'

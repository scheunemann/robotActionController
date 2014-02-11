import threading
from Robot.ServoInterface.servoInterface import ServoInterface
from base import Runner
from Data.Model import Pose
from multiprocessing.pool import ThreadPool as Pool


class PoseRunner(Runner):

    class PoseHandle(Runner.ExecutionHandle):

        def __init__(self, pose, robot):
            super(PoseRunner.PoseHandle, self).__init__(pose)
            self._robot = robot

        def _runInternal(self, action, session):
            self._cancel = False
            interfaces = {}
            robot = session.merge(self._robot, load=False)
            pool = Pool(processes=len(action.jointPositions))

            l = []
            for jointPosition in action.jointPositions:
                servos = filter(lambda s: s.jointName == jointPosition.jointName, robot.servos)
                if len(servos) != 1:
                    self._logger.critical("Could not determine appropriate servo(%s) on Robot(%s).  Expected 1 match, got %s" % (jointPosition.jointName, robot.name, len(servos)))
                    raise ValueError("Could not determine appropriate servo(%s) on Robot(%s).  Expected 1 match, got %s" % (jointPosition.jointName, robot.name, len(servos)))
                servo = servos[0]
                speed = jointPosition.speed or servo.defaultSpeed
                speed = speed * (action.speedModifier or 1)
                position = jointPosition.position
                if position == None:
                    if jointPosition.positions != None:
                        try:
                            position = eval(jointPosition.positions)
                        except Exception as e:
                            self._logger.critical("Invalid multiple position(%s) specified for servo %s.  Joint Positions %s" % (jointPosition.position, servo, jointPosition.id))
                            self._logger.critical(e)
                            return False
                    elif servo.defaultPosition != None:
                        position = servo.defaultPosition
                    elif servo.defaultPositions != None:
                        try:
                            position = eval(servo.defaultPositions)
                        except Exception as e:
                            self._logger.critical("Invalid multiple position(%s) default specified for servo %s." % (jointPosition.position, servo))
                            self._logger.critical(e)
                            return False
                    else:
                        self._logger.critical("Could not determine servo position for joint %s" % jointPosition)
                        self._logger.critical(e)
                try:
                    servoInterface = ServoInterface.getServoInterface(servo)
                except ValueError as e:
                    self._logger.critical("Servo %s is in an error state" % (servo))
                    self._logger.critical(e)
                    return False

                l.append((position, speed, servoInterface))
                interfaces[jointPosition] = servoInterface

            results = [pool.apply_async(servoInterface.setPosition, args=(position, speed)) for (position, speed, servoInterface) in l]

            pool.close()
            pool.join()

            if self._cancel:
                result = False
            else:
                # TODO: add result to setPosition as needed
                result = all([r.get() for r in results])
#                 result = all([(abs(interface.getPosition() - joint.position) <= 10) for (joint, interface) in interfaces.iteritems()])

            return result

        def waitForComplete(self):
            if not self is threading.current_thread():
                self.join()

            return self._result

        def stop(self):
            self._cancel = True
            self.waitForComplete()

    supportedClass = Pose

    def _getHandle(self, action):
        return PoseRunner.PoseHandle(action, self._robot)

    def __init__(self, robot):
        super(PoseRunner, self).__init__(robot)

    def isValid(self, pose):
        if len(pose.jointPositions) > 0:
            for jointPosition in pose.jointPositions:
                if len(filter(lambda s: s.jointName == jointPosition.jointName, self._robot.servos)) == 0:
                    return False
            return True
        else:
            return False

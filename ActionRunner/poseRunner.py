import threading
from Robot.ServoInteface.servoInterface import ServoInterface
from base import Runner
from Data.Model import Pose, Robot
from multiprocessing.pool import ThreadPool as Pool


class PoseRunner(Runner):

    class PoseHandle(Runner.ExecutionHandle):

        def __init__(self, pose, robot):
            super(PoseRunner.PoseHandle, self).__init__(pose)
            self._robotId = robot.id

        def _runInternal(self, action, session):
            self._cancel = False
            interfaces = {}
            robot = session.query(Robot).get(self._robotId)
            pool = Pool(processes=len(action.jointPositions))
            for jointPosition in action.jointPositions:
                servos = filter(lambda s: s.jointName == jointPosition.jointName, robot.servos)
                if len(servos) != 1:
                    self._logger.critical("Could not determine appropriate servo on Robot(%s).  Expected 1 match, got %s", robot.name, len(servos))
                    raise ValueError("Could not determine appropriate servo on Robot(%s).  Expected 1 match, got %s", robot.name, len(servos))
                servo = servos[0]
                speed = jointPosition.speed or servo.defaultSpeed or servo.model.defaultSpeed or 100
                speed = speed * (action.speedModifier or 1)
                position = jointPosition.position or servo.defaultPosition or servo.model.defaultPosition or 0
                servoInterface = ServoInterface.getServoInterface(servo)
                pool.apply_async(servoInterface.setPosition, args=(position, speed))
                interfaces[jointPosition] = servoInterface

            pool.close()
            pool.join()
#             for (jointPosition, interface) in interfaces.iteritems():
#                 # TODO: better tolerance calculation
#                 while not self._cancel and interface.isMoving() and abs(interface.getPosition() - jointPosition.position) > 10:
#                     time.sleep(0.001)

            if self._cancel:
                result = False
            else:
                result = all([(abs(interface.getPosition() - joint.position) <= 10) for (joint, interface) in interfaces.iteritems()])

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
